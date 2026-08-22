import os
import asyncio
import aiohttp
import uvicorn
import discord
from discord.ext import commands
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# --- FASTAPI DASHBOARD & OAUTH2 SERVER ---
app = FastAPI(title="Git Music API")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")
DISCORD_API = "https://discord.com/api/v10"

# --- OAUTH2 AUTHENTICATION ---
@app.get("/api/auth/login")
async def discord_login():
    oauth_url = (
        f"{DISCORD_API}/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={CALLBACK_URL}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
    )
    return RedirectResponse(url=oauth_url)

@app.get("/auth/callback")
async def discord_callback(code: str):
    token_payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": CALLBACK_URL,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{DISCORD_API}/oauth2/token", data=token_payload, headers=headers) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=400, detail="Failed to retrieve token from Discord.")
            token_data = await resp.json()

        access_token = token_data.get("access_token")

    response = RedirectResponse(url="/")
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=True
    )
    return response

# --- WEBDASHBOARD CONTROL API ENDPOINTS ---
@app.get("/api/player/{guild_id}")
async def get_player_state(guild_id: int):
    cog = bot.get_cog("MusicCommands")
    if not cog:
        raise HTTPException(status_code=500, detail="Music engine not loaded.")
    
    current = cog.now_playing.get(guild_id)
    queue = cog.queues.get(guild_id, [])
    volume = int(cog.guild_volume.get(guild_id, 0.5) * 100)
    loop = cog.loop_modes.get(guild_id, "off")

    return {
        "guild_id": guild_id,
        "now_playing": current,
        "queue": queue,
        "volume": volume,
        "loop": loop
    }

@app.post("/api/player/{guild_id}/control")
async def player_control(guild_id: int, request: Request):
    data = await request.json()
    action = data.get("action")
    val = data.get("value")

    guild = bot.get_guild(guild_id)
    if not guild or not guild.voice_client:
        raise HTTPException(status_code=400, detail="Bot not connected to voice in this server.")

    vc = guild.voice_client
    cog = bot.get_cog("MusicCommands")

    if action == "pause" and vc.is_playing():
        vc.pause()
    elif action == "resume" and vc.is_paused():
        vc.resume()
    elif action == "skip" and (vc.is_playing() or vc.is_paused()):
        vc.stop()
    elif action == "volume" and val is not None:
        level = max(0.0, min(1.0, float(val) / 100.0))
        cog.guild_volume[guild_id] = level
        if vc.source:
            vc.source.volume = level

    return {"status": "success", "action": action}

# --- STATIC FILE SERVING FOR NEXT.JS FRONTEND ---
if os.path.exists("viper-audio-core/out"):
    app.mount("/_next", StaticFiles(directory="viper-audio-core/out/_next"), name="next")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = f"viper-audio-core/out/{full_path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse("viper-audio-core/out/index.html")

# --- DISCORD BOT INITIALIZATION ---
class GitMusicBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("commands")
        print("⚙️ Loaded commands extension for Git Music.")

intents = discord.Intents.default()
intents.message_content = True
bot = GitMusicBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user} (Git Music) | Commands synced.")

# --- DUAL-PROCESS RUNNER ---
async def start_web_server():
    port = int(os.environ.get("PORT", 3000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    asyncio.create_task(start_web_server())
    await bot.start(os.environ.get("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())