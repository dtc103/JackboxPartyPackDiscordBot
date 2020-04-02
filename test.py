import dotenv
from dotenv import load_dotenv
import os

import discord
from discord.ext import commands

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='!')

bot.run(TOKEN)
