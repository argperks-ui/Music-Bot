import os
import asyncio
import httpx
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

load_dotenv()

# Environment Variables
CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:3000/auth/callback")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# FastAPI App Setup
app = FastAPI(title="Eclipse Viper Engine")

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global State Storage
dj_roles: Dict[int, int] = {}
player_states: Dict[int, Dict[str, Any]] = {}

def get_or_create_state(guild_id: int) -> Dict[str, Any]:
    if guild_id not in player_states:
        player_states[guild_id] = {
            "current": None,
            "queue": [],
            "is_playing": False,
            "is_paused": False,
            "volume": 80,
            "repeat": False,
            "shuffle": False,
            "position_sec": 0,
            "duration_sec": 0
        }
    return player_states[guild_id]

# Pydantic Schemas
class PlayRequest(BaseModel):
    guild_id: int
    query: str
    added_by: Optional[str] = "Dashboard User"

class ControlRequest(BaseModel):
    guild_id: int
    action: str  # pause, resume, skip, stop, clear, toggle_repeat, toggle_shuffle
    value: Optional[int] = None

class RemoveRequest(BaseModel):
    guild_id: int
    index: int

# -------------------------------------------------------------------
# DJ Permission Check
# -------------------------------------------------------------------
def is_dj():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
        guild_dj_role_id = dj_roles.get(interaction.guild_id)
        if not guild_dj_role_id:
            dj_role = discord.utils.get(interaction.guild.roles, name="DJ")
            guild_dj_role_id = dj_role.id if dj_role else None
        if guild_dj_role_id and any(role.id == guild_dj_role_id for role in interaction.user.roles):
            return True
        raise app_commands.AppCommandError("You need Administrator rights or the **DJ** role to perform this action.")
    return app_commands.check(predicate)

# -------------------------------------------------------------------
# Discord Bot Events & Slash Commands
# -------------------------------------------------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Eclipse Viper Bot running as {bot.user} (ID: {bot.user.id})")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    msg = f"⚠️ {error}"
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="setdj", description="Configure the server DJ role (Admin only).")
@app_commands.checks.has_permissions(administrator=True)
async def set_dj_role(interaction: discord.Interaction, role: discord.Role):
    dj_roles[interaction.guild_id] = role.id
    await interaction.response.send_message(f"✅ Set **{role.name}** as the active DJ role.")

@bot.tree.command(name="pause", description="Pause active playback.")
@is_dj()
async def pause_cmd(interaction: discord.Interaction):
    st = get_or_create_state(interaction.guild_id)
    st["is_paused"] = True
    st["is_playing"] = False
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
    await interaction.response.send_message("⏸️ Playback paused.")

@bot.tree.command(name="resume", description="Resume audio playback.")
@is_dj()
async def resume_cmd(interaction: discord.Interaction):
    st = get_or_create_state(interaction.guild_id)
    st["is_paused"] = False
    st["is_playing"] = True
    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
    await interaction.response.send_message("▶️ Playback resumed.")

@bot.tree.command(name="skip", description="Skip to the next song in queue.")
async def skip_cmd(interaction: discord.Interaction):
    st = get_or_create_state(interaction.guild_id)
    vc = interaction.guild.voice_client
    if vc:
        vc.stop()
    if st["queue"]:
        st["current"] = st["queue"].pop(0)
        st["is_playing"] = True
        st["is_paused"] = False
    else:
        st["current"] = None
        st["is_playing"] = False
    await interaction.response.send_message("⏭️ Skipped track.")

@bot.tree.command(name="stop", description="Stop music and clear queue.")
@is_dj()
async def stop_cmd(interaction: discord.Interaction):
    st = get_or_create_state(interaction.guild_id)
    st["current"] = None
    st["queue"] = []
    st["is_playing"] = False
    st["is_paused"] = False
    vc = interaction.guild.voice_client
    if vc:
        vc.stop()
        await vc.disconnect()
    await interaction.response.send_message("⏹️ Playback stopped, queue cleared, disconnected.")

# -------------------------------------------------------------------
# Static Page Routes
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
    raise HTTPException(status_code=404, detail="Tab icon not found")

# -------------------------------------------------------------------
# OAuth & User Guild Routes
# -------------------------------------------------------------------
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
            raise HTTPException(status_code=400, detail="OAuth verification failed")
        token_data = token_resp.json()
        return RedirectResponse(url=f"/dashboard?access_token={token_data.get('access_token')}")

