import os
import asyncio
from typing import Optional, Dict, Any
from dotenv import load_dotenv

import discord
from discord.ext import commands
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

app = FastAPI(title="Git Music Engine Core")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

try:
    bot = commands.Bot(command_prefix="!", intents=intents)
except Exception:
    bot = None

# State Engine Storage with resilient fallbacks
guild_settings: Dict[int, Dict[str, Any]] = {}
player_states: Dict[int, Dict[str, Any]] = {}

def get_or_create_state(guild_id: int) -> Dict[str, Any]:
    if guild_id not in player_states:
        player_states[guild_id] = {
            "current": {
                "id": "trk_default",
                "title": "Git Music Studio Stream",
                "artist": "Verified Audio Core",
                "duration": "3:45",
                "duration_sec": 225,
                "position_sec": 42,
                "thumbnail": "https://picsum.photos/seed/gitmusic/300/300",
                "added_by": "System"
            },
            "queue": [],
            "is_playing": True,
            "is_paused": False,
            "volume": 80,
            "pitch": 1.0,
            "speed": 1.0,
            "bass": 0,
            "mid": 0,
            "treble": 0,
            "crossfader": 0,
            "scratch_mode": False,
            "filter_cutoff": 20000,
            "active_vc_id": None,
            "logs": ["[SYS] Git Music audio engine initialized successfully."]
        }
    return player_states[guild_id]

def get_or_create_settings(guild_id: int) -> Dict[str, Any]:
    if guild_id not in guild_settings:
        guild_settings[guild_id] = {
            "prefix": "!",
            "auto_disconnect": True,
            "announce_songs": True,
            "dj_only_mode": False,
            "max_queue_size": 100,
            "default_volume": 80,
            "mode_24_7": False,
            "target_vc": None
        }
    return guild_settings[guild_id]

# Models
class PlayRequest(BaseModel):
    guild_id: int
    query: str
    added_by: Optional[str] = "Dashboard Console"

class ControlRequest(BaseModel):
    guild_id: int
    action: str
    value: Optional[Any] = None

class RemoveRequest(BaseModel):
    guild_id: int
    index: int

class SettingsRequest(BaseModel):
    guild_id: int
    prefix: Optional[str] = "!"
    auto_disconnect: Optional[bool] = True
    announce_songs: Optional[bool] = True
    dj_only_mode: Optional[bool] = False
    max_queue_size: Optional[int] = 100
    default_volume: Optional[int] = 80
    mode_24_7: Optional[bool] = Field(default=False, alias="24_7_mode")
    target_vc: Optional[str] = None

    class Config:
        populate_by_name = True

class DspRequest(BaseModel):
    guild_id: int
    pitch: Optional[float] = 1.0
    speed: Optional[float] = 1.0
    bass: Optional[int] = 0
    mid: Optional[int] = 0
    treble: Optional[int] = 0
    crossfader: Optional[int] = 0
    scratch_mode: Optional[bool] = False

# Discord Bot Setup & Cog Loading
if bot:
    @bot.event
    async def on_ready():
        try:
            # Load the commands cog extension
            await bot.load_extension("commands")
            print("[SYSTEM] Loaded commands.py extension successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to load commands extension: {e}")

        try:
            # INSTANT SYNC FOR YOUR SERVER: Replace YOUR_SERVER_ID with your actual server ID number
            GUILD_ID = discord.Object(id=1491730170099273778)
            bot.tree.copy_global_to(guild=GUILD_ID)
            await bot.tree.sync(guild=GUILD_ID)
            print(f"[SYSTEM] Slash commands synced instantly to server ID: {GUILD_ID.id}")
        except Exception as e:
            print(f"[ERROR] Failed to sync command tree: {e}")
        
        print(f"[SYSTEM] Git Music Core live as {bot.user}")

