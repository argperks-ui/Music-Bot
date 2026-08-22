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

CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:3000/auth/callback")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

app = FastAPI(title="Eclipse Viper Engine Core")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# State Engine Storage
dj_roles: Dict[int, int] = {}
guild_settings: Dict[int, Dict[str, Any]] = {}
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
            "bass_boost": False,
            "nightcore": False,
            "position_sec": 0,
            "duration_sec": 0,
            "logs": ["[SYS] Audio engine initialized successfully."]
        }
    return player_states[guild_id]

def get_or_create_settings(guild_id: int) -> Dict[str, Any]:
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {
            "prefix": "!",
            "auto_disconnect": True,
            "announce_songs": True,
            "dj_only_mode": False,
            "max_queue_len": 50,
            "default_volume": 80
        }
    return guild_settings[guild_id]

# Models
class PlayRequest(BaseModel):
    guild_id: int
    query: str
    added_by: Optional[str] = "Studio Console"

class ControlRequest(BaseModel):
    guild_id: int
    action: str
    value: Optional[int] = None

class RemoveRequest(BaseModel):
    guild_id: int
    index: int

class SettingsRequest(BaseModel):
    guild_id: int
    prefix: Optional[str] = "!"
    auto_disconnect: Optional[bool] = True
    announce_songs: Optional[bool] = True
    dj_only_mode: Optional[bool] = False

# Bot Commands
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"[SYSTEM] Eclipse Viper Core live as {bot.user}")

@bot.tree.command(name="setdj", description="Configure DJ Role.")
@app_commands.checks.has_permissions(administrator=True)
async def set_dj_role(interaction: discord.Interaction, role: discord.Role):
    dj_roles[interaction.guild_id] = role.id
    await interaction.response.send_message(f"[OK] Assigned {role.name} as DJ role.")

# Routes
@app.get("/")
async def serve_index():
    return FileResponse("index.html")

@app.get("/login")
async def serve_login():
    return FileResponse("login.html")

@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse("Dashboard/dashboard.html")

@app.get("/tab-icon.png")
async def serve_tab_icon():
    if os.path.exists("tab-icon.png"):
        return FileResponse("tab-icon.png")
    raise HTTPException(status_code=404, detail="Icon not found")

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
    if not guilds_data:
        guilds_data.append({"id": "123456789012345678", "name": "Eclipse Main Guild", "member_count": 42})
    return {"guilds": guilds_data}

@app.get("/api/search")
async def search_tracks(q: str = Query(..., min_length=1)):
    clean = q.strip()
    return {
        "results": [
            {
                "id": f"trk_{hash(clean + '1') & 0xffffff}",
                "title": f"{clean.title()} (Master Cut)",
                "artist": "Verified Stream",
                "duration": "3:45",
                "thumbnail": f"https://picsum.photos/seed/{abs(hash(clean))}/300/300",
                "query": clean
            },
            {
                "id": f"trk_{hash(clean + '2') & 0xffffff}",
                "title": f"{clean.title()} (Viper Remix)",
                "artist": "Eclipse Audio Lab",
                "duration": "4:12",
                "thumbnail": f"https://picsum.photos/seed/{abs(hash(clean + 'remix'))}/300/300",
                "query": f"{clean} remix"
            }
        ]
    }

@app.get("/api/player/state/{guild_id}")
async def get_player_state(guild_id: int):
    st = get_or_create_state(guild_id)
    sett = get_or_create_settings(guild_id)
    return {"state": st, "settings": sett}

@app.post("/api/player/play")
async def api_play_track(req: PlayRequest):
    st = get_or_create_state(req.guild_id)
    track_item = {
        "id": f"q_{len(st['queue']) + 1000}",
        "title": req.query.title(),
        "artist": "Dashboard Stream",
        "duration": "3:30",
        "thumbnail": f"https://picsum.photos/seed/{abs(hash(req.query))}/300/300",
        "added_by": req.added_by
    }

    if not st["current"] and not st["is_playing"]:
        st["current"] = track_item
        st["is_playing"] = True
        st["is_paused"] = False
        st["logs"].append(f"[EXEC] Now playing '{track_item['title']}'")
    else:
        st["queue"].append(track_item)
        st["logs"].append(f"[QUEUE] Added '{track_item['title']}' at index #{len(st['queue'])}")

    return {"status": "success", "state": st}

@app.post("/api/player/control")
async def api_control_player(req: ControlRequest):
    st = get_or_create_state(req.guild_id)
    action = req.action.lower()

    if action == "pause":
        st["is_paused"] = True
        st["is_playing"] = False
        st["logs"].append("[CTRL] Playback paused.")
    elif action == "resume":
        st["is_paused"] = False
        st["is_playing"] = True
        st["logs"].append("[CTRL] Playback resumed.")
    elif action == "skip":
        if st["queue"]:
            st["current"] = st["queue"].pop(0)
            st["is_playing"] = True
            st["is_paused"] = False
            st["logs"].append(f"[CTRL] Skipped to '{st['current']['title']}'")
        else:
            st["current"] = None
            st["is_playing"] = False
            st["logs"].append("[CTRL] Skipped. Queue empty.")
    elif action == "clear":
        st["queue"] = []
        st["logs"].append("[CTRL] Queue stack wiped.")
    elif action == "volume" and req.value is not None:
        st["volume"] = max(0, min(100, req.value))
        st["logs"].append(f"[CTRL] Master volume set to {st['volume']}%.")
    elif action == "toggle_bass":
        st["bass_boost"] = not st["bass_boost"]
        st["logs"].append(f"[EQ] Bass Boost: {st['bass_boost']}")
    elif action == "toggle_nightcore":
        st["nightcore"] = not st["nightcore"]
        st["logs"].append(f"[EQ] Nightcore DSP: {st['nightcore']}")

    return {"status": "success", "state": st}

@app.post("/api/player/remove")
async def api_remove_queue_item(req: RemoveRequest):
    st = get_or_create_state(req.guild_id)
    if 0 <= req.index < len(st["queue"]):
        removed = st["queue"].pop(req.index)
        st["logs"].append(f"[QUEUE] Removed item '{removed['title']}'")
        return {"status": "success", "state": st}
    raise HTTPException(status_code=400, detail="Invalid index")

@app.post("/api/guild/settings")
async def api_update_settings(req: SettingsRequest):
    sett = get_or_create_settings(req.guild_id)
    sett["prefix"] = req.prefix
    sett["auto_disconnect"] = req.auto_disconnect
    sett["announce_songs"] = req.announce_songs
    sett["dj_only_mode"] = req.dj_only_mode
    return {"status": "success", "settings": sett}

@app.on_event("startup")
async def startup_event():
    if DISCORD_TOKEN:
        asyncio.create_task(bot.start(DISCORD_TOKEN))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 3000)))