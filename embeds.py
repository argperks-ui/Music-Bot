import discord

# Theme Colors
COLOR_PRIMARY = 0x5865F2  # Blurple
COLOR_SUCCESS = 0x57F287  # Green
COLOR_WARNING = 0xFEE75C  # Yellow
COLOR_DANGER = 0xED4245   # Red

def now_playing_embed(song: dict, volume: int, loop_mode: str) -> discord.Embed:
    embed = discord.Embed(
        title="🎵 Now Playing",
        description=f"[{song['title']}]({song.get('webpage_url', song['url'])})",
        color=COLOR_PRIMARY
    )
    if 'thumbnail' in song and song['thumbnail']:
        embed.set_thumbnail(url=song['thumbnail'])
    
    embed.add_field(name="Duration", value=song.get('duration_string', 'Live Stream'), inline=True)
    embed.add_field(name="Requested By", value=song.get('requester', 'Unknown'), inline=True)
    embed.add_field(name="Volume", value=f"{volume}%", inline=True)
    embed.add_field(name="Loop Status", value=loop_mode.capitalize(), inline=True)
    embed.set_footer(text="Cyber Music Engine • Render Cloud")
    return embed

def queue_embed(queue: list, current_song: dict) -> discord.Embed:
    embed = discord.Embed(title="🎶 Audio Queue", color=COLOR_PRIMARY)
    if current_song:
        embed.add_field(
            name="Now Playing",
            value=f"▶️ [{current_song['title']}]({current_song.get('webpage_url', current_song['url'])})",
            inline=False
        )
    
    if not queue:
        embed.add_field(name="Up Next", value="*Queue is currently empty.*", inline=False)
    else:
        queue_list = ""
        for idx, song in enumerate(queue[:10], start=1):
            queue_list += f"`{idx}.` [{song['title']}]({song.get('webpage_url', song['url'])})\n"
        if len(queue) > 10:
            queue_list += f"\n*...and {len(queue) - 10} more track(s)*"
        embed.add_field(name="Up Next", value=queue_list, inline=False)
    
    embed.set_footer(text=f"Total Queued Tracks: {len(queue)}")
    return embed

def status_embed(title: str, description: str, color_type: str = "success") -> discord.Embed:
    colors = {
        "success": COLOR_SUCCESS,
        "warning": COLOR_WARNING,
        "danger": COLOR_DANGER,
        "info": COLOR_PRIMARY
    }
    return discord.Embed(
        title=title,
        description=description,
        color=colors.get(color_type, COLOR_PRIMARY)
    )

class InteractiveMusicView(discord.ui.View):
    """Interactive Discord UI Buttons attached to player messages"""
    def __init__(self, bot, guild_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="Pause / Resume", style=discord.ButtonStyle.secondary, emoji="⏯️")
    async def toggle_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Paused playback.", ephemeral=True)
        elif vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed playback.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.primary, emoji="⏭️")
    async def skip_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped current track.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing to skip.", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def stop_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog("Music")
        if cog:
            cog.queues[self.guild_id] = []
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await interaction.response.send_message("⏹️ Playback stopped and queue cleared.", ephemeral=True)