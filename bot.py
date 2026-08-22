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

# Server-specific queues & player states
guild_queues = {}  # { guild_id: [track_info, track_info, ...] }

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'default_search': 'ytsearch5',
    'source_address': '0.0.0.0',
    'extractor_args': {'youtube': {'player_client': ['web', 'mweb']}}
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
ytdl = yt_dlp.YoutubeDL(YDL_OPTIONS)

# ── ADVANCED MUSIC CONTROL PANEL (PERSISTENT BUTTONS) ──
class MusicControllerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Pause/Resume", style=discord.ButtonStyle.primary, emoji="⏯️", row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Bot is not in a voice channel!", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Music paused.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Music resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is currently playing.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️", row=0)
    async def skip_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped current track.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No audio currently playing to skip.", ephemeral=True)

    @discord.ui.button(label="Queue", style=discord.ButtonStyle.success, emoji="📜", row=0)
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        queue = guild_queues.get(interaction.guild.id, [])
        if not queue:
            return await interaction.response.send_message("📜 The music queue is currently empty.", ephemeral=True)
        
        desc = ""
        for i, track in enumerate(queue[:10], 1):
            desc += f"`{i}.` **[{track['title']}]({track['webpage_url']})** — *{track['uploader']}*\n"
        
        embed = discord.Embed(title="🎶 Current Music Queue", description=desc, color=0x8b5cf6)
        embed.set_footer(text=f"Total tracks in queue: {len(queue)}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Disconnect", style=discord.ButtonStyle.danger, emoji="⏹️", row=1)
    async def stop_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            guild_queues[interaction.guild.id] = []
            await vc.disconnect()
            await interaction.response.send_message("⏹️ Disconnected from voice channel and cleared queue.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bot is not connected.", ephemeral=True)


# ── INTERACTIVE SONG SELECTION DROPDOWN ──
class SongSelectDropdown(discord.ui.Select):
    def __init__(self, entries):
        self.entries = entries
        options = []
        for i, entry in enumerate(entries[:5]):
            title = entry.get('title', 'Unknown Title')[:95]
            artist = entry.get('uploader', 'Unknown Artist')[:95]
            options.append(
                discord.SelectOption(
                    label=title,
                    description=f"By: {artist}",
                    value=str(i),
                    emoji="🎵"
                )
            )
        super().__init__(placeholder="👉 Choose a track to add/play...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            selected_index = int(self.values[0])
            info = self.entries[selected_index]
            
            guild_id = interaction.guild.id
            if guild_id not in guild_queues:
                guild_queues[guild_id] = []
            
            guild_queues[guild_id].append(info)

            vc = interaction.guild.voice_client
            if not vc or not vc.is_connected():
                return await interaction.followup.send("❌ Bot got disconnected from the voice channel.", ephemeral=True)

            # If nothing is playing right now, start playing immediately
            if not vc.is_playing() and not vc.is_paused():
                await play_next(interaction.guild, interaction)
            else:
                embed = discord.Embed(
                    title="➕ Added to Queue",
                    description=f"**[{info.get('title')}]({info.get('webpage_url')})**",
                    color=0x06b6d4
                )
                embed.add_field(name="Position in Queue", value=str(len(guild_queues[guild_id])), inline=True)
                embed.set_thumbnail(url=info.get('thumbnail'))
                await interaction.edit_original_response(content="✅ Track successfully queued!", embed=embed, view=None)

        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Failed to process track: `{str(e)}`", embed=None, view=None)


class SongSelectView(discord.ui.View):
    def __init__(self, entries):
        super().__init__(timeout=60)
        self.add_item(SongSelectDropdown(entries))


async def play_next(guild, interaction_or_ctx):
    guild_id = guild.id
    if guild_id not in guild_queues or not guild_queues[guild_id]:
        return

    track = guild_queues[guild_id].pop(0)
    audio_url = track.get('url')
    if not audio_url:
        loop = asyncio.get_running_loop()
        fresh_data = await loop.run_in_executor(None, lambda: ytdl.extract_info(track['webpage_url'], download=False))
        audio_url = fresh_data.get('url')

    vc = guild.voice_client
    if not vc:
        return

    source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)

    def after_playback(error):
        if error:
            print(f"Player error: {error}")
        fut = asyncio.run_coroutine_threadsafe(play_next(guild, None), bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(e)

    vc.play(source, after=after_playback)

    embed = discord.Embed(
        title="🎶 Now Playing",
        description=f"**[{track.get('title')}]({track.get('webpage_url', '#')})**",
        color=0x8b5cf6
    )
    embed.add_field(name="🎤 Artist", value=track.get('uploader', 'Unknown'), inline=True)
    embed.add_field(name="⏱️ Duration", value=track.get('duration_string', 'Live'), inline=True)
    embed.set_thumbnail(url=track.get('thumbnail', 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4'))
    
    if interaction_or_ctx:
        if isinstance(interaction_or_ctx, discord.Interaction):
            try:
                await interaction_or_ctx.edit_original_response(content="✅ Now playing track!", embed=embed, view=MusicControllerView())
            except:
                pass


# ── BOT EVENTS & COMMANDS ──

@bot.event
async def on_ready():
    print(f"-----------------------------------")
    print(f"Logged in as: {bot.user.name} ({bot.user.id})")
    print(f"-----------------------------------")
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Successfully synced {len(synced)} slash commands!")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.tree.command(name="join", description="Make the bot join your current voice channel.")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.response.send_message("❌ You must be connected to a voice channel first!", ephemeral=True)
    
    channel = interaction.user.voice.channel
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect()
        
    await interaction.response.send_message(f"✅ Joined **{channel.name}**!", ephemeral=True)

@bot.tree.command(name="panel", description="Deploy a permanent interactive music control dashboard embed in chat.")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎛️ Git Music Control Center",
        description="Use the buttons below to control audio playback, skip songs, or inspect the queue at any time.",
        color=0x8b5cf6
    )
    embed.set_image(url="https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4")
    embed.set_footer(text="Git Music Engine • Powered by Discord UI")
    await interaction.response.send_message(embed=embed, view=MusicControllerView())

@bot.tree.command(name="play", description="Search YouTube for songs and pick from an interactive list.")
@app_commands.describe(search="Song name or artist")
async def play(interaction: discord.Interaction, search: str):
    await interaction.response.send_message("🔍 **Scanning music archives...**", ephemeral=True)

    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.edit_original_response(content="❌ You need to be in a voice channel to play music!")

    channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client
    if not vc:
        vc = await channel.connect()
    elif vc.channel != channel:
        await vc.move_to(channel)

    await interaction.edit_original_response(content="🎸 **Tuning instruments & fetching results...**")

    loop = asyncio.get_running_loop()
    try:
        query = search if search.startswith("http") else f"ytsearch5:{search}"
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        
        entries = data.get('entries', [])
        if not entries:
            return await interaction.edit_original_response(content="❌ No songs found matching your search.")

        view = SongSelectView(entries)
        await interaction.edit_original_response(
            content=f"🎵 **Found matching tracks for:** `{search}`\nSelect a track from the menu below:",
            view=view
        )

    except Exception as e:
        await interaction.edit_original_response(content=f"❌ Error searching tracks: `{str(e)}`")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: Bot token missing!")
    else:
        bot.run(TOKEN)