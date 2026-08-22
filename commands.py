import os
import random
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import aiohttp
from bs4 import BeautifulSoup

from embeds import now_playing_embed, queue_embed, status_embed, InteractiveMusicView

AUDIO_FILTERS = {
    "off": "",
    "bassboost": "-af equalizer=f=50:width_type=h:width=100:g=15",
    "nightcore": "-af asetrate=44100*1.25,aresample=44100,equalizer=f=40:width_type=h:width=50:g=5",
    "vaporwave": "-af asetrate=44100*0.8,aresample=44100",
    "8d": "-af apulsator=hz=0.125"
}

class TrackSelectView(discord.ui.View):
    def __init__(self, tracks, music_cog, interaction):
        super().__init__(timeout=60)
        self.tracks = tracks
        self.music_cog = music_cog
        self.orig_interaction = interaction

        options = [
            discord.SelectOption(
                label=t['title'][:90],
                description=f"Duration: {t.get('duration_string', 'N/A')}",
                value=str(idx)
            ) for idx, t in enumerate(tracks[:5])
        ]
        
        select = discord.ui.Select(placeholder="Choose a track to play...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        idx = int(interaction.data['values'][0])
        selected_track = self.tracks[idx]
        await interaction.response.defer()
        await self.music_cog.enqueue_and_play(self.orig_interaction, selected_track)
        await interaction.edit_original_response(
            embed=status_embed("Selected Track", f"Queued: **{selected_track['title']}**"),
            view=None
        )

class MusicCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues = {}
        self.now_playing = {}
        self.history = {}
        self.guild_volume = {}
        self.loop_modes = {}
        self.current_filter = {}
        self.autoplay_modes = {}

        self.ydl_options = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'default_search': 'ytsearch1',
            'source_address': '0.0.0.0',
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'mweb'],
                    'skip': ['hls', 'dash']
                }
            }
        }

    def get_ffmpeg_options(self, guild_id: int, start_time: int = 0):
        filter_str = AUDIO_FILTERS.get(self.current_filter.get(guild_id, "off"), "")
        before_opts = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
        if start_time > 0:
            before_opts += f' -ss {start_time}'
        
        options = '-vn'
        if filter_str:
            options += f" {filter_str}"

        return {'before_options': before_opts, 'options': options}

    def play_next(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        vc = interaction.guild.voice_client
        if not vc:
            return

        current = self.now_playing.get(guild_id)
        if current:
            if guild_id not in self.history:
                self.history[guild_id] = []
            self.history[guild_id].insert(0, current)
            if len(self.history[guild_id]) > 20:
                self.history[guild_id].pop()

        mode = self.loop_modes.get(guild_id, 'off')
        if mode == 'song' and current:
            song = current
        elif mode == 'queue' and current:
            self.queues[guild_id].append(current)
            song = self.queues[guild_id].pop(0) if self.queues.get(guild_id) else None
        elif self.queues.get(guild_id) and len(self.queues[guild_id]) > 0:
            song = self.queues[guild_id].pop(0)
        else:
            self.now_playing[guild_id] = None
            return

        self.now_playing[guild_id] = song
        vol = self.guild_volume.get(guild_id, 0.5)
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(song['url'], **self.get_ffmpeg_options(guild_id)),
            volume=vol
        )

        vc.play(source, after=lambda e: self.play_next(interaction))
        embed = now_playing_embed(song, int(vol * 100), mode)
        view = InteractiveMusicView(self.bot, guild_id)
        asyncio.run_coroutine_threadsafe(
            interaction.channel.send(embed=embed, view=view),
            self.bot.loop
        )

    async def enqueue_and_play(self, interaction: discord.Interaction, song: dict):
        guild_id = interaction.guild_id
        vc = interaction.guild.voice_client

        if guild_id not in self.queues:
            self.queues[guild_id] = []

        if vc.is_playing() or vc.is_paused():
            self.queues[guild_id].append(song)
            await interaction.followup.send(
                embed=status_embed("Queued Track", f"Added [{song['title']}]({song['webpage_url']}) to queue.", "info")
            )
        else:
            self.now_playing[guild_id] = song
            vol = self.guild_volume.get(guild_id, 0.5)
            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(song['url'], **self.get_ffmpeg_options(guild_id)),
                volume=vol
            )
            vc.play(source, after=lambda e: self.play_next(interaction))
            embed = now_playing_embed(song, int(vol * 100), self.loop_modes.get(guild_id, 'off'))
            view = InteractiveMusicView(self.bot, guild_id)
            await interaction.followup.send(embed=embed, view=view)

    # --- VOICE CHANNEL COMMANDS ---

    @app_commands.command(name="join", description="Connect bot to your current voice channel")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(embed=status_embed("Error", "Join a voice channel first!", "danger"), ephemeral=True)
        
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()
        await interaction.response.send_message(embed=status_embed("Connected", f"Joined **{channel.name}**"))

    @app_commands.command(name="leave", description="Disconnect bot from voice channel")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message(embed=status_embed("Disconnected", "Left voice channel."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Not connected to voice.", "warning"), ephemeral=True)

    # --- PLAYBACK & QUEUE COMMANDS ---

    @app_commands.command(name="play", description="Play a track or search query")
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(embed=status_embed("Error", "Join a VC first!", "danger"), ephemeral=True)

        await interaction.response.defer()
        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect()

        with yt_dlp.YoutubeDL(self.ydl_options) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                song = {
                    'url': info['url'],
                    'webpage_url': info.get('webpage_url', query),
                    'title': info.get('title', 'Audio Track'),
                    'thumbnail': info.get('thumbnail'),
                    'duration_string': str(info.get('duration_string', 'N/A')),
                    'requester': interaction.user.display_name
                }
            except Exception as err:
                return await interaction.followup.send(embed=status_embed("Error", f"Failed to extract audio: {err}", "danger"))

        await self.enqueue_and_play(interaction, song)

    @app_commands.command(name="search", description="Search YouTube and select from top 5 results")
    async def search(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(embed=status_embed("Error", "Join a VC first!", "danger"), ephemeral=True)

        await interaction.response.defer()
        opts = dict(self.ydl_options)
        opts['default_search'] = 'ytsearch5'

        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                entries = info.get('entries', [])
                if not entries:
                    return await interaction.followup.send(embed=status_embed("No Results", "No matching videos found.", "warning"))

                tracks = [{
                    'url': e['url'],
                    'webpage_url': e.get('webpage_url', ''),
                    'title': e.get('title', 'Track'),
                    'thumbnail': e.get('thumbnail'),
                    'duration_string': str(e.get('duration_string', 'N/A')),
                    'requester': interaction.user.display_name
                } for e in entries]

                view = TrackSelectView(tracks, self, interaction)
                await interaction.followup.send(embed=status_embed("Search Results", f"Found 5 tracks for `{query}`:"), view=view)
            except Exception as err:
                await interaction.followup.send(embed=status_embed("Search Failed", f"Error: {err}", "danger"))

    @app_commands.command(name="replay", description="Restart current track from beginning")
    async def replay(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        vc = interaction.guild.voice_client
        current = self.now_playing.get(guild_id)
        if vc and current:
            vol = self.guild_volume.get(guild_id, 0.5)
            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(current['url'], **self.get_ffmpeg_options(guild_id, 0)),
                volume=vol
            )
            vc.stop()
            vc.play(source, after=lambda e: self.play_next(interaction))
            await interaction.response.send_message(embed=status_embed("Replaying", f"Restarted **{current['title']}**"))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Nothing active to replay.", "warning"), ephemeral=True)

    @app_commands.command(name="pause", description="Pause playback")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message(embed=status_embed("Paused", "Audio paused."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Nothing playing.", "warning"), ephemeral=True)

    @app_commands.command(name="resume", description="Resume playback")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message(embed=status_embed("Resumed", "Audio resumed."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Audio is not paused.", "warning"), ephemeral=True)

    @app_commands.command(name="skip", description="Skip current track")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message(embed=status_embed("Skipped", "Skipped to next track."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Nothing to skip.", "warning"), ephemeral=True)

    @app_commands.command(name="stop", description="Stop music and clear queue")
    async def stop(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        if guild_id in self.queues:
            self.queues[guild_id].clear()
        self.now_playing[guild_id] = None
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await interaction.response.send_message(embed=status_embed("Stopped", "Cleared queue and stopped playback."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Not in VC.", "warning"), ephemeral=True)

    @app_commands.command(name="queue", description="Display active track queue")
    async def queue_cmd(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        q = self.queues.get(guild_id, [])
        current = self.now_playing.get(guild_id)
        await interaction.response.send_message(embed=queue_embed(q, current))

    @app_commands.command(name="nowplaying", description="Show active song details")
    async def nowplaying(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        song = self.now_playing.get(guild_id)
        if not song:
            return await interaction.response.send_message(embed=status_embed("Idle", "Nothing currently playing.", "warning"), ephemeral=True)
        vol = int(self.guild_volume.get(guild_id, 0.5) * 100)
        embed = now_playing_embed(song, vol, self.loop_modes.get(guild_id, 'off'))
        view = InteractiveMusicView(self.bot, guild_id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="history", description="Show recently played tracks")
    async def history_cmd(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        h = self.history.get(guild_id, [])
        if not h:
            return await interaction.response.send_message(embed=status_embed("History Empty", "No recently played tracks.", "info"), ephemeral=True)
        
        desc = ""
        for idx, song in enumerate(h[:10], start=1):
            desc += f"`{idx}.` [{song['title']}]({song.get('webpage_url', song['url'])})\n"
        
        embed = discord.Embed(title="📜 Recently Played Tracks", description=desc, color=0x5865F2)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="removeduplicates", description="Remove duplicate tracks from queue")
    async def removeduplicates(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        q = self.queues.get(guild_id, [])
        if not q:
            return await interaction.response.send_message(embed=status_embed("Empty Queue", "No tracks in queue to clean.", "warning"), ephemeral=True)

        seen = set()
        clean_queue = []
        for song in q:
            if song['url'] not in seen:
                seen.add(song['url'])
                clean_queue.append(song)
        
        removed_count = len(q) - len(clean_queue)
        self.queues[guild_id] = clean_queue
        await interaction.response.send_message(embed=status_embed("Queue Cleaned", f"Removed **{removed_count}** duplicate track(s)."))

    @app_commands.command(name="shuffle", description="Randomize queue order")
    async def shuffle(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        q = self.queues.get(guild_id, [])
        if len(q) > 1:
            random.shuffle(q)
            await interaction.response.send_message(embed=status_embed("Shuffled", f"Randomized {len(q)} tracks."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Need at least 2 tracks to shuffle.", "warning"), ephemeral=True)

    @app_commands.command(name="grab", description="Receive current track details in private Direct Messages")
    async def grab(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        song = self.now_playing.get(guild_id)
        if not song:
            return await interaction.response.send_message(embed=status_embed("Idle", "Nothing playing right now.", "warning"), ephemeral=True)
        
        try:
            embed = now_playing_embed(song, int(self.guild_volume.get(guild_id, 0.5) * 100), self.loop_modes.get(guild_id, 'off'))
            await interaction.user.send(content="💾 Saved track details from your server:", embed=embed)
            await interaction.response.send_message(embed=status_embed("Saved", "Sent track details to your DMs! 📩"), ephemeral=True)
        except Exception:
            await interaction.response.send_message(embed=status_embed("Error", "Could not send DM. Please check your privacy settings.", "danger"), ephemeral=True)

    @app_commands.command(name="lyrics", description="Fetch song lyrics for current track or search query")
    async def lyrics(self, interaction: discord.Interaction, query: str = None):
        await interaction.response.defer()
        guild_id = interaction.guild_id
        if not query:
            song = self.now_playing.get(guild_id)
            if song:
                query = song['title']
            else:
                return await interaction.followup.send(embed=status_embed("Error", "Provide a song title or play a track first.", "warning"))

        # Simple Genius lyrics scraper fallback
        search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}+genius+lyrics"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, headers=headers) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                link = soup.find('a', class_='result__url')
                
                if link and 'genius.com' in link.get('href', ''):
                    target_url = link['href']
                    async with session.get(target_url, headers=headers) as lyric_resp:
                        l_html = await lyric_resp.text()
                        l_soup = BeautifulSoup(l_html, 'html.parser')
                        containers = l_soup.find_all('div', {'data-lyrics-container': 'true'})
                        if containers:
                            lyrics_text = "\n".join([c.get_text(separator="\n") for c in containers])
                            if len(lyrics_text) > 4000:
                                lyrics_text = lyrics_text[:4000] + "..."
                            embed = discord.Embed(title=f"📜 Lyrics: {query}", description=lyrics_text, color=0x5865F2)
                            return await interaction.followup.send(embed=embed)

        await interaction.followup.send(embed=status_embed("Lyrics Not Found", f"Could not locate lyrics for `{query}`.", "warning"))

    # --- AUDIO EQUALIZERS & VOLUME ---

    @app_commands.command(name="volume", description="Set audio volume (1-100)")
    async def volume(self, interaction: discord.Interaction, level: int):
        if not (1 <= level <= 100):
            return await interaction.response.send_message(embed=status_embed("Error", "Volume must be 1-100.", "warning"), ephemeral=True)

        guild_id = interaction.guild_id
        self.guild_volume[guild_id] = level / 100.0
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = self.guild_volume[guild_id]
        await interaction.response.send_message(embed=status_embed("Volume", f"Volume set to **{level}%**."))

    @app_commands.command(name="filter", description="Apply FFmpeg audio filter presets")
    @app_commands.choices(preset=[
        app_commands.Choice(name="Off", value="off"),
        app_commands.Choice(name="Bass Boost", value="bassboost"),
        app_commands.Choice(name="Nightcore", value="nightcore"),
        app_commands.Choice(name="Vaporwave", value="vaporwave"),
        app_commands.Choice(name="8D Audio", value="8d")
    ])
    async def set_filter(self, interaction: discord.Interaction, preset: app_commands.Choice[str]):
        guild_id = interaction.guild_id
        self.current_filter[guild_id] = preset.value
        await interaction.response.send_message(embed=status_embed("Filter Updated", f"Audio preset set to **{preset.name}**."))

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=status_embed("Pong! 🏓", f"Latency: **{round(self.bot.latency * 1000)}ms**"))

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCommands(bot))