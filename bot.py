import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# State Storage per Guild
guild_states = {}

def get_state(guild_id):
    if guild_id not in guild_states:
        guild_states[guild_id] = {
            'queue': [],
            'current': None,
            'loop': False,
            'volume': 1.0,
            'filter': 'off',
            'mode_247': False,
            'autoplay': True
        }
    return guild_states[guild_id]

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'default_search': 'ytsearch5',
    'source_address': '0.0.0.0',
    'extractor_args': {'youtube': {'player_client': ['web', 'mweb']}}
}
ytdl = yt_dlp.YoutubeDL(YDL_OPTIONS)

FILTER_PRESETS = {
    'off': '',
    'bassboost': '-af "equalizer=f=40:width_type=h:width=50:g=10"',
    'nightcore': '-af "asetrate=44100*1.25,aresample=44100,atempo=1.05"',
    'vaporwave': '-af "asetrate=44100*0.8,aresample=44100,atempo=0.9"',
    '8d': '-af "apulsator=hz=0.125"'
}

def get_ffmpeg_opts(state):
    vol_filter = f'volume={state["volume"]}'
    dsp = FILTER_PRESETS.get(state['filter'], '')
    filter_chain = f'-filter:a "{vol_filter}"' if not dsp else f'{dsp},volume={state["volume"]}'
    return {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': f'-vn {filter_chain}'
    }

# ── EMBEDDED DASHBOARD API SERVER ──
async def handle_get_state(request):
    data = {}
    for gid, state in guild_states.items():
        guild = bot.get_guild(gid)
        data[str(gid)] = {
            'guild_name': guild.name if guild else str(gid),
            'current': state['current'],
            'queue': state['queue'],
            'loop': state['loop'],
            'filter': state['filter'],
            'mode_247': state['mode_247'],
            'volume': int(state['volume'] * 100)
        }
    return web.json_response({'status': 'online', 'guilds': data})

async def handle_control(request):
    body = await request.json()
    action = body.get('action')
    guild_id = int(body.get('guild_id', 0))
    guild = bot.get_guild(guild_id)

    if not guild or not guild.voice_client:
        return web.json_response({'success': False, 'message': 'Bot not active in this guild.'})

    state = get_state(guild_id)
    vc = guild.voice_client

    if action == 'pause_resume':
        if vc.is_playing():
            vc.pause()
        elif vc.is_paused():
            vc.resume()
    elif action == 'skip':
        if vc.is_playing():
            vc.stop()
    elif action == 'filter':
        state['filter'] = body.get('value', 'off')
    elif action == 'mode_247':
        state['mode_247'] = not state['mode_247']

    return web.json_response({'success': True, 'state': state})

async def start_api_server():
    app = web.Application()
    app.router.add_get('/api/state', handle_get_state)
    app.router.add_post('/api/control', handle_control)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 5000)
    await site.start()
    print("⚡ Embedded Dashboard API listening on http://127.0.0.1:5000")

# ── MUSIC CONTROLLER VIEW ──
class MusicControllerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Pause/Resume", style=discord.ButtonStyle.primary, emoji="⏯️", row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Bot not connected!", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ **Paused**", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ **Resumed**", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️", row=0)
    async def skip_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭️ **Skipped!**", ephemeral=True)

    @discord.ui.button(label="DSP Filter", style=discord.ButtonStyle.success, emoji="🎛️", row=0)
    async def cycle_filter(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = get_state(interaction.guild.id)
        filters = ['off', 'bassboost', 'nightcore', 'vaporwave', '8d']
        next_f = filters[(filters.index(state['filter']) + 1) % len(filters)]
        state['filter'] = next_f
        await interaction.response.send_message(f"🎛️ Audio filter updated to: **{next_f.upper()}** (applies on next track)", ephemeral=True)

async def play_next(guild):
    state = get_state(guild.id)
    if state['loop'] and state['current']:
        track = state['current']
    elif state['queue']:
        track = state['queue'].pop(0)
        state['current'] = track
    else:
        state['current'] = None
        if not state['mode_247'] and guild.voice_client:
            await guild.voice_client.disconnect()
        return

    audio_url = track.get('url')
    if not audio_url:
        loop = asyncio.get_running_loop()
        fresh_data = await loop.run_in_executor(None, lambda: ytdl.extract_info(track['webpage_url'], download=False))
        audio_url = fresh_data.get('url')

    vc = guild.voice_client
    if not vc:
        return

    source = discord.FFmpegPCMAudio(audio_url, **get_ffmpeg_opts(state))
    vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild), bot.loop))

@bot.event
async def on_ready():
    print(f"-----------------------------------")
    print(f"Logged in as: {bot.user.name}")
    print(f"-----------------------------------")
    await start_api_server()
    await bot.tree.sync()

@bot.tree.command(name="play", description="Play a track with custom DSP filters and queue support.")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer(thinking=True, ephemeral=True)
    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.followup.send("❌ Join a voice channel first!")

    channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client
    if not vc:
        vc = await channel.connect()

    state = get_state(interaction.guild.id)
    loop = asyncio.get_running_loop()
    query = search if search.startswith("http") else f"ytsearch1:{search}"
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
    
    track = data['entries'][0] if 'entries' in data else data
    state['queue'].append(track)

    if not vc.is_playing() and not vc.is_paused():
        await play_next(interaction.guild)
        await interaction.followup.send(f"🎶 **Now Playing:** `{track['title']}`", view=MusicControllerView())
    else:
        await interaction.followup.send(f"➕ **Queued:** `{track['title']}` (Position #{len(state['queue'])})")

@bot.tree.command(name="filter", description="Set DSP Audio Preset (bassboost, nightcore, vaporwave, 8d, off).")
async def filter_cmd(interaction: discord.Interaction, preset: str):
    preset = preset.lower()
    if preset not in FILTER_PRESETS:
        return await interaction.response.send_message("❌ Presets: `bassboost`, `nightcore`, `vaporwave`, `8d`, `off`", ephemeral=True)
    state = get_state(interaction.guild.id)
    state['filter'] = preset
    await interaction.response.send_message(f"🎛️ DSP Audio preset set to: **{preset.upper()}**")

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)