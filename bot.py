import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from commands import setup_music_commands

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")

# Setup bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"-----------------------------------")
    print(f"Logged in as: {bot.user.name} ({bot.user.id})")
    print(f"Discord.py Version: {discord.__version__}")
    print(f"-----------------------------------")
    
    # Load and register music slash commands
    await setup_music_commands(bot)
    
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash commands globally.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

@bot.event
async def on_guild_join(guild):
    print(f"Bot joined a new server: {guild.name} (ID: {guild.id})")

@bot.event
async def on_guild_remove(guild):
    print(f"Bot left server: {guild.name} (ID: {guild.id})")

# Run the bot
if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: Bot token not found! Please check your .env file.")
    else:
        bot.run(TOKEN)