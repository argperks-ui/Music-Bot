import os
import asyncio
import httpx
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

load_dotenv()

# Environment Config
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:3000/auth/callback")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# FastAPI App
app = FastAPI(title="Git Music Core")

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# In-Memory Storage for Guild Settings & Queues
dj_roles = {}  # {guild_id: role_id}
queues = {}    # {guild_id: [tracks]}

# -------------------------------------------------------------------
# DJ Role Slash Command Check
# -------------------------------------------------------------------
def is_dj():
    """Custom slash command check for Admin, DJ role, or Guild Owner."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        
        guild_dj_role_id = dj_roles.get(interaction.guild_id)
        if not guild_dj_role_id:
            dj_role = discord.utils.get(interaction.guild.roles, name="DJ")
            guild_dj_role_id = dj_role.id if dj_role else None

        if guild_dj_role_id and any(role.id == guild_dj_role_id for role in interaction.user.roles):
            return True

        raise app_commands.AppCommandError("You need the **DJ** role or Administrator permissions to use this command.")
    return app_commands.check(predicate)

# -------------------------------------------------------------------
# Bot Events & Error Handling
# -------------------------------------------------------------------
@bot.event
async def on_ready():
    # Sync slash commands globally with Discord
    await bot.tree.sync()
    print(f"Bot online as {bot.user} (ID: {bot.user.id}) - Slash commands synced.")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    msg = f"⚠️ {error}"
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)

# -------------------------------------------------------------------
# Slash Commands
# -------------------------------------------------------------------
@bot.tree.command(name="setdj", description="Assign the official DJ role for music commands (Admin only).")
@app_commands.checks.has_permissions(administrator=True)
async def set_dj_role(interaction: discord.Interaction, role: discord.Role):
    dj_roles[interaction.guild_id] = role.id
    await interaction.response.send_message(f"✅ Set **{role.name}** as the official DJ role.")

@bot.tree.command(name="pause", description="Pause current music playback (DJ Only).")
@is_dj()
async def pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸️ Playback paused.")
    else:
        await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)

@bot.tree.command(name="resume", description="Resume paused music playback (DJ Only).")
@is_dj()
async def resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ Playback resumed.")
    else:
        await interaction.response.send_message("Playback is not paused.", ephemeral=True)

@bot.tree.command(name="stop", description="Stop playback, clear queue, and leave voice channel (DJ Only).")
@is_dj()
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        queues[interaction.guild_id] = []
        vc.stop()
        await vc.disconnect()
        await interaction.response.send_message("⏹️ Stopped playback, cleared queue, and left the voice channel.")
    else:
        await interaction.response.send_message("The bot is not in a voice channel.", ephemeral=True)

@bot.tree.command(name="clear", description="Clear all queued tracks (DJ Only).")
@is_dj()
async def clear_queue(interaction: discord.Interaction):
    queues[interaction.guild_id] = []
    await interaction.response.send_message("🗑️ Cleared the music queue.")

@bot.tree.command(name="skip", description="Skip the current playing track.")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        return await interaction.response.send_message("Nothing to skip.", ephemeral=True)

    user = interaction.user
    is_author_dj = (
        user.guild_permissions.administrator 
        or user.id == interaction.guild.owner_id 
        or any(r.id == dj_roles.get(interaction.guild_id) for r in user.roles)
    )

    vc.stop()
    if is_author_dj:
        await interaction.response.send_message("⏭️ **DJ Force Skipped** the track.")
    else:
        await interaction.response.send_message("⏭️ Skipped current track.")

# -------------------------------------------------------------------
# FastAPI Web & OAuth Routes
# -------------------------------------------------------------------
@app.get("/")
async def serve_index():
    return FileResponse("index.html")

@app.get("/login")
async def serve_login():
    return FileResponse("login.html")

@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse("Dashboard/dashboard.html")

@app.get("/full-logo.png")
async def serve_logo():
    if os.path.exists("full-logo.png"):
        return FileResponse("full-logo.png")
    raise HTTPException(status_code=404, detail="Logo not found")

@app.get("/tab-icon.png")
async def serve_tab_icon():
    if os.path.exists("tab-icon.png"):
        return FileResponse("tab-icon.png")
    raise HTTPException(status_code=404, detail="Icon not found")

@app.get("/api/discord/login")
async def discord_login():
    url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={CALLBACK_URL}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
    )
    return RedirectResponse(url)

@app.get("/auth/callback")
async def discord_callback(code: str):
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": CALLBACK_URL,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with httpx.AsyncClient() as client:
        token_resp = await client.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="OAuth failed")
        
        token_data = token_resp.json()
        user_resp = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {token_data.get('access_token')}"}
        )
        if user_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve user profile")

    return RedirectResponse(url="/dashboard")

# -------------------------------------------------------------------
# Concurrent Execution (FastAPI + Discord Bot)
# -------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    if DISCORD_TOKEN:
        asyncio.create_task(bot.start(DISCORD_TOKEN))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)