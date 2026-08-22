import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import dashboard

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Load commands extension from commands.py
        await self.load_extension("commands")
        await self.tree.sync()
        print("Commands extension loaded and synced successfully!")

bot = MusicBot()

# Start dashboard server in the background
dashboard.start_dashboard(bot)

@bot.event
async def on_ready():
    dashboard.bot_status = "Online"
    dashboard.guild_count = len(bot.guilds)
    dashboard.add_log(f"Bot logged in successfully as {bot.user}")
    print(f'Logged in as {bot.user} successfully!')

bot.run(TOKEN)