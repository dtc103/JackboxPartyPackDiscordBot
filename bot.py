# bot.py
import os
import discord
import random

from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")
WORKING_CHANNEL = os.getenv("WORKING_CHANNEL_ID")
JACKBOX_VOICECHANNEL_CATEGORY = os.getenv("JACKBOX_VOICECHANNEL_CATEGORY")

# client = discord.Client()
bot = commands.Bot(command_prefix="!")


# @bot.event
# async def on_message(message):
# if message.author == bot.user:
#     return

# channel_id = discord.utils.find(
#     lambda channel: channel.name == message.channel.name, message.guild.channels)

# await message.channel.send(f"The message {message.content} was sent in {channel_id.mention}")

##################### HELPER FUNCTIONS ###########################
def get_current_guild():
    return discord.utils.find(lambda g: GUILD == g.name, bot.guilds)


def get_jackbox_voicechannels():
    return discord.utils.find(lambda c: JACKBOX_VOICECHANNEL_CATEGORY == c.name.lower(), get_current_guild().categories).channels


def manage_channels():
    pass


def bot_command_channel(channel="searching-for-players"):
    async def wrapper_for_check(ctx):
        if ctx.message.channel.name != channel:
            await ctx.send(f"{ctx.message.author.mention}, this botcommand belongs into {discord.utils.find(lambda c: channel == c.name, ctx.message.guild.channels).mention}", delete_after=10)
            await ctx.message.delete(delay=10)

            return False
        else:
            return True

    return commands.check(wrapper_for_check)

##################### EVENTS AND COMMANDS #######################################


@bot.event
async def on_ready():
    guild = get_current_guild()

    members = guild.members
    roles = guild.roles


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

wtp_player_list = []
smallest_possible_number_of_channel = 3
current_smallest_number = 3
maximum_channel_number = 20


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
    print("ERROR OCCURED")


# wenn nach x minuten kein neuer user mehr dazu kommt, muss die liste gelehrt werden
@bot.command(name="wtp", help="Searching for some companions to play with")
@bot_command_channel("searching-for-players")
async def want_to_play(ctx):
    minimum_amount_of_players = 4

    if ctx.message.author in wtp_player_list:
        await ctx.send(f"Sorry {ctx.message.author.mention}, but you are already in the queue. Wait for other players to show up.")
    else:
        wtp_player_list.append(ctx.message.author)
        await ctx.send(f"{len(wtp_player_list)} players wants to play currently")

    if(len(wtp_player_list) >= minimum_amount_of_players):
        reply_message = "Hey "
        for index, player in enumerate(wtp_player_list):
            if index == len(wtp_player_list) - 1:
                reply_message += f" and {player.mention}"
            else:
                reply_message += f", {player.mention}"
        reply_message += ", finally you are enough players for a new Jackbox session. Have fun!!!"

        manage_channels(wtp_player_list)

        await ctx.send(reply_message)

        wtp_player_list.clear()


@bot.command(name="wtp-info", help="show the number of people, currently searching for players")
@bot_command_channel("searching-for-players")
async def want_to_play_info(ctx):
    reply_message = ""
    if(len(wtp_player_list) == 1):
        reply_message += f"```This {len(wtp_player_list)} player is currently waiting for more people:\n"
    else:
        reply_message += f"```These {len(wtp_player_list)} players are currently waiting for more people:\n"
    for player in wtp_player_list:
        reply_message += player.name + "\n"
    reply_message += "```"
    await ctx.send(reply_message)


bot.run(TOKEN)
