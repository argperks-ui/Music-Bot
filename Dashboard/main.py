import asyncio
import random
from pathlib import Path
from aiohttp import web
from bot import bot, bot_state  # Import bot instance and shared state

BASE_DIR = Path(__file__).resolve().parent
HTML_PATH = BASE_DIR / "dashboard.html"

# Serve Frontend
async def index(request: web.Request) -> web.Response:
    return web.Response(
        text=HTML_PATH.read_text(encoding="utf-8"),
        content_type="text/html",
    )

# API: Fetch State
async def get_state(request: web.Request) -> web.Response:
    guild_id = request.match_info.get("guild_id", "main")
    policy = bot_state["policies"].get(guild_id, bot_state["policies"]["main"])
    return web.json_response({
        "policy": policy,
        "player": bot_state["player"]
    })

# API: Player Actions
async def player_action(request: web.Request) -> web.Response:
    guild_id = request.match_info.get("guild_id", "main")
    data = await request.json()
    action = data.get("action")

    if action == "toggle_play":
        bot_state["player"]["playing"] = not bot_state["player"]["playing"]
        # Add voice_client.pause() / resume() calls here
    elif action == "skip" and bot_state["player"]["queue"]:
        bot_state["player"]["current_track"] = bot_state["player"]["queue"].pop(0)
        # Add voice_client.stop() call here to trigger next track
    elif action == "shuffle":
        random.shuffle(bot_state["player"]["queue"])

    return web.json_response({"status": "ok", "player": bot_state["player"]})

# API: Save Server Policies
async def save_policy(request: web.Request) -> web.Response:
    guild_id = request.match_info.get("guild_id", "main")
    data = await request.json()
    bot_state["policies"][guild_id] = data
    return web.json_response({"status": "saved", "policy": bot_state["policies"][guild_id]})

# Bot Lifecycle Tasks
async def start_bot_task(app: web.Application):
    BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE"
    if BOT_TOKEN != "YOUR_DISCORD_BOT_TOKEN_HERE":
        app["bot_task"] = asyncio.create_task(bot.start(BOT_TOKEN))

async def stop_bot_task(app: web.Application):
    if "bot_task" in app:
        await bot.close()
        app["bot_task"].cancel()

# Router Config
app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/api/state/{guild_id}", get_state)
app.router.add_post("/api/player/{guild_id}/action", player_action)
app.router.add_post("/api/policy/{guild_id}", save_policy)

app.on_startup.append(start_bot_task)
app.on_cleanup.append(stop_bot_task)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8000)