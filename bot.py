# bot.py
import os
import discord
import random
import asyncio
import typing
import re
import datetime

from dotenv import load_dotenv
from discord.ext import commands, tasks

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")
WORKING_CHANNEL = os.getenv("WORKING_CHANNEL_ID")
JACKBOX_VOICECHANNEL_CATEGORY = os.getenv("JACKBOX_VOICECHANNEL_CATEGORY")
DEFAULT_QUEUE_NAME = os.getenv("DEFAULT_QUEUE_NAME")
DEFAULT_QUEUE_MINIMUM_REQ = 2

# client = discord.Client()
bot = commands.Bot(command_prefix="!")
bot.remove_command("help")

# maximum amount of jackbox voicechannels
maximum_channel_number = 20
# maximum size of one jackbox voicechannel
maximum_channel_size = 16
# minimum size of one jackbox voicechannel
minimum_channel_size = 2

# the maximum amount of seconds a user should be in a queue
max_user_livetime = 60*30  # 30 mins

wtp_queues = []


################# CLASSES #####################

class QueueUser:
    def __init__(self, member, queue):
        self.member = member
        self.queue = queue
        self.livetime = 0

    def __eq__(self, other):
        return self.member == other.member


class IndividQueue:
    FULL = 2
    NOTFULL = 1
    EMPTY = 0

    def __init__(self, originator: QueueUser, queue_name: str, min_req: int):
        self.userlist = []
        if originator is not None:
            self.userlist.append(originator)
        self.originator = originator
        self.name = queue_name
        self.min_req = min_req

    def append(self, queue_user: QueueUser):
        self.userlist.append(queue_user)

    def remove(self, queue_user: QueueUser):
        self.userlist.remove(queue_user)

    def status(self):
        if len(self.userlist) == 0:
            return IndividQueue.EMPTY
        elif len(self.userlist) < self.min_req:
            return IndividQueue.NOTFULL
        elif len(self.userlist) == self.min_req:
            return IndividQueue.FULL

    def __len__(self):
        return len(self.userlist)

    def __eq__(self, other):
        return self.name == other.name


##################### HELPER FUNCTIONS ###########################

def bot_command_channel(channel="searching-for-players"):
    async def wrapper_for_check(ctx, *args):
        if ctx.message.channel.name != channel:
            await ctx.send(f"{ctx.message.author.mention}, this botcommand belongs into {discord.utils.find(lambda c: channel == c.name, ctx.message.guild.channels).mention}", delete_after=20)
            await ctx.message.delete(delay=20)

            return False
        else:
            return True

    return commands.check(wrapper_for_check)


def get_current_guild():
    return discord.utils.find(lambda g: GUILD == g.name, bot.guilds)


def get_current_jackbox_vcs():
    return discord.utils.find(lambda c: JACKBOX_VOICECHANNEL_CATEGORY == c.name, get_current_guild().categories).voice_channels


# FIXME dont forget that I subtracted the deltatime of 2 hrs, to get the same time, as the discord UI
async def manage_channels(refreshrate_sec: int):
    while not bot.is_closed():
        jack_calls = get_current_jackbox_vcs()
        for vc in jack_calls:
            if vc.name == "jackbox 1" or vc.name == "jackbox 2":
                continue
            else:
                if len(vc.members) == 0 and (vc.created_at + datetime.timedelta(minutes=10) < datetime.datetime.now() - datetime.timedelta(hours=2)):
                    await vc.delete(reason="Empty")
        await update_queue_user(refreshrate_sec)
        await asyncio.sleep(refreshrate_sec)


async def update_queue_user(time_to_add: int):
    for queue in wtp_queues:
        for queue_user in queue.userlist:
            queue_user.livetime += time_to_add
            if queue_user.livetime > max_user_livetime:
                queue.remove(queue_user)
        if queue.status() == IndividQueue.EMPTY and queue.name != DEFAULT_QUEUE_NAME:
            wtp_queues.remove(queue)


def queue_name_is_valid(channelname: str):
    if re.match(r"jackbox \d+", channelname.lower()) or channelname.lower() == DEFAULT_QUEUE_NAME.lower():
        return False
    else:
        return True


