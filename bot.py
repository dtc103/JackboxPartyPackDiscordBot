# bot.py
import os
import discord
import random
import asyncio
import typing
import re

from dotenv import load_dotenv
from discord.ext import commands, tasks

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")
WORKING_CHANNEL = os.getenv("WORKING_CHANNEL_ID")
JACKBOX_VOICECHANNEL_CATEGORY = os.getenv("JACKBOX_VOICECHANNEL_CATEGORY")
DEFAULT_QUEUE = os.getenv("DEFAULT_QUEUE")
DEFAULT_QUEUE_MINIMUM_REQ = 4

# client = discord.Client()
bot = commands.Bot(command_prefix="!")

# because jackbox 1 and jackbox 2 are fixed channels
smallest_poss_number_of_channel = 3
# if unnamed queue, just add a number
current_smallest_number = 3
# maximum amount of jackbox voicechannels
maximum_channel_number = 20

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

    def __len__(self):
        return len(self.userlist)

    def __eq__(self, other):
        return self.name == other.name


##################### HELPER FUNCTIONS ###########################


def get_current_guild():
    return discord.utils.find(lambda g: GUILD == g.name, bot.guilds)


def get_current_jackbox_vcs():
    return discord.utils.find(lambda c: JACKBOX_VOICECHANNEL_CATEGORY == c.name, get_current_guild().categories).channels


async def manage_channels():
    jack_calls = get_current_jackbox_vcs()
    for vc in jack_calls:
        if vc.name == "jackbox 1" or vc.name == "jackbox 2":
            continue
        else:
            if len(vc.members) == 0:
                await vc.delete(reason="Empty")


def bot_command_channel(channel="searching-for-players"):
    async def wrapper_for_check(ctx, *args):
        if ctx.message.channel.name != channel:
            await ctx.send(f"{ctx.message.author.mention}, this botcommand belongs into {discord.utils.find(lambda c: channel == c.name, ctx.message.guild.channels).mention}", delete_after=20)
            await ctx.message.delete(delay=20)

            return False
        else:
            return True

    return commands.check(wrapper_for_check)


def queue_name_is_valid(channelname: str):
    if re.match("jackbox \d+", channelname.lower()) or channelname.lower() == "default" or channelname == DEFAULT_QUEUE:
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
    if queue_name == DEFAULT_QUEUE:
        return wtp_queues[0]

    for queue in wtp_queues:
        if queue_name == queue.name:
            return queue
    return None

# adds a user to a exisitng queue


def add_user_to_queue(member: discord.Member, queuename: str):
    queue = get_queue(queuename)
    new_user = QueueUser(member, queue)
    queue.append(new_user)
    return queue

# creates a new queue and adds the originator to it


def add_queue(originator: discord.Member, queuename: str, min_req: int):
    new_originator = QueueUser(originator, None)
    queue = IndividQueue(new_originator, queuename, min_req)
    new_originator.queue = queue
    wtp_queues.append(queue)
    return queue

# checks if a queue has enough member to create a party


def queue_is_full(queuename):
    if isinstance(queuename, IndividQueue):
        return len(queuename) >= queuename.min_req
    elif isinstance(queuename, str):
        queue = get_queue(queuename)
        if len(queue) >= queue.min_req:
            return True
        else:
            return False

# create the response message, if the queue is full


def queue_full_response(queue: IndividQueue):
    response = "Hey "
    for index, queue_user in enumerate(queue.userlist):
        response += f"{queue_user.member.mention}, "

    response += "finally you are enough players for a new party. Have fun!!!"

    return response


def delete_queue():
    pass

##################### EVENTS AND COMMANDS #######################################

# async def check_queue():
#     while not bot.is_closed():
#         print("henlo")
#         await asyncio.sleep(5)


@bot.event
async def on_ready():
    wtp_queues.append(IndividQueue(
        None, DEFAULT_QUEUE, DEFAULT_QUEUE_MINIMUM_REQ))
    await manage_channels()
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
    print("Seems like the command was wrong")


@bot.command(name="wtp", help="Searching for some companions to play with.\n Usage... ")
@bot_command_channel("searching-for-players")
async def want_to_play(ctx, channelname: str = None, channelsize=10):
    user = user_already_in_any_queue(ctx.author)

    # check, if user is already in a queue
    if user is not None:
        await ctx.send(f"{ctx.author.mention} you are already in the **{user.queue.name}** queue")
        return

    # check if the queue already exists
    if channelname is None:
        curr_queue = add_user_to_queue(ctx.author, DEFAULT_QUEUE)
        if queue_is_full(curr_queue):
            await ctx.send(queue_full_response(curr_queue))
        else:
            await ctx.send(f"There are currently **{len(get_queue(DEFAULT_QUEUE))}** people waiting in **{get_queue(DEFAULT_QUEUE).name}** queue")
    else:
        opt_queue = get_queue(channelname)
        if opt_queue is None:
            add_queue(ctx.author, channelname, channelsize)
            await ctx.send(f"{ctx.author.mention} created the queue: **{channelname}**. Feel free to join!")
        else:
            curr_queue = add_user_to_queue(ctx.author, channelname)
            if queue_is_full(curr_queue):
                await ctx.send(queue_full_response(curr_queue))
                delete_queue(curr_queue)
            else:
                await ctx.send(f"There are currently **{len(get_queue(channelname))}** people waiting in the **{get_queue(channelname).name}** queue")

        # if(len(wtp_player_list) >= minimum_amount_of_players):
        #     reply_message = "Hey "
        #     for index, player in enumerate(wtp_player_list):
        #         if index == len(wtp_player_list) - 1:
        #             reply_message += f" and {player.mention}"
        #         else:
        #             reply_message += f", {player.mention}"
        #     reply_message += ", finally you are enough players for a new Jackbox session. Have fun!!!"

        #     # TODO add new channel

        #     await ctx.send(reply_message)

        #     wtp_player_list.clear()


@bot.command(name="wtp-info", help="show the number of people, currently searching for players")
@bot_command_channel("searching-for-players")
async def want_to_play_info(ctx, queue_name: str = None):
    reply_message = ""
    if(len(wtp_player_list) == 1):
        reply_message += f"```This {len(wtp_player_list)} player is currently waiting for more people:\n"
    else:
        reply_message += f"```These {len(wtp_player_list)} players are currently waiting for more people:\n"
    for player in wtp_player_list:
        reply_message += player.name + "\n"
    reply_message += "```"
    await ctx.send(reply_message)


@bot.command(name="wtp-switch", help="switch to another queue")
@bot_command_channel("searching-for-players")
async def switch_queue(ctx, queue_name: str):
    pass


@bot.command(name="wtp-leave", help="leave the current queue")
@bot_command_channel("searching-for-players")
async def leave_queue(ctx):
    if ctx.author in wtp_player_list:
        wtp_all_queue_members.remove(ctx.author)


bot.run(TOKEN)