# API Routes
@app.get("/")
async def serve_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return FileResponse("Dashboard/dashboard.html")

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
    if bot and bot.guilds:
        for guild in bot.guilds:
            guilds_data.append({
                "id": str(guild.id),
                "name": guild.name,
                "icon": str(guild.icon.url) if guild.icon else None,
                "member_count": guild.member_count
            })
    if not guilds_data:
        guilds_data = [
            {"id": "123456789012345678", "name": "Git Music Main Guild", "member_count": 128},
            {"id": "876543210987654321", "name": "Studio Lounge Community", "member_count": 45}
        ]
    return {"guilds": guilds_data}

@app.get("/api/bot/voice_channels/{guild_id}")
async def get_voice_channels(guild_id: int):
    channels = []
    if bot:
        guild = bot.get_guild(guild_id)
        if guild:
            for vc in guild.voice_channels:
                channels.append({
                    "id": str(vc.id),
                    "name": vc.name,
                    "members_count": len(vc.members)
                })
    if not channels:
        channels = [
            {"id": "9901", "name": "🔊 General Stage", "members_count": 5},
            {"id": "9902", "name": "🎧 High Quality Audio", "members_count": 2},
            {"id": "9903", "name": "⚡ Git Music VIP Lounge", "members_count": 1}
        ]
    return {"channels": channels}

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
                "duration_sec": 225,
                "thumbnail": f"https://picsum.photos/seed/{abs(hash(clean))}/300/300",
                "query": clean
            },
            {
                "id": f"trk_{hash(clean + '2') & 0xffffff}",
                "title": f"{clean.title()} (Git Music Remix)",
                "artist": "Studio Audio Lab",
                "duration": "4:12",
                "duration_sec": 252,
                "thumbnail": f"https://picsum.photos/seed/{abs(hash(clean + 'remix'))}/300/300",
                "query": f"{clean} remix"
            }
        ]
    }

@app.get("/api/player/state/{guild_id}")
async def get_player_state(guild_id: int):
    st = get_or_create_state(guild_id)
    sett = get_or_create_settings(guild_id)
    if st["is_playing"] and not st["is_paused"] and st["current"]:
        st["position_sec"] = min(st["current"].get("duration_sec", 225), st["position_sec"] + 2)
    return {"state": st, "settings": sett}

@app.post("/api/player/play")
async def api_play_track(req: PlayRequest):
    st = get_or_create_state(req.guild_id)
    track_item = {
        "id": f"q_{len(st['queue']) + 1000}",
        "title": req.query.title(),
        "artist": "Dashboard Stream",
        "duration": "3:30",
        "duration_sec": 210,
        "thumbnail": f"https://picsum.photos/seed/{abs(hash(req.query))}/300/300",
        "added_by": req.added_by
    }

    if not st["current"] or not st["is_playing"]:
        st["current"] = track_item
        st["position_sec"] = 0
        st["is_playing"] = True
        st["is_paused"] = False
        st["logs"].append(f"[EXEC] Now streaming '{track_item['title']}'")
    else:
        st["queue"].append(track_item)
        st["logs"].append(f"[QUEUE] Added '{track_item['title']}' at position #{len(st['queue'])}")

    return {"status": "success", "state": st, "message": f"Added '{track_item['title']}' to playback queue"}

