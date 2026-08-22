import discord
from discord import app_commands
from discord.ext import commands

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Helper function to get or create state from main.py or a shared module
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
            st["logs"].append(f"[VC] Connected to #{channel.name} via Discord command by {interaction.user}")
            await interaction.response.send_message(f"✅ Successfully joined **{channel.name}**!")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to connect: {str(e)}", ephemeral=True)

    @app_commands.command(name="play", description="Play a track or add it to the playback queue.")
    @app_commands.describe(query="The song title, keywords, or URL to stream")
    async def slash_play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        st = self.get_state(interaction.guild.id)

        if not interaction.guild.voice_client and interaction.user.voice and interaction.user.voice.channel:
            try:
                await interaction.user.voice.channel.connect()
                st["active_vc_id"] = str(interaction.user.voice.channel.id)
            except Exception:
                pass

        track_item = {
            "id": f"q_{len(st['queue']) + 1000}",
            "title": query.title(),
            "artist": f"Requested by {interaction.user.name}",
            "duration": "3:30",
            "duration_sec": 210,
            "thumbnail": f"https://picsum.photos/seed/{abs(hash(query))}/300/300",
            "added_by": str(interaction.user)
        }

        if not st["current"] or not st["is_playing"]:
            st["current"] = track_item
            st["position_sec"] = 0
            st["is_playing"] = True
            st["is_paused"] = False
            st["logs"].append(f"[EXEC] Stream started for '{query}' via Discord command")
            await interaction.followup.send(f"▶️ Now streaming: **{track_item['title']}**")
        else:
            st["queue"].append(track_item)
            st["logs"].append(f"[QUEUE] Added '{query}' to queue position #{len(st['queue'])}")
            await interaction.followup.send(f"➕ Added to queue (#{len(st['queue'])}): **{track_item['title']}**")

    @app_commands.command(name="pause", description="Pause current music playback.")
    async def slash_pause(self, interaction: discord.Interaction):
        st = self.get_state(interaction.guild.id)
        st["is_paused"] = True
        st["is_playing"] = False
        st["logs"].append("[CTRL] Playback paused via Discord command")
        await interaction.response.send_message("⏸️ Playback suspended.")

    @app_commands.command(name="resume", description="Resume music playback.")
    async def slash_resume(self, interaction: discord.Interaction):
        st = self.get_state(interaction.guild.id)
        st["is_paused"] = False
        st["is_playing"] = True
        st["logs"].append("[CTRL] Playback resumed via Discord command")
        await interaction.response.send_message("▶️ Playback resumed.")

    @app_commands.command(name="skip", description="Skip to the next track in the queue.")
    async def slash_skip(self, interaction: discord.Interaction):
        st = self.get_state(interaction.guild.id)
        if st["queue"]:
            st["current"] = st["queue"].pop(0)
            st["position_sec"] = 0
            st["is_playing"] = True
            st["is_paused"] = False
            st["logs"].append(f"[CTRL] Skipped to '{st['current']['title']}'")
            await interaction.response.send_message(f"⏭️ Skipped! Now playing: **{st['current']['title']}**")
        else:
            await interaction.response.send_message("⚠️ The queue stack is currently empty.", ephemeral=True)

    @app_commands.command(name="queue", description="Display the current playback queue.")
    async def slash_queue(self, interaction: discord.Interaction):
        st = self.get_state(interaction.guild.id)
        current = st["current"]["title"] if st["current"] else "Nothing playing"
        
        desc = f"**Now Playing:**\n🎵 {current}\n\n**Up Next:**\n"
        if st["queue"]:
            for idx, item in enumerate(st["queue"][:10], 1):
                desc += f"`{idx}.` {item['title']} *({item['added_by']})*\n"
        else:
            desc += "*Queue is currently empty.*"

        embed = discord.Embed(title="🎶 Git Music Queue Studio", description=desc, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stop", description="Stop music and disconnect the bot from the voice channel.")
    async def slash_stop(self, interaction: discord.Interaction):
        st = self.get_state(interaction.guild.id)
        st["current"] = None
        st["queue"] = []
        st["is_playing"] = False
        st["is_paused"] = False
        st["active_vc_id"] = None
        
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            
        st["logs"].append("[CTRL] Bot disconnected and queue wiped via Discord command")
        await interaction.response.send_message("⏹️ Stopped playback, cleared queue, and disconnected.")

async def setup(bot):
    await bot.add_cog(MusicCommands(bot))