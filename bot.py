import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Central state shared with the web dashboard
bot_state = {
    "policies": {
        "main": {"role": "DJ", "admin": True, "skip": True, "announce": True},
        "test": {"role": "Music Master", "admin": True, "skip": True, "announce": False},
        "vip": {"role": "DJ", "admin": False, "skip": True, "announce": True}
    },
    "player": {
        "playing": True,
        "current_track": {
            "title": "Eclipse Viper",
            "artist": "Neon Sovereign",
            "requested_by": "@admin"
        },
        "queue": [
            {"title": "Synthwave Drift", "artist": "Midnight Circuit", "requested_by": "@lena"},
            {"title": "Cyberpunk Beats Vol 3", "artist": "District 9", "requested_by": "@ravi"},
            {"title": "Low-Fi Chill Beats", "artist": "Cozy Static", "requested_by": "@mira"}
        ]
    }
}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")