def user_already_in_any_queue(queue_user_to_check: discord.Member):
    for queue in wtp_queues:
        for queue_user in queue.userlist:
            if queue_user_to_check == queue_user.member:
                return queue_user

    return None


def get_queue(queue_name: str):
    if queue_name == DEFAULT_QUEUE_NAME:
        return wtp_queues[0]

    for queue in wtp_queues:
        if queue_name == queue.name:
            return queue

    return None


def add_user_to_queue(member: discord.Member, queuename: str):
    queue = get_queue(queuename)
    new_user = QueueUser(member, queue)
    queue.append(new_user)
    return queue


def add_queue(originator: discord.Member, queuename: str, min_req: int):
    new_originator = QueueUser(originator, None)
    queue = IndividQueue(new_originator, queuename, min_req)
    new_originator.queue = queue
    wtp_queues.append(queue)
    return queue


def queue_full_response(queue: IndividQueue):
    response = "Hey "
    for queue_user in queue.userlist:
        response += f"{queue_user.member.mention}, "

    response += "finally you are enough players for a new party. Have fun!!!"
    return response


def delete_queue(queue: IndividQueue):
    queue.userlist.clear()
    wtp_queues.remove(queue)


def get_smallest_available_channelnumber():
    vcs = get_current_jackbox_vcs()
    channelnumbers = []
    for vc in vcs:
        groups = re.match(r"jackbox (\d+)", vc.name.lower())
        channelnumbers.append(int(groups.group(1)))

    channelnumbers.sort()
    if len(channelnumbers) == 0:
        return 1
    elif len(channelnumbers) == 1:
        return channelnumbers[0] + 1
    else:
        for i in range(1, len(channelnumbers)):
            if channelnumbers[i - 1] == channelnumbers[i] - 1:
                continue
            else:
                return channelnumbers[i] - 1

        # we return len + 1, because the first channel starts at 1
        return len(channelnumbers) + 1

##################### EVENTS AND COMMANDS #######################################


@bot.event
async def on_ready():
    wtp_queues.append(IndividQueue(
        None, DEFAULT_QUEUE_NAME, DEFAULT_QUEUE_MINIMUM_REQ))
    bot.loop.create_task(manage_channels(60))
    print("bot started")


@bot.event
async def on_member_join(member):
    welcome_messages = [
        f"What's up {member.name}. Welcome to this Discord server, where everybody shares the same interest in playing Jackbox games."
    ]

    await member.create_dm()
    await member.dm_channel.send(random.choice(welcome_messages))


# jedes mal, wenn reaction hinzugefügt wird, schauen, ob in den channels genug leute sind und mach dann entsprechende channeladministrationen
@bot.event
async def on_reaction_add(reaction, user):
    print(f"added {reaction.message} reaction, by {user.name}")
    await reaction.message.channel.send(f"added {reaction.emoji} reaction, by {user.name}")


@bot.event
async def on_voice_state_update(member, before, after):
    # switch
    if before.channel != after.channel and before.channel is not None and after.channel is not None:
        print(
            f"user {member.name} switched from {before.channel.name} to channel {after.channel.name}")
    # leave
    elif before.channel is not None and after.channel is None:
        print(f"user {member.name} left channel {before.channel.name}")
    # join
    elif before.channel is None and after.channel is not None:
        print(f"user {member.name} joined channel {after.channel.name}")


@bot.event
async def on_command_error(ctx, error):
    print(f"Seems like the command was wrong: {error}")


