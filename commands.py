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

USER_LIKES = set()
SERVER_HISTORY = []

class GitMusicControlView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.secondary, custom_id="git_pause_resume")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        st = self.cog.get_state(guild.id)
        if guild.voice_client:
            if guild.voice_client.is_playing():
                guild.voice_client.pause()
                st["is_paused"] = True
                st["is_playing"] = False
                await interaction.response.send_message("⏸️ **Paused.**", ephemeral=True)
            elif guild.voice_client.is_paused():
                guild.voice_client.resume()
                st["is_paused"] = False
                st["is_playing"] = True
                await interaction.response.send_message("▶️ **Resumed.**", ephemeral=True)
            else:
                await interaction.response.send_message("⚠️ Nothing is playing.", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="git_stop")
    async def stop_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        st = self.cog.get_state(guild.id)
        st["current"] = None
        st["queue"] = []
        st["is_playing"] = False
        st["is_paused"] = False
        if guild.voice_client:
            await guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ **Stopped and cleared the queue.**", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="git_skip")
    async def skip_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if guild.voice_client and (guild.voice_client.is_playing() or guild.voice_client.is_paused()):
            guild.voice_client.stop()
            await interaction.response.send_message("⏭️ **Skipped track.**", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Nothing to skip.", ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="git_shuffle")
    async def shuffle_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        import random
        st = self.cog.get_state(interaction.guild.id)
        if len(st["queue"]) > 1:
            random.shuffle(st["queue"])
            await interaction.response.send_message("🔀 **Queue shuffled.**", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Not enough tracks in queue to shuffle.", ephemeral=True)


class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_state(self, guild_id: int):
        from main import get_or_create_state
        return get_or_create_state(guild_id)

    def play_next(self, guild: discord.Guild, voice_client: discord.VoiceClient):
        st = self.get_state(guild.id)
        
        if st.get("loop") and st.get("current"):
            self._start_playback(guild, voice_client, st["current"])
            return

        if st["queue"]:
            next_track = st["queue"].pop(0)
            self._start_playback(guild, voice_client, next_track)
        else:
            current = st.get("current")
            if current and "title" in current:
                try:
                    data = yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(f"similar songs to {current['title']}", download=False)
                    if 'entries' in data and data['entries']:
                        entry = data['entries'][0]
                        auto_track = {
                            "title": entry.get('title', 'Auto Track'),
                            "artist": entry.get('uploader', 'YouTube'),
                            "url": entry.get('url'),
                            "duration": f"{entry.get('duration', 210) // 60}:{(entry.get('duration', 210) % 60):02d}",
                            "thumbnail": entry.get('thumbnail', "https://picsum.photos/300/300"),
                            "webpage_url": entry.get('webpage_url', 'https://youtube.com'),
                            "added_by": "Git Music Autoplay"
                        }
                        SERVER_HISTORY.append(auto_track["title"])
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

        try:
            FFMPEG_OPTIONS = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }
            source = discord.FFmpegPCMAudio(track_item['url'], **FFMPEG_OPTIONS)
            
            def after_playing(error):
                if error:
                    st["logs"].append(f"[ERROR] {error}")
                self.play_next(guild, voice_client)

            voice_client.play(source, after=after_playing)
        except Exception as e:
            st["is_playing"] = False

    async def _fetch_track(self, query: str):
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(
            None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(query, download=False)
        )
        if 'entries' in data:
            data = data['entries'][0]
        
        return {
            "title": data.get('title', query),
            "artist": data.get('uploader', 'YouTube'),
            "duration": f"{data.get('duration', 210) // 60}:{(data.get('duration', 210) % 60):02d}",
            "thumbnail": data.get('thumbnail', f"https://picsum.photos/seed/{abs(hash(query))}/300/300"),
            "url": data.get('url'),
            "webpage_url": data.get('webpage_url', 'https://youtube.com'),
            "added_by": None
        }

    def git_embed(self, title: str, description: str, color=0xFEE75C):
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text="Git Music • Powered by Rythm Engine")
        return embed

    # ==================== COMMANDS & ALIASES ====================

    @app_commands.command(name="play", description="Plays a track or adds it to the queue.")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        guild = interaction.guild
        st = self.get_state(guild.id)

        if not guild.voice_client:
            if interaction.user.voice and interaction.user.voice.channel:
                await interaction.user.voice.channel.connect()
            else:
                await interaction.followup.send(embed=self.git_embed("Error", "❌ You must be in a voice channel first!", 0xED4245))
                return

        try:
            track = await self._fetch_track(query)
            track["added_by"] = str(interaction.user)
        except Exception as e:
            await interaction.followup.send(embed=self.git_embed("Error", f"❌ Could not load track: {e}", 0xED4245))
            return

        SERVER_HISTORY.append(track["title"])

        if not guild.voice_client.is_playing() and not guild.voice_client.is_paused():
            self._start_playback(guild, guild.voice_client, track)
            embed = self.git_embed("🎶 Now Playing", f"[{track['title']}]({track['webpage_url']})\n\n**Duration:** `{track['duration']}` | **Requested by:** {track['added_by']}")
            embed.set_thumbnail(url=track["thumbnail"])
            await interaction.followup.send(embed=embed, view=GitMusicControlView(self, guild.id))
        else:
            st["queue"].append(track)
            embed = self.git_embed("➕ Added to Queue", f"[{track['title']}]({track['webpage_url']})\n\n**Position in queue:** `{len(st['queue'])}`")
            embed.set_thumbnail(url=track["thumbnail"])
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="p", description="Alias for /play")
    async def p(self, interaction: discord.Interaction, query: str):
        await self.play.callback(self, interaction, query)

    @app_commands.command(name="queue", description="Displays the current music queue.")
    async def queue(self, interaction: discord.Interaction):
        st = self.get_state(interaction.guild.id)
        current = st.get("current")
        q = st.get("queue", [])

        if not current and not q:
            await interaction.response.send_message(embed=self.git_embed("Queue", "📂 The queue is currently empty."))
            return

        desc = ""
        if current:
            desc += f"**Now Playing:**\n🎵 [{current['title']}]({current['webpage_url']}) (`{current['duration']}`)\n\n"
        
        if q:
            desc += "**Up Next:**\n"
            for i, trk in enumerate(q[:10], 1):
                desc += f"`{i}.` [{trk['title']}]({trk['webpage_url']}) (`{trk['duration']}`)\n"
            if len(q) > 10:
                desc += f"\n*...and {len(q) - 10} more tracks.*"
        
        embed = self.git_embed("📑 Git Music Queue", desc)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="q", description="Alias for /queue")
    async def q(self, interaction: discord.Interaction):
        await self.queue.callback(self, interaction)

    @app_commands.command(name="skip", description="Skips the current song.")
    async def skip(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild.voice_client and (guild.voice_client.is_playing() or guild.voice_client.is_paused()):
            guild.voice_client.stop()
            await interaction.response.send_message(embed=self.git_embed("Skipped", "⏭️ Current track has been skipped."))
        else:
            await interaction.response.send_message(embed=self.git_embed("Error", "⚠️ Nothing playing to skip.", 0xED4245), ephemeral=True)

    @app_commands.command(name="s", description="Alias for /skip")
    async def s(self, interaction: discord.Interaction):
        await self.skip.callback(self, interaction)

    @app_commands.command(name="stop", description="Stops music and clears queue.")
    async def stop(self, interaction: discord.Interaction):
        guild = interaction.guild
        st = self.get_state(guild.id)
        st["current"] = None
        st["queue"] = []
        st["is_playing"] = False
        st["is_paused"] = False
        if guild.voice_client:
            await guild.voice_client.disconnect()
        await interaction.response.send_message(embed=self.git_embed("Stopped", "⏹️ Music stopped and queue cleared."))

    @app_commands.command(name="pause", description="Pauses playback.")
    async def pause(self, interaction: discord.Interaction):
        st = self.get_state(interaction.guild.id)
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            st["is_paused"] = True
            st["is_playing"] = False
            await interaction.response.send_message(embed=self.git_embed("Paused", "⏸️ Playback paused."))
        else:
            await interaction.response.send_message(embed=self.git_embed("Error", "⚠️ Nothing is playing.", 0xED4245), ephemeral=True)

    @app_commands.command(name="resume", description="Resumes playback.")
    async def resume(self, interaction: discord.Interaction):
        st = self.get_state(interaction.guild.id)
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            st["is_paused"] = False
            st["is_playing"] = True
            await interaction.response.send_message(embed=self.git_embed("Resumed", "▶️ Playback resumed."))
        else:
            await interaction.response.send_message(embed=self.git_embed("Error", "⚠️ Player is not paused.", 0xED4245), ephemeral=True)

    @app_commands.command(name="join", description="Connects bot to your voice channel.")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(embed=self.git_embed("Error", "❌ Connect to a voice channel first!", 0xED4245), ephemeral=True)
            return
        channel = interaction.user.voice.channel
        st = self.get_state(interaction.guild.id)
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()
        st["active_vc_id"] = str(channel.id)
        await interaction.response.send_message(embed=self.git_embed("Connected", f"🔊 Joined **{channel.name}**."))

    @app_commands.command(name="summon", description="Alias for /join")
    async def summon(self, interaction: discord.Interaction):
        await self.join.callback(self, interaction)

    @app_commands.command(name="connect", description="Alias for /join")
    async def connect(self, interaction: discord.Interaction):
        await self.join.callback(self, interaction)

    @app_commands.command(name="leave", description="Disconnects bot from voice channel.")
    async def leave(self, interaction: discord.Interaction):
        guild = interaction.guild
        st = self.get_state(guild.id)
        st["current"] = None
        st["queue"] = []
        if guild.voice_client:
            await guild.voice_client.disconnect()
        await interaction.response.send_message(embed=self.git_embed("Disconnected", "👋 Left the voice channel."))

    @app_commands.command(name="disconnect", description="Alias for /leave")
    async def disconnect_cmd(self, interaction: discord.Interaction):
        await self.leave.callback(self, interaction)

    @app_commands.command(name="dc", description="Alias for /leave")
    async def dc(self, interaction: discord.Interaction):
        await self.leave.callback(self, interaction)

    @app_commands.command(name="fuckoff", description="Alias for /leave")
    async def fuckoff(self, interaction: discord.Interaction):
        await self.leave.callback(self, interaction)

    @app_commands.command(name="loop", description="Toggles loop mode for the current track.")
    async def loop(self, interaction: discord.Interaction):
        st = self.get_state(interaction.guild.id)
        st["loop"] = not st.get("loop", False)
        status = "Enabled 🔂" if st["loop"] else "Disabled ➡️"
        await interaction.response.send_message(embed=self.git_embed("Loop Mode", f"🔁 Loop is now **{status}**."))

    @app_commands.command(name="nowplaying", description="Shows the current playing song.")
    async def nowplaying(self, interaction: discord.Interaction):
        st = self.get_state(interaction.guild.id)
        current = st.get("current")
        if not current:
            await interaction.response.send_message(embed=self.git_embed("Now Playing", "⚠️ No music is playing right now.", 0xED4245))
            return
        embed = self.git_embed("🎶 Now Playing", f"[{current['title']}]({current['webpage_url']})\n\n**Duration:** `{current['duration']}`\n**Requested by:** {current.get('added_by', 'Unknown')}")
        embed.set_thumbnail(url=current["thumbnail"])
        await interaction.response.send_message(embed=embed, view=GitMusicControlView(self, interaction.guild.id))

    @app_commands.command(name="np", description="Alias for /nowplaying")
    async def np(self, interaction: discord.Interaction):
        await self.nowplaying.callback(self, interaction)

    @app_commands.command(name="search", description="Search for songs interactively.")
    async def search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        try:
            data = yt_dlp.YoutubeDL({'default_search': 'ytsearch5', 'quiet': True}).extract_info(query, download=False)
            entries = data.get('entries', [])[:5]
            if not entries:
                await interaction.followup.send(embed=self.git_embed("Search", "❌ No results found."))
                return
            desc = "\n".join([f"`{i+1}.` [{e.get('title')}]({e.get('webpage_url')}) (`{e.get('duration', 0)//60}:{e.get('duration', 0)%60:02d}`)" for i, e in enumerate(entries)])
            await interaction.followup.send(embed=self.git_embed(f"🔍 Search Results for '{query}'", desc))
        except Exception as e:
            await interaction.followup.send(embed=self.git_embed("Error", f"❌ Search failed: {e}", 0xED4245))

    @app_commands.command(name="like", description="Like the current track.")
    async def like(self, interaction: discord.Interaction):
        st = self.get_state(interaction.guild.id)
        current = st.get("current")
        if not current:
            await interaction.response.send_message(embed=self.git_embed("Error", "⚠️ Nothing is playing to like.", 0xED4245), ephemeral=True)
            return
        USER_LIKES.add(current["title"])
        await interaction.response.send_message(embed=self.git_embed("Liked", f"❤️ Added **{current['title']}** to your favorites!"))

    @app_commands.command(name="love", description="Alias for /like")
    async def love(self, interaction: discord.Interaction):
        await self.like.callback(self, interaction)

    @app_commands.command(name="grab", description="Alias for /like")
    async def grab(self, interaction: discord.Interaction):
        await self.like.callback(self, interaction)

    @app_commands.command(name="liked", description="View your favorite liked tracks.")
    async def liked(self, interaction: discord.Interaction):
        if not USER_LIKES:
            await interaction.response.send_message(embed=self.git_embed("Favorites", "📂 You have no liked tracks."), ephemeral=True)
            return
        desc = "\n".join([f"• {t}" for t in list(USER_LIKES)[:15]])
        await interaction.response.send_message(embed=self.git_embed("❤️ Your Liked Tracks", desc), ephemeral=True)

    @app_commands.command(name="history", description="View recent server history.")
    async def history(self, interaction: discord.Interaction):
        if not SERVER_HISTORY:
            await interaction.response.send_message(embed=self.git_embed("History", "📂 No listening history yet."))
            return
        desc = "\n".join([f"• {h}" for h in SERVER_HISTORY[-15:][::-1]])
        await interaction.response.send_message(embed=self.git_embed("📜 Recent Server History", desc))

async def setup(bot):
    await bot.add_cog(MusicCommands(bot))