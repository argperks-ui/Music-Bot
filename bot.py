import os
import asyncio
import discord
from discord.ext import commands
import yt_dlp
from dotenv import load_dotenv
import dashboard  # Import our separate dashboard file

# Start the web dashboard server in the background
dashboard.start_dashboard()

# Load environment variables from the .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
APPLICATION_ID = os.getenv("APPLICATION_ID")

# Setup bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configure yt-dlp options for seamless streaming
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.event
async def on_ready():
    dashboard.bot_status = "Online"
    dashboard.guild_count = len(bot.guilds)
    print(f'Logged in as {bot.user} successfully!')

@bot.command(name='join', help='Joins your voice channel')
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("❌ You need to be in a voice channel first!")
    channel = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    await ctx.send(f'🔊 Joined **{channel.name}**')

@bot.command(name='play', help='Plays audio from a URL or search query')
async def play(ctx, *, url):
    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            return await ctx.send("❌ You need to be in a voice channel first!")

    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        dashboard.current_song = player.title
        ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

    await ctx.send(f'🎵 **Now Playing:** {player.title}')

@bot.command(name='pause', help='Pauses the current song')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused the music.")
    else:
        await ctx.send("❌ Nothing is playing right now.")

@bot.command(name='resume', help='Resumes the paused song')
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed the music.")
    else:
        await ctx.send("❌ The music is not paused.")

@bot.command(name='stop', help='Stops the music and disconnects')
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        dashboard.current_song = "None"
        await ctx.send("⏹️ Disconnected from the voice channel.")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

# Run the bot
bot.run(TOKEN)