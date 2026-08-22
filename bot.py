import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Advanced guild state storage: { guild_id: { 'queue': [], 'current': track, 'loop': bool, 'volume': float } }
guild_states = {}

def get_guild_state(guild_id):
    if guild_id not in guild_states:
        guild_states[guild_id] = {
            'queue': [],
            'current': None,
            'loop': False,
            'volume': 1.0
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

def get_ffmpeg_options(volume=1.0):
    return {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': f'-vn -filter:a "volume={volume}"'
    }

# ── ULTIMATE INTERACTIVE MUSIC CONTROL PANEL ──
class MusicControllerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Pause/Resume", style=discord.ButtonStyle.primary, emoji="⏯️", row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Bot is not connected to a voice channel!", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ **Playback Paused**", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ **Playback Resumed**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is currently playing.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️", row=0)
    async def skip_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭️ **Track Skipped!** Loading next in queue...", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No active track to skip.", ephemeral=True)

    @discord.ui.button(label="Loop", style=discord.ButtonStyle.secondary, emoji="🔁", row=0)
    async def toggle_loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = get_guild_state(interaction.guild.id)
        state['loop'] = not state['loop']
        status = "ENABLED 🟢" if state['loop'] else "DISABLED 🔴"
        button.style = discord.ButtonStyle.success if state['loop'] else discord.ButtonStyle.secondary
        await interaction.response.send_message(f"🔁 Loop mode is now **{status}**", ephemeral=True)

    @discord.ui.button(label="Queue", style=discord.ButtonStyle.success, emoji="📜", row=1)
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = get_guild_state(interaction.guild.id)
        queue = state['queue']
        current = state['current']

        embed = discord.Embed(title="📜 Server Music Queue", color=0x8b5cf6)
        
        if current:
            embed.add_field(name="🎶 Now Playing", value=f"**[{current['title']}]({current['webpage_url']})** — *{current['uploader']}*", inline=False)
        
        if queue:
            desc = ""
            for i, track in enumerate(queue[:10], 1):
                desc += f"`{i}.` **[{track['title']}]({track['webpage_url']})** | *{track['uploader']}*\n"
            embed.add_field(name="📋 Up Next", value=desc, inline=False)
            embed.set_footer(text=f"Total tracks queued: {len(queue)}")
        else:
            embed.add_field(name="📋 Up Next", value="*Queue is empty. Add more tracks with `/play`!*", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Stop & Clear", style=discord.ButtonStyle.danger, emoji="⏹️", row=1)
    async def stop_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            state = get_guild_state(interaction.guild.id)
            state['queue'] = []
            state['current'] = None
            await vc.disconnect()
            await interaction.response.send_message("⏹️ **Disconnected** and cleared playback memory.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bot is not in a voice channel.", ephemeral=True)


# ── SEARCH SELECTION DROPDOWN MENU ──
class SongSelectDropdown(discord.ui.Select):
    def __init__(self, entries):
        self.entries = entries
        options = []
        for i, entry in enumerate(entries[:5]):
            title = entry.get('title', 'Unknown Title')[:95]
            artist = entry.get('uploader', 'Unknown Artist')[:95]
            duration = entry.get('duration_string', 'Live')
            options.append(
                discord.SelectOption(
                    label=title,
                    description=f"Artist: {artist} | ⏱️ {duration}",
                    value=str(i),
                    emoji="🎵"
                )
            )
        super().__init__(placeholder="⚡ Select your track from search results...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            selected_index = int(self.values[0])
            info = self.entries[selected_index]
            
            state = get_guild_state(interaction.guild.id)
            state['queue'].append(info)

            vc = interaction.guild.voice_client
            if not vc or not vc.is_connected():
                return await interaction.followup.send("❌ Bot got disconnected from voice.", ephemeral=True)

            if not vc.is_playing() and not vc.is_paused():
                await play_next(interaction.guild, interaction)
            else:
                embed = discord.Embed(
                    title="⚡ Track Added to Queue",
                    description=f"**[{info.get('title')}]({info.get('webpage_url')})**",
                    color=0x06b6d4
                )
                embed.add_field(name="🎤 Artist", value=info.get('uploader', 'Unknown'), inline=True)
                embed.add_field(name="⏱️ Duration", value=info.get('duration_string', 'Live'), inline=True)
                embed.add_field(name="📊 Position", value=f"`#{len(state['queue'])}`", inline=True)
                embed.set_thumbnail(url=info.get('thumbnail'))
                embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
                await interaction.edit_original_response(content="✅ **Successfully queued track!**", embed=embed, view=None)

        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Error loading track: `{str(e)}`", embed=None, view=None)


class SongSelectView(discord.ui.View):
    def __init__(self, entries):
        super().__init__(timeout=60)
        self.add_item(SongSelectDropdown(entries))


async def play_next(guild, interaction_or_ctx):
    state = get_guild_state(guild.id)
    
    if state['loop'] and state['current']:
        track = state['current']
    elif state['queue']:
        track = state['queue'].pop(0)
        state['current'] = track
    else:
        state['current'] = None
        return

    audio_url = track.get('url')
    if not audio_url:
        loop = asyncio.get_running_loop()
        fresh_data = await loop.run_in_executor(None, lambda: ytdl.extract_info(track['webpage_url'], download=False))
        audio_url = fresh_data.get('url')

    vc = guild.voice_client
    if not vc:
        return

    source = discord.FFmpegPCMAudio(audio_url, **get_ffmpeg_options(state['volume']))

    def after_playback(error):
        if error:
            print(f"Playback error: {error}")
        fut = asyncio.run_coroutine_threadsafe(play_next(guild, None), bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(e)

    vc.play(source, after=after_playback)

    embed = discord.Embed(
        title="🎶 NOW PLAYING",
        description=f"**[{track.get('title')}]({track.get('webpage_url', '#')})**",
        color=0x8b5cf6
    )
    embed.add_field(name="🎤 Artist / Channel", value=track.get('uploader', 'Unknown'), inline=True)
    embed.add_field(name="⏱️ Duration", value=track.get('duration_string', 'Live'), inline=True)
    embed.add_field(name="🔁 Loop Mode", value="`Active`" if state['loop'] else "`Off`", inline=True)
    embed.set_thumbnail(url=track.get('thumbnail', 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4'))
    embed.set_footer(text="Git Music Engine • Powered by Discord UI")

    if interaction_or_ctx and isinstance(interaction_or_ctx, discord.Interaction):
        try:
            await interaction_or_ctx.edit_original_response(content="🔊 **Audio Stream Initialized!**", embed=embed, view=MusicControllerView())
        except:
            pass


# ── SLASH COMMANDS ──

@bot.event
async def on_ready():
    print(f"-----------------------------------")
    print(f"Logged in as: {bot.user.name} ({bot.user.id})")
    print(f"-----------------------------------")
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Successfully synced {len(synced)} futuristic slash commands!")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.tree.command(name="join", description="Summon the bot to your current voice channel.")
async def join(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.followup.send("❌ You must be inside a voice channel first!")
    
    channel = interaction.user.voice.channel
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect()
        
    await interaction.followup.send(f"✅ Connected to **{channel.name}**!")

@bot.tree.command(name="play", description="Search YouTube for songs and choose from an interactive selector.")
@app_commands.describe(search="Song name, artist, or YouTube URL")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.defer(thinking=True, ephemeral=True)

    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.followup.send("❌ You need to be in a voice channel to play music!")

    channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client
    if not vc:
        vc = await channel.connect()
    elif vc.channel != channel:
        await vc.move_to(channel)

    loop = asyncio.get_running_loop()
    try:
        query = search if search.startswith("http") else f"ytsearch5:{search}"
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        
        entries = data.get('entries', [])
        if not entries:
            return await interaction.followup.send("❌ No matches found for your search query.")

        view = SongSelectView(entries)
        embed = discord.Embed(
            title="🔍 Search Results Matrix",
            description=f"Query: `{search}`\nChoose the exact track you want to stream from the menu below:",
            color=0x06b6d4
        )
        await interaction.followup.send(embed=embed, view=view)

    except Exception as e:
        await interaction.followup.send(f"❌ Error querying archive: `{str(e)}`")

@bot.tree.command(name="np", description="Display rich information about the currently playing song.")
async def now_playing(interaction: discord.Interaction):
    state = get_guild_state(interaction.guild.id)
    track = state['current']
    if not track:
        return await interaction.response.send_message("❌ Nothing is currently streaming.", ephemeral=True)

    embed = discord.Embed(
        title="🎶 Now Playing Status",
        description=f"**[{track.get('title')}]({track.get('webpage_url', '#')})**",
        color=0x8b5cf6
    )
    embed.add_field(name="🎤 Artist", value=track.get('uploader', 'Unknown'), inline=True)
    embed.add_field(name="⏱️ Duration", value=track.get('duration_string', 'Live'), inline=True)
    embed.set_thumbnail(url=track.get('thumbnail'))
    await interaction.response.send_message(embed=embed, view=MusicControllerView())

@bot.tree.command(name="volume", description="Adjust playback volume level.")
@app_commands.describe(level="Volume percentage from 1 to 100")
async def volume(interaction: discord.Interaction, level: int):
    if not 1 <= level <= 100:
        return await interaction.response.send_message("❌ Volume must be between **1** and **100**.", ephemeral=True)
    
    state = get_guild_state(interaction.guild.id)
    state['volume'] = level / 100.0
    
    vc = interaction.guild.voice_client
    if vc and vc.source:
        # Note: volume filter applies to newly started streams
        pass

    await interaction.response.send_message(f"🔊 Volume adjusted to **{level}%** (applies on next track).", ephemeral=True)

@bot.tree.command(name="stop", description="Stop music playback, wipe the queue, and disconnect.")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        state = get_guild_state(interaction.guild.id)
        state['queue'] = []
        state['current'] = None
        await vc.disconnect()
        await interaction.response.send_message("⏹️ Bot disconnected and playback state wiped clean.")
    else:
        await interaction.response.send_message("❌ Bot is not connected to any voice channel.", ephemeral=True)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: Bot token missing!")
    else:
        bot.run(TOKEN)