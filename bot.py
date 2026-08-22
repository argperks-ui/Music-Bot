import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.load_extension("commands")
        await self.tree.sync()
        print("Music commands extension synced successfully!")

bot = MusicBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} successfully!')

bot.run(TOKEN)