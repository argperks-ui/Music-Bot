import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio

# Safe logging fallback so the bot never crashes if dashboard changes
try:
    import dashboard
except ImportError:
    class DummyDashboard:
        current_song = "None"
        volume_level = 50
        def add_log(self, msg): print(f"[Log]: {msg}")
    dashboard = DummyDashboard()

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
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

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
            await interaction.response.send_message("⏹️ Disconnected from the voice channel.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ I'm not in a voice channel.", ephemeral=True)

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="join", description="Make the bot join your voice channel")
    async def join(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not interaction.user.voice:
            return await interaction.followup.send("❌ You need to be in a voice channel first!")
        
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()
        
        await interaction.followup.send(f'🔊 Joined **{channel.name}**!')

    @app_commands.command(name="play", description="Play a song or search query")
    @app_commands.describe(query="Song name or YouTube link")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            return await interaction.followup.send("❌ You need to be in a voice channel first!")

        vc = interaction.guild.voice_client
        if vc is None:
            vc = await interaction.user.voice.channel.connect()

        try:
            player = await asyncio.wait_for(
                YTDLSource.from_url(query, loop=self.bot.loop, stream=True),
                timeout=10.0
            )
            
            try:
                dashboard.current_song = player.title
            except AttributeError:
                pass

            if vc.is_playing() or vc.is_paused():
                vc.stop()
                
            vc.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**[{player.title}]({player.url})**",
                color=discord.Color.blurple()
            )
            embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
            
            await interaction.followup.send(embed=embed, view=MusicControlView())
            
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ **Request timed out!** YouTube took too long to respond.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error playing song: `{e}`")

    @app_commands.command(name="pause", description="Pause the current song")
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer()
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.followup.send("⏸️ Paused the music.")
        else:
            await interaction.followup.send("❌ Nothing is playing right now.")

    @app_commands.command(name="resume", description="Resume the paused song")
    async def resume(self, interaction: discord.Interaction):
        await interaction.response.defer()
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.followup.send("▶️ Resumed the music.")
        else:
            await interaction.followup.send("❌ The music is not paused.")

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer()
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.followup.send("⏭️ Skipped the song!")
        else:
            await interaction.followup.send("❌ Nothing to skip.")

    @app_commands.command(name="volume", description="Change audio output volume (0-100)")
    @app_commands.describe(volume="Volume percentage")
    async def volume(self, interaction: discord.Interaction, volume: int):
        await interaction.response.defer()
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.followup.send("❌ Nothing is playing right now.")
        
        if volume < 0 or volume > 100:
            return await interaction.followup.send("❌ Volume must be between 0 and 100.")
        
        vc.source.volume = volume / 100.0
        await interaction.followup.send(f"🔊 Volume set to **{volume}%**")

    @app_commands.command(name="stop", description="Stop music and disconnect")
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.defer()
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            try:
                dashboard.current_song = "None"
            except AttributeError:
                pass
            await interaction.followup.send("⏹️ Disconnected from the voice channel.")
        else:
            await interaction.followup.send("❌ I'm not in a voice channel.")

async def setup(bot):
    await bot.add_cog(MusicCommands(bot))