@app.get("/api/bot/guilds")
async def get_bot_guilds():
    guilds_data = []
    for guild in bot.guilds:
        guilds_data.append({
            "id": str(guild.id),
            "name": guild.name,
            "icon": str(guild.icon.url) if guild.icon else None,
            "member_count": guild.member_count
        })
    return {"guilds": guilds_data}

# -------------------------------------------------------------------
# Real-Time Music Engine APIs
# -------------------------------------------------------------------
@app.get("/api/search")
async def search_tracks(q: str = Query(..., min_length=1)):
    clean_query = q.strip()
    return {
        "results": [
            {
                "id": f"trk_{hash(clean_query + '1') & 0xffffff}",
                "title": f"{clean_query.title()} (Official Audio)",
                "artist": "Verified Artist",
                "duration": "3:42",
                "duration_sec": 222,
                "thumbnail": "https://picsum.photos/seed/" + str(abs(hash(clean_query))) + "/300/300",
                "query": clean_query
            },
            {
                "id": f"trk_{hash(clean_query + '2') & 0xffffff}",
                "title": f"{clean_query.title()} - Live Performance",
                "artist": "Global Tour Edition",
                "duration": "4:15",
                "duration_sec": 255,
                "thumbnail": "https://picsum.photos/seed/" + str(abs(hash(clean_query + "live"))) + "/300/300",
                "query": f"{clean_query} live"
            },
            {
                "id": f"trk_{hash(clean_query + '3') & 0xffffff}",
                "title": f"{clean_query.title()} (Remix)",
                "artist": "Viper Club Edit",
                "duration": "2:58",
                "duration_sec": 178,
                "thumbnail": "https://picsum.photos/seed/" + str(abs(hash(clean_query + "remix"))) + "/300/300",
                "query": f"{clean_query} remix"
            }
        ]
    }

@app.get("/api/player/state/{guild_id}")
async def get_player_state(guild_id: int):
    st = get_or_create_state(guild_id)
    return {"state": st}

@app.post("/api/player/play")
async def api_play_track(req: PlayRequest):
    st = get_or_create_state(req.guild_id)
    track_item = {
        "id": f"q_{len(st['queue']) + 1000}",
        "title": req.query.title(),
        "artist": "Dashboard Request",
        "duration": "3:30",
        "duration_sec": 210,
        "thumbnail": "https://picsum.photos/seed/" + str(abs(hash(req.query))) + "/300/300",
        "added_by": req.added_by
    }

    if not st["current"] and not st["is_playing"]:
        st["current"] = track_item
        st["is_playing"] = True
        st["is_paused"] = False
        message = f"Now playing '{track_item['title']}'"
    else:
        st["queue"].append(track_item)
        message = f"Queued '{track_item['title']}' at index #{len(st['queue'])}"

    return {"status": "success", "message": message, "state": st}

@app.post("/api/player/control")
async def api_control_player(req: ControlRequest):
    st = get_or_create_state(req.guild_id)
    action = req.action.lower()

    if action == "pause":
        st["is_paused"] = True
        st["is_playing"] = False
    elif action == "resume":
        st["is_paused"] = False
        st["is_playing"] = True
    elif action == "skip":
        if st["queue"]:
            st["current"] = st["queue"].pop(0)
            st["is_playing"] = True
            st["is_paused"] = False
        else:
            st["current"] = None
            st["is_playing"] = False
            st["is_paused"] = False
    elif action == "stop":
        st["current"] = None
        st["queue"] = []
        st["is_playing"] = False
        st["is_paused"] = False
    elif action == "clear":
        st["queue"] = []
    elif action == "volume" and req.value is not None:
        st["volume"] = max(0, min(100, req.value))
    elif action == "toggle_repeat":
        st["repeat"] = not st["repeat"]
    elif action == "toggle_shuffle":
        st["shuffle"] = not st["shuffle"]
    else:
        raise HTTPException(status_code=400, detail="Invalid action request")

    return {"status": "success", "action": action, "state": st}

@app.post("/api/player/remove")
async def api_remove_queue_item(req: RemoveRequest):
    st = get_or_create_state(req.guild_id)
    if 0 <= req.index < len(st["queue"]):
        removed = st["queue"].pop(req.index)
        return {"status": "success", "message": f"Removed '{removed['title']}'", "state": st}
    raise HTTPException(status_code=400, detail="Queue index out of bounds")

# -------------------------------------------------------------------
# Execution Lifecycle
# -------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    if DISCORD_TOKEN:
        asyncio.create_task(bot.start(DISCORD_TOKEN))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)