@app.post("/api/player/control")
async def api_control_player(req: ControlRequest):
    st = get_or_create_state(req.guild_id)
    action = req.action.lower()
    msg = f"Action executed: {action}"

    if action == "pause":
        st["is_paused"] = True
        st["is_playing"] = False
        msg = "Playback suspended."
        st["logs"].append("[CTRL] Playback paused.")
    elif action == "resume":
        st["is_paused"] = False
        st["is_playing"] = True
        msg = "Playback resumed."
        st["logs"].append("[CTRL] Playback resumed.")
    elif action == "skip":
        if st["queue"]:
            st["current"] = st["queue"].pop(0)
            st["position_sec"] = 0
            st["is_playing"] = True
            st["is_paused"] = False
            msg = f"Skipped to '{st['current']['title']}'"
            st["logs"].append(f"[CTRL] Skipped to '{st['current']['title']}'")
        else:
            st["logs"].append("[CTRL] Skipped. Queue empty.")
            msg = "Queue is empty."
    elif action == "clear":
        st["queue"] = []
        msg = "Queue stack cleared."
        st["logs"].append("[CTRL] Queue stack wiped.")
    elif action == "seek" and req.value is not None:
        if st["current"]:
            target = max(0, min(st["current"].get("duration_sec", 225), int(req.value)))
            st["position_sec"] = target
            msg = f"Seek position set to {target}s"
            st["logs"].append(f"[CTRL] Track position jumped to {target}s.")
    elif action == "volume" and req.value is not None:
        st["volume"] = max(0, min(100, int(req.value)))
        msg = f"Master Volume set to {st['volume']}%"
        st["logs"].append(f"[CTRL] Master volume set to {st['volume']}%.")
    elif action == "join_vc" and req.value:
        st["active_vc_id"] = str(req.value)
        msg = f"Bot connected to voice channel ID: {req.value}"
        
        if bot:
            guild = bot.get_guild(req.guild_id)
            if guild:
                channel = guild.get_channel(int(req.value))
                if channel and isinstance(channel, discord.VoiceChannel):
                    try:
                        if guild.voice_client:
                            await guild.voice_client.move_to(channel)
                        else:
                            await channel.connect()
                        st["logs"].append(f"[VC] Successfully connected to #{channel.name}")
                    except Exception as e:
                        msg = f"Failed to connect to VC: {str(e)}"
                        st["logs"].append(f"[ERROR] VC connection error: {str(e)}")
                else:
                    msg = "Voice channel not found or invalid."
            else:
                msg = "Bot is not in the specified Discord guild."
        else:
            st["logs"].append(f"[VC] Engine bound to channel ID: {req.value} (Mock Mode)")

    return {"status": "success", "state": st, "message": msg}

@app.post("/api/player/dsp")
async def api_update_dsp(req: DspRequest):
    st = get_or_create_state(req.guild_id)
    if req.pitch is not None: st["pitch"] = round(float(req.pitch), 2)
    if req.speed is not None: st["speed"] = round(float(req.speed), 2)
    if req.bass is not None: st["bass"] = int(req.bass)
    if req.mid is not None: st["mid"] = int(req.mid)
    if req.treble is not None: st["treble"] = int(req.treble)
    if req.crossfader is not None: st["crossfader"] = int(req.crossfader)
    if req.scratch_mode is not None: st["scratch_mode"] = bool(req.scratch_mode)
    
    st["logs"].append(f"[DJ] Deck Mixer Sync - Pitch: {st['pitch']}x | Crossfader: {st['crossfader']} | Scratch: {st['scratch_mode']}")
    return {"status": "success", "state": st, "message": "DJ Mixer & DSP Profile Synchronized"}

@app.post("/api/player/remove")
async def api_remove_queue_item(req: RemoveRequest):
    st = get_or_create_state(req.guild_id)
    if 0 <= req.index < len(st["queue"]):
        removed = st["queue"].pop(req.index)
        st["logs"].append(f"[QUEUE] Removed item '{removed['title']}'")
        return {"status": "success", "state": st, "message": f"Removed '{removed['title']}'"}
    raise HTTPException(status_code=400, detail="Invalid queue item index")

@app.post("/api/guild/settings")
async def api_update_settings(req: SettingsRequest):
    sett = get_or_create_settings(req.guild_id)
    sett["prefix"] = req.prefix
    sett["auto_disconnect"] = req.auto_disconnect
    sett["announce_songs"] = req.announce_songs
    sett["dj_only_mode"] = req.dj_only_mode
    sett["max_queue_size"] = req.max_queue_size
    sett["default_volume"] = req.default_volume
    sett["mode_24_7"] = req.mode_24_7
    sett["target_vc"] = req.target_vc
    return {"status": "success", "settings": sett, "message": "Guild configuration synchronized"}

@app.on_event("startup")
async def startup_event():
    if DISCORD_TOKEN and bot:
        asyncio.create_task(bot.start(DISCORD_TOKEN))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 3000)))