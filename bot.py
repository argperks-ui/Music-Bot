import os
import asyncio
import discord
from discord.ext import commands
from aiohttp import web

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def start_health_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Render Music Bot Online"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 3000))
    await web.TCPSite(runner, '0.0.0.0', port).start()

@bot.event
async def on_ready():
    # Load the Cog from commands.py
    await bot.load_extension("commands")
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user} | All commands synchronized from commands.py!")

async def main():
    asyncio.create_task(start_health_server())
    await bot.start(os.environ.get("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())