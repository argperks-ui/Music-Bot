import os
import asyncio
import aiohttp
import uvicorn
import discord
from discord.ext import commands
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# --- 1. FASTAPI DASHBOARD & OAUTH2 SERVER ---
app = FastAPI()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL")
DISCORD_API = "https://discord.com/api/v10"

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

# Serve Next.js static export from viper-audio-core/out
if os.path.exists("viper-audio-core/out"):
    app.mount("/_next", StaticFiles(directory="viper-audio-core/out/_next"), name="next")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = f"viper-audio-core/out/{full_path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse("viper-audio-core/out/index.html")

# --- 2. DISCORD BOT BOT INITIALIZATION ---
class CyberMusicBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("commands")
        print("⚙️ Loaded commands extension.")

intents = discord.Intents.default()
intents.message_content = True
bot = CyberMusicBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user} | Commands synced.")

# --- 3. DUAL-PROCESS RUNNER ---
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