@bot.command(name="wtp", help="Searching for some companions to play with.\n Usage... ")
@bot_command_channel("searching-for-players")
async def want_to_play(ctx, channelname: str = None, channelsize=10):
    if len(get_current_jackbox_vcs()) >= maximum_channel_number:
        await ctx.send(f"Sorry {ctx.author.mention}, but the maximum amount of voicechats is reached, but you can try to join an existing one or try later")
        return

    if channelsize > maximum_channel_size:
        channelsize = 16
        await ctx.send(f"Your channelsize exceeded the maximum size and was set to 16")
    if channelsize < minimum_channel_size:
        channelsize = 2
        await ctx.send(f"Your channelsize is below the minimum and was set to 2")

    user = user_already_in_any_queue(ctx.author)

    # check, if user is already in any queue
    if user is not None:
        await ctx.send(f"{ctx.author.mention} you are already in the **{user.queue.name}** queue")
        return

    # check if the queue already exists
    if channelname is None:
        curr_queue = add_user_to_queue(ctx.author, DEFAULT_QUEUE_NAME)
        if curr_queue.status() == IndividQueue.FULL:
            current_smallest_number = get_smallest_available_channelnumber()
            await ctx.guild.create_voice_channel(f"jackbox {current_smallest_number}", category=discord.utils.find(lambda c: JACKBOX_VOICECHANNEL_CATEGORY == c.name, get_current_guild().categories), user_limit=channelsize)
            await ctx.send(queue_full_response(curr_queue))
            curr_queue.userlist.clear()
        else:
            await ctx.send(f"There are currently **{len(get_queue(DEFAULT_QUEUE_NAME))}** people waiting in **{get_queue(DEFAULT_QUEUE_NAME).name}** queue")
    else:
        opt_queue = get_queue(channelname.lower())
        if opt_queue is None:
            if queue_name_is_valid(channelname):
                add_queue(ctx.author, channelname, channelsize)
                await ctx.send(f"{ctx.author.mention} created the queue: **{channelname}**. Feel free to join!")
            else:
                await ctx.send(f"Sorry {ctx.author.mention}, but the channelname **{channelname}** is not allowed")
                return 
        else:
            curr_queue = add_user_to_queue(ctx.author, channelname)
            if curr_queue.status() == IndividQueue.FULL:
                await ctx.guild.create_voice_channel(channelname, category=discord.utils.find(lambda c: JACKBOX_VOICECHANNEL_CATEGORY == c.name, get_current_guild().categories), user_limit=channelsize)
                await ctx.send(queue_full_response(curr_queue))
                delete_queue(curr_queue)
            else:
                await ctx.send(f"There are currently **{len(get_queue(channelname))}** people waiting in the **{get_queue(channelname).name}** queue")


@bot.command(name="wtp-info", help="show the number of people, currently searching for players")
@bot_command_channel("searching-for-players")
async def want_to_play_info(ctx, queue_name: str = None):
    response = "```"
    response += "The following queues are currently available\n\n"
    for index, queue in enumerate(wtp_queues):
        response += f"{index + 1}. {queue.name}:\n"
        for user in queue.userlist:
            response += f"{user.member.name}\n"
        response += f"waiting for {queue.min_req - len(queue)} more people to start\n\n"
    response += "```"
    await ctx.send(response)


@bot.command(name="wtp-leave", help="leave the current queue")
@bot_command_channel("searching-for-players")
async def leave_queue(ctx):

    user = user_already_in_any_queue(ctx.author)
    if user is not None:
        user.queue.remove(user)
        if user.queue.status() == IndividQueue.EMPTY and user.queue.name != DEFAULT_QUEUE_NAME:
            wtp_queues.remove(user.queue)
        user.queue = None


@bot.command(name="help")
async def help(ctx):
    embed = discord.Embed(colour=discord.Colour.gold())
    embed.set_author(
        name="Help table"
    )
    embed.add_field(
        name="wtp-help", 
        value="shows a table with all commands", 
        inline=False
    )
    embed.add_field(
        name="<font color=\"red\">This</font></HTML>", 
        value="""
            wtp: enter a waiting queue
            wtp [queuename]: joins a queue with the name [queuename] or creates a new one if not existing
            wtp [queuename] [queuelength]: create a new queue with [queuename] and a maximal size of [queuelength].
        """, 
        inline=False
    )
    embed.add_field(
        name="wtp-leave", 
        value="leaves a queue, if already in one", 
        inline=False
    )
    embed.add_field(
        name="wtp-info", 
        value="shows information about existing queues and personal belongings"
    )
    embed.description = ""
    await ctx.author.send(embed=embed)

bot.run(TOKEN)
