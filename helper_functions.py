import discord
from discord.ext import commands


'''
checks, if the bot command was written in the intended channel
'''


def bot_command_channel(channels="searching-for-players"):
    async def wrapper_for_check(ctx, *args):
        for channel in channels:
            if ctx.message.channel.name == channel:
                return True
        if ctx.message.channel.name != channel:
            await ctx.send(f"{ctx.message.author.mention}, this botcommand belongs into {discord.utils.find(lambda c: channel == c.name, ctx.message.guild.channels).mention}", delete_after=20)
            await ctx.message.delete(delay=20)

            return False

    return commands.check(wrapper_for_check)
