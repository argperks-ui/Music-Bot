import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'ytsearch',
    'quiet': True,
    'reconnect': '1',
    'reconnect_streamed': '1',
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web']
        }
    }
}

class MusicControlView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(label="⏸️ Pause/Resume", style=discord.ButtonStyle.primary, custom_id="music_pause_resume")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        st = self.cog.get_state(guild.id)
        if guild.voice_client:
            if guild.voice_client.is_playing():
                guild.voice_client.pause()
                st["is_paused"] = True
                st["is_playing"] = False
                await interaction.response.send_message("⏸️ Paused playback.", ephemeral=True)
            elif guild.voice_client.is_paused():
                guild.voice_client.resume()
                st["is_paused"] = False
                st["is_playing"] = True
                await interaction.response.send_message("▶️ Resumed playback.", ephemeral=True)
            else:
                await interaction.response.send_message("⚠️ Nothing is playing.", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary, custom_id="music_skip")
    async def skip_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if guild.voice_client and (guild.voice_client.is_playing() or guild.voice_client.is_paused()):
            guild.voice_client.stop()
            await interaction.response.send_message("⏭️ Skipped current track.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Nothing to skip.", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger, custom_id="music_stop")
    async def stop_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        st = self.cog.get_state(guild.id)
        st["current"] = None
        st["queue"] = []
        st["is_playing"] = False
        st["is_paused"] = False
        if guild.voice_client:
            await guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ Stopped music and cleared queue.", ephemeral=True)


class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_state(self, guild_id: int):
        from main import get_or_create_state
        return get_or_create_state(guild_id)

    def play_next(self, guild: discord.Guild, voice_client: discord.VoiceClient):
        st = self.get_state(guild.id)
        
        # If queue has items, pop the next one
        if st["queue"]:
            next_track = st["queue"].pop(0)
            self._start_playback(guild, voice_client, next_track)
        else:
            # Auto-play fallback: if we had a current song, play a related track automatically!
            current = st.get("current")
            if current and "title" in current:
                fallback_query = f"similar songs to {current['title']}"
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    data = yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(fallback_query, download=False)
                    if 'entries' in data and len(data['entries']) > 0:
                        entry = data['entries'][0]
                        auto_track = {
                            "title": entry.get('title', 'Auto-played Track'),
                            "artist": entry.get('uploader', 'YouTube'),
                            "url": entry.get('url'),
                            "duration": f"{entry.get('duration', 210) // 60}:{(entry.get('duration', 210) % 60):02d}",
                            "thumbnail": entry.get('thumbnail', "https://picsum.photos/300/300"),
                            "added_by": "🤖 Auto-Play"
                        }
                        self._start_playback(guild, voice_client, auto_track)
                        return
                except Exception:
                    pass

            st["current"] = None
            st["is_playing"] = False
            st["is_paused"] = False

    def _start_playback(self, guild, voice_client, track_item):
        st = self.get_state(guild.id)
        st["current"] = track_item
        st["is_playing"] = True
        st["is_paused"] = False
        st["logs"].append(f"[EXEC] Now playing: '{track_item['title']}'")

        try:
            FFMPEG_OPTIONS = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }
            source = discord.FFmpegPCMAudio(track_item['url'], **FFMPEG_OPTIONS)
            
            def after_playing(error):
                if error:
                    st["logs"].append(f"[ERROR] Player error: {error}")
                self.play_next(guild, voice_client)

            voice_client.play(source, after=after_playing)
        except Exception as e:
            st["logs"].append(f"[ERROR] Playback failed: {e}")
            st["is_playing"] = False

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

    @app_commands.command(name="play", description="Stream full-length tracks with interactive controls and endless auto-play.")
    @app_commands.describe(query="The song name, artist, or YouTube URL")
    async def slash_play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        guild = interaction.guild
        st = self.get_state(guild.id)

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
            st["logs"].append(f"[ERROR] Extraction failed: {e}")
            await interaction.followup.send(f"❌ Could not extract audio for **'{query}'**: {e}")
            return

        track_item = {
            "title": title,
            "artist": data.get('uploader', 'YouTube Stream'),
            "duration": f"{duration_sec // 60}:{duration_sec % 60:02d}",
            "duration_sec": duration_sec,
            "thumbnail": thumbnail,
            "url": song_url,
            "added_by": str(interaction.user)
        }

        embed = discord.Embed(title="🎶 Now Playing", description=f"**[{title}]({data.get('webpage_url', 'https://youtube.com')})**", color=0x7289DA)
        embed.add_field(name="Duration", value=track_item["duration"], inline=True)
        embed.add_field(name="Requested By", value=track_item["added_by"], inline=True)
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text="Eclipse Viper Music • Endless Auto-Play Active")

        view = MusicControlView(self, guild.id)

        if not voice_client.is_playing() and not voice_client.is_paused():
            self._start_playback(guild, voice_client, track_item)
            await interaction.followup.send(embed=embed, view=view)
        else:
            st["queue"].append(track_item)
            q_embed = discord.Embed(title="➕ Added to Queue", description=f"**{title}**", color=0x43B581)
            q_embed.add_field(name="Position in Queue", value=str(len(st["queue"])), inline=True)
            q_embed.set_thumbnail(url=thumbnail)
            await interaction.followup.send(embed=q_embed)

    @app_commands.command(name="stop", description="Stop music and disconnect bot.")
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
        await interaction.response.send_message("⏹️ Stopped stream and cleared queue.")

async def setup(bot):
    await bot.add_cog(MusicCommands(bot))