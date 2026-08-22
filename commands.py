import os
import random
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

from embeds import now_playing_embed, queue_embed, status_embed, InteractiveMusicView

# Preset Audio Filters (FFmpeg options)
AUDIO_FILTERS = {
    "off": "",
    "bassboost": "-af equalizer=f=50:width_type=h:width=100:g=15",
    "nightcore": "-af asetrate=44100*1.25,aresample=44100,equalizer=f=40:width_type=h:width=50:g=5",
    "vaporwave": "-af asetrate=44100*0.8,aresample=44100",
    "8d": "-af apulsator=hz=0.125"
}

class MusicCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues = {}
        self.now_playing = {}
        self.guild_volume = {}
        self.loop_modes = {}  # 'off', 'song', 'queue'
        self.current_filter = {}

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

    def get_ffmpeg_options(self, guild_id: int):
        filter_str = AUDIO_FILTERS.get(self.current_filter.get(guild_id, "off"), "")
        options = '-vn'
        if filter_str:
            options += f" {filter_str}"
        return {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': options
        }

    def play_next(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        vc = interaction.guild.voice_client
        if not vc:
            return

        current = self.now_playing.get(guild_id)
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

    # --- MUSIC PLAYBACK COMMANDS ---

    @app_commands.command(name="play", description="Play a track or add it to queue")
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(
                embed=status_embed("Voice Error", "Join a Voice Channel first!", "danger"), ephemeral=True
            )

        await interaction.response.defer()
        voice_channel = interaction.user.voice.channel
        guild_id = interaction.guild_id

        if interaction.guild.voice_client is None:
            vc = await voice_channel.connect()
        else:
            vc = interaction.guild.voice_client
            if vc.channel != voice_channel:
                await vc.move_to(voice_channel)

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
                return await interaction.followup.send(
                    embed=status_embed("Extraction Error", f"Failed to fetch track: {err}", "danger")
                )

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

    @app_commands.command(name="pause", description="Pause current audio playback")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message(embed=status_embed("Paused", "Playback paused."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Nothing is playing.", "warning"), ephemeral=True)

    @app_commands.command(name="resume", description="Resume paused audio")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message(embed=status_embed("Resumed", "Playback resumed."))
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

    @app_commands.command(name="skipto", description="Skip directly to a specific position in queue")
    async def skipto(self, interaction: discord.Interaction, position: int):
        guild_id = interaction.guild_id
        q = self.queues.get(guild_id, [])
        if 1 <= position <= len(q):
            self.queues[guild_id] = q[position - 1:]
            vc = interaction.guild.voice_client
            if vc:
                vc.stop()
            await interaction.response.send_message(embed=status_embed("Skipped", f"Jumped directly to position #{position}."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Invalid position in queue.", "warning"), ephemeral=True)

    @app_commands.command(name="stop", description="Stop music and wipe queue")
    async def stop(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        if guild_id in self.queues:
            self.queues[guild_id].clear()
        self.now_playing[guild_id] = None
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await interaction.response.send_message(embed=status_embed("Stopped", "Cleared queue and stopped audio."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Not connected to voice.", "warning"), ephemeral=True)

    # --- QUEUE MANAGEMENT ---

    @app_commands.command(name="queue", description="Display current queue")
    async def queue_cmd(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        q = self.queues.get(guild_id, [])
        current = self.now_playing.get(guild_id)
        await interaction.response.send_message(embed=queue_embed(q, current))

    @app_commands.command(name="nowplaying", description="Show active track details")
    async def nowplaying(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        song = self.now_playing.get(guild_id)
        if not song:
            return await interaction.response.send_message(embed=status_embed("Idle", "Nothing playing.", "warning"), ephemeral=True)
        vol = int(self.guild_volume.get(guild_id, 0.5) * 100)
        embed = now_playing_embed(song, vol, self.loop_modes.get(guild_id, 'off'))
        view = InteractiveMusicView(self.bot, guild_id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="shuffle", description="Shuffle current queue")
    async def shuffle(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        q = self.queues.get(guild_id, [])
        if len(q) > 1:
            random.shuffle(q)
            await interaction.response.send_message(embed=status_embed("Shuffled", f"Shuffled {len(q)} tracks."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Need at least 2 tracks to shuffle.", "warning"), ephemeral=True)

    @app_commands.command(name="clear", description="Clear all queued tracks")
    async def clear(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        if guild_id in self.queues:
            self.queues[guild_id].clear()
            await interaction.response.send_message(embed=status_embed("Cleared", "Emptied queue."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Queue is already empty.", "warning"), ephemeral=True)

    @app_commands.command(name="remove", description="Remove track by queue index")
    async def remove(self, interaction: discord.Interaction, index: int):
        guild_id = interaction.guild_id
        q = self.queues.get(guild_id, [])
        if 1 <= index <= len(q):
            removed = q.pop(index - 1)
            await interaction.response.send_message(embed=status_embed("Removed", f"Removed `{removed['title']}`."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Invalid position index.", "warning"), ephemeral=True)

    @app_commands.command(name="move", description="Move track position in queue")
    async def move(self, interaction: discord.Interaction, from_pos: int, to_pos: int):
        guild_id = interaction.guild_id
        q = self.queues.get(guild_id, [])
        if 1 <= from_pos <= len(q) and 1 <= to_pos <= len(q):
            track = q.pop(from_pos - 1)
            q.insert(to_pos - 1, track)
            await interaction.response.send_message(embed=status_embed("Moved", f"Moved `{track['title']}` to position #{to_pos}."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Invalid positions specified.", "warning"), ephemeral=True)

    @app_commands.command(name="loop", description="Set loop mode")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Off", value="off"),
        app_commands.Choice(name="Song", value="song"),
        app_commands.Choice(name="Queue", value="queue")
    ])
    async def loop(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        guild_id = interaction.guild_id
        self.loop_modes[guild_id] = mode.value
        await interaction.response.send_message(embed=status_embed("Loop Mode", f"Loop mode set to **{mode.name}**."))

    # --- AUDIO CONTROLS & FILTERS ---

    @app_commands.command(name="volume", description="Set volume level (1-100)")
    async def volume(self, interaction: discord.Interaction, level: int):
        if not (1 <= level <= 100):
            return await interaction.response.send_message(embed=status_embed("Error", "Volume must be 1-100.", "warning"), ephemeral=True)

        guild_id = interaction.guild_id
        self.guild_volume[guild_id] = level / 100.0
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = self.guild_volume[guild_id]
        await interaction.response.send_message(embed=status_embed("Volume", f"Volume set to **{level}%**."))

    @app_commands.command(name="filter", description="Apply FFmpeg audio equalizers")
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
        await interaction.response.send_message(embed=status_embed("Filter Updated", f"Audio preset set to **{preset.name}**. (Applies on next track)"))

    # --- UTILITY COMMANDS ---

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(embed=status_embed("Pong! 🏓", f"Bot Latency: **{latency}ms**"))

    @app_commands.command(name="botinfo", description="View bot specifications and guild count")
    async def botinfo(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🤖 Cyber Music Engine Info", color=0x5865F2)
        embed.add_field(name="Servers Connected", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name="Library", value="`discord.py v2.4+`", inline=True)
        embed.add_field(name="Runtime Environment", value="`Docker on Render`", inline=True)
        embed.set_footer(text="24/7 Cloud Architecture")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leave", description="Disconnect bot from voice channel")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message(embed=status_embed("Disconnected", "Left voice channel."))
        else:
            await interaction.response.send_message(embed=status_embed("Error", "Not connected to voice.", "warning"), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCommands(bot))