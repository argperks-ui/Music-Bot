import discord
from discord import app_commands
import yt_dlp
import asyncio

# YTDLP Options for fast searching and audio extraction
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True'}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YDL_OPTIONS)

class MusicControllerView(discord.ui.View):
    def __init__(self, bot, ctx_or_interaction):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Pause/Resume", style=discord.ButtonStyle.primary, emoji="⏯️")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("Bot is not in a voice channel!", ephemeral=True)
        
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Music paused.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Music resumed.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped current track.", ephemeral=True)
        else:
            await interaction.response.send_message("No audio currently playing.", ephemeral=True)

    @discord.ui.button(label="Stop & Disconnect", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def stop_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("⏹️ Stopped playback and disconnected from voice.", ephemeral=True)
        else:
            await interaction.response.send_message("Bot is not connected to any voice channel.", ephemeral=True)

async def setup_music_commands(bot):
    
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

    @bot.tree.command(name="play", description="Search YouTube/Spotify and play a song.")
    @app_commands.describe(search="Song name, keywords, or URL")
    async def play(interaction: discord.Interaction, search: str):
        await interaction.response.defer()

        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.followup.send("❌ You need to be in a voice channel to play music!", ephemeral=True)

        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        if not vc:
            vc = await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)

        # Search logic using yt-dlp
        loop = asyncio.get_running_loop()
        try:
            query = search if search.startswith("http") else f"ytsearch:{search}"
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
            
            if 'entries' in data:
                # Take the first search result
                info = data['entries'][0]
            else:
                info = data

            audio_url = info.get('url')
            title = info.get('title', 'Unknown Titleuploader')
            artist = info.get('uploader', 'Unknown Artist')
            duration = info.get('duration_string', 'Live')
            thumbnail = info.get('thumbnail', 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4')

            source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)

            def after_playing(error):
                if error:
                    print(f"Player error: {error}")

            if vc.is_playing():
                vc.stop()

            vc.play(source, after=after_playing)

            # Build a gorgeous embedded control card
            embed = discord.Embed(
                title="🎶 Now Playing",
                description=f"**[{title}]({info.get('webpage_url', '#')})**",
                color=0x8b5cf6
            )
            embed.add_field(name="Artist / Uploader", value=artist, inline=True)
            embed.add_field(name="Duration", value=duration, inline=True)
            embed.set_thumbnail(url=thumbnail)
            embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

            view = MusicControllerView(bot, interaction)
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            await interaction.followup.send(f"❌ Error processing search: `{str(e)}`", ephemeral=True)