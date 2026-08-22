import asyncio
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
import discord
from discord.ext import commands

# --- FastAPI Initialization ---
app = FastAPI(title="Git Music Bot Dashboard")

@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "bot_ready": bot.is_ready() if 'bot' in globals() else False
    }

# --- Mount Static Frontend ---
dashboard_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "Git-Music-Dashboard", "out"))

print(f"🔍 Checking dashboard path: {dashboard_path}")

if os.path.exists(dashboard_path) and os.listdir(dashboard_path):
    print("✅ Dashboard folder found! Mounting to '/'...")
    app.mount("/", StaticFiles(directory=dashboard_path, html=True), name="dashboard")
else:
    print("❌ Dashboard static folder NOT found or empty.")
    @app.get("/")
    async def root_fallback():
        return {
            "error": "Dashboard build not found",
            "expected_path": dashboard_path
        }

# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as: {bot.user} (ID: {bot.user.id})")

# --- Concurrent Execution ---
async def main():
    token = os.getenv("DISCORD_TOKEN")
    port = int(os.getenv("PORT", 3000))

    config = uvicorn.Config(app=app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)

    if token:
        await asyncio.gather(
            server.serve(),
            bot.start(token)
        )
    else:
        await server.serve()

if __name__ == "__main__":
    asyncio.run(main())