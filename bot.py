import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
from dotenv import load_dotenv
import dashboard  # Keep your web dashboard running

# Start the web dashboard server in the background
dashboard.start_dashboard()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Setup bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Sync slash commands with Discord globally
        await self.tree.sync()
        print("Slash commands synced successfully!")

bot = MusicBot()

# Configure yt-dlp options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration', 0)

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# --- INTERACTIVE BUTTON CONTROLS (RYTHM STYLE) ---
class MusicControlView(discord.ui.View):
    def __init__(self, ctx_or_interaction):
        super().__init__(timeout=None)
        self.ctx = ctx_or_interaction

    @discord.ui.button(label="Pause/Resume", style=discord.ButtonStyle.primary, emoji="⏯️")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Bot is not connected.", ephemeral=True)
        
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Paused the music.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed the music.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped the song!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing to skip.", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            dashboard.current_song = "None"
            await interaction.response.send_message("⏹️ Stopped music and disconnected.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ I'm not in a voice channel.", ephemeral=True)

@bot.event
async def on_ready():
    dashboard.bot_status = "Online"
    dashboard.guild_count = len(bot.guilds)
    print(f'Logged in as {bot.user} successfully!')

# --- SLASH COMMANDS ---

@bot.tree.command(name="join", description="Make the bot join your voice channel")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)
    
    channel = interaction.user.voice.channel
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect()
    
    await interaction.response.send_message(f'🔊 Joined **{channel.name}**!')

@bot.tree.command(name="play", description="Play a song or YouTube search query")
@app_commands.describe(query="The song name or YouTube link")
async def play(interaction: discord.Interaction, query: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)

    await interaction.response.defer() # Lets Discord know we are processing

    vc = interaction.guild.voice_client
    if vc is None:
        vc = await interaction.user.voice.channel.connect()

    try:
        player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
        dashboard.current_song = player.title
        
        if vc.is_playing() or vc.is_paused():
            vc.stop() # Stop current track to play new one (or set up a queue later)
            
        vc.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
        
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{player.title}]({player.url})**",
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed, view=MusicControlView(interaction))
    except Exception as e:
        await interaction.followup.send(f"❌ Error playing song: `{e}`")

@bot.tree.command(name="pause", description="Pause the currently playing song")
async def pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸️ Paused the music.")
    else:
        await interaction.response.send_message("❌ Nothing is playing right now.", ephemeral=True)

@bot.tree.command(name="resume", description="Resume the paused song")
async def resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ Resumed the music.")
    else:
        await interaction.response.send_message("❌ The music is not paused.", ephemeral=True)

@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭️ Skipped the song!")
    else:
        await interaction.response.send_message("❌ Nothing to skip.", ephemeral=True)

@bot.tree.command(name="volume", description="Change the bot's volume (0 to 100)")
@app_commands.describe(volume="Volume level from 0 to 100")
async def volume(interaction: discord.Interaction, volume: int):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        return await interaction.response.send_message("❌ Nothing is playing right now.", ephemeral=True)
    
    if volume < 0 or volume > 100:
        return await interaction.response.send_message("❌ Volume must be between 0 and 100.", ephemeral=True)
    
    vc.source.volume = volume / 100.0
    await interaction.response.send_message(f"🔊 Volume set to **{volume}%**")

@bot.tree.command(name="stop", description="Stop the music and disconnect the bot")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        dashboard.current_song = "None"
        await interaction.response.send_message("⏹️ Disconnected from the voice channel.")
    else:
        await interaction.response.send_message("❌ I'm not in a voice channel.", ephemeral=True)

# Run the bot
bot.run(TOKEN)