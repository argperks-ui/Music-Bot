import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio

# Configure yt-dlp to extract audio URLs safely
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'ytsearch1',
    'quiet': True,
    'reconnect': '1',
    'reconnect_streamed': '1',
}

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_state(self, guild_id: int):
        from main import get_or_create_state
        return get_or_create_state(guild_id)

    @app_commands.command(name="join", description="Make the bot join your current voice channel.")
    async def slash_join(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)
            return
        
        channel = interaction.user.voice.channel
        st = self.get_state(interaction.guild.id)
        
        try:
            if interaction.guild.voice_client:
                await interaction.guild.voice_client.move_to(channel)
            else:
                await channel.connect()
            
            st["active_vc_id"] = str(channel.id)
            st["logs"].append(f"[VC] Connected to #{channel.name} by {interaction.user}")
            await interaction.response.send_message(f"✅ Successfully joined **{channel.name}**!")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to connect: {str(e)}", ephemeral=True)

    @app_commands.command(name="play", description="Search and stream a real track into your voice channel.")
    @app_commands.describe(query="The song name, artist, or YouTube URL")
    async def slash_play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        guild = interaction.guild
        st = self.get_state(guild.id)

        # 1. Ensure bot is in voice channel
        if not guild.voice_client:
            if interaction.user.voice and interaction.user.voice.channel:
                channel = interaction.user.voice.channel
                try:
                    await channel.connect()
                    st["active_vc_id"] = str(channel.id)
                except Exception as e:
                    await interaction.followup.send(f"❌ Failed to join voice channel: {e}")
                    return
            else:
                await interaction.followup.send("❌ You must be in a voice channel to play music!")
                return
        
        voice_client = guild.voice_client

        # 2. Extract track info using yt-dlp in a background thread to prevent blocking
        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(
                None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(query, download=False)
            )
            
            if 'entries' in data:
                data = data['entries'][0]
                
            song_url = data.get('url')
            title = data.get('title', query)
            duration_sec = data.get('duration', 210)
            thumbnail = data.get('thumbnail', f"https://picsum.photos/seed/{abs(hash(query))}/300/300")
        except Exception as e:
            st["logs"].append(f"[ERROR] yt-dlp extraction failed: {e}")
            await interaction.followup.send(f"❌ Could not extract audio for **'{query}'**: {e}")
            return

        track_item = {
            "id": f"trk_{abs(hash(title)) & 0xffffff}",
            "title": title,
            "artist": data.get('uploader', 'YouTube Stream'),
            "duration": f"{duration_sec // 60}:{duration_sec % 60:02d}",
            "duration_sec": duration_sec,
            "position_sec": 0,
            "thumbnail": thumbnail,
            "added_by": str(interaction.user)
        }

        # 3. Handle Queue vs Instant Play
        if not voice_client.is_playing() and not voice_client.is_paused():
            st["current"] = track_item
            st["is_playing"] = True
            st["is_paused"] = False
            st["logs"].append(f"[EXEC] Now streaming: '{title}'")

            try:
                FFMPEG_OPTIONS = {
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                    'options': '-vn'
                }
                source = discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS)
                
                def after_playing(error):
                    if error:
                        st["logs"].append(f"[ERROR] Player error: {error}")
                    st["is_playing"] = False

                voice_client.play(source, after=after_playing)
                await interaction.followup.send(f"▶️ Now streaming: **{title}**")
            except Exception as e:
                st["logs"].append(f"[ERROR] FFmpeg playback failed: {e}")
                await interaction.followup.send(f"⚠️ Failed to start audio stream: {e}")
        else:
            st["queue"].append(track_item)
            st["logs"].append(f"[QUEUE] Added '{title}' at position #{len(st['queue'])}")
            await interaction.followup.send(f"➕ Added to queue (#{len(st['queue'])}): **{title}**")

    @app_commands.command(name="pause", description="Pause current playback.")
    async def slash_pause(self, interaction: discord.Interaction):
        guild = interaction.guild
        st = self.get_state(guild.id)
        if guild.voice_client and guild.voice_client.is_playing():
            guild.voice_client.pause()
            st["is_paused"] = True
            st["is_playing"] = False
            st["logs"].append("[CTRL] Playback paused.")
            await interaction.response.send_message("⏸️ Playback paused.")
        else:
            await interaction.response.send_message("⚠️ Nothing is currently playing.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume playback.")
    async def slash_resume(self, interaction: discord.Interaction):
        guild = interaction.guild
        st = self.get_state(guild.id)
        if guild.voice_client and guild.voice_client.is_paused():
            guild.voice_client.resume()
            st["is_paused"] = False
            st["is_playing"] = True
            st["logs"].append("[CTRL] Playback resumed.")
            await interaction.response.send_message("▶️ Playback resumed.")
        else:
            await interaction.response.send_message("⚠️ Player is not paused.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop music and disconnect.")
    async def slash_stop(self, interaction: discord.Interaction):
        guild = interaction.guild
        st = self.get_state(guild.id)
        st["current"] = None
        st["queue"] = []
        st["is_playing"] = False
        st["is_paused"] = False
        st["active_vc_id"] = None

        if guild.voice_client:
            await guild.voice_client.disconnect()

        st["logs"].append("[CTRL] Stream stopped and bot disconnected.")
        await interaction.response.send_message("⏹️ Stopped stream and disconnected from voice channel.")

async def setup(bot):
    await bot.add_cog(MusicCommands(bot))