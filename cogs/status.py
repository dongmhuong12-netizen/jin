import discord
from discord import app_commands
from discord.ext import commands
import time
import os
import psutil # Cần thêm vào requirements.txt để check RAM/CPU
import datetime

from constants import COLOR_GENERAL

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.datetime.now(datetime.timezone.utc)

    @app_commands.command(name="jin", description="Bảng điều khiển sức khỏe của Jin")
    async def jin_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) # Tránh bị timeout lệnh
        
        # 1. Tính toán Latency
        ws_latency = round(self.bot.latency * 1000)
        start_time = time.perf_counter()
        # Ping thử vào DB để check kết nối
        db_status = "💚 Tốt"
        try:
            await self.bot.db.command("ping")
        except:
            db_status = "❤️ Mất kết nối"
        end_time = time.perf_counter()
        db_latency = round((end_time - start_time) * 1000)

        # 2. Thông số hệ thống (Tư duy IT)
        process = psutil.Process(os.getpid())
        ram_usage = round(process.memory_info().rss / 1024 / 1024, 2) # MB
        uptime = datetime.datetime.now(datetime.timezone.utc) - self.start_time
        
        # Format thời gian Uptime dễ nhìn
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # 3. Thông số quy mô
        guild_count = len(self.bot.guilds)
        user_count = sum(guild.member_count for guild in self.bot.guilds)

        embed = discord.Embed(
            title="🖥️ JIN SYSTEM DASHBOARD",
            description=f"Trạng thái vận hành của hệ thống Anti-Spam",
            color=COLOR_GENERAL,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="📶 Kết nối", value=f"**WS:** `{ws_latency}ms`\n**DB:** `{db_latency}ms` ({db_status})", inline=True)
        embed.add_field(name="⚙️ Tài nguyên", value=f"**RAM:** `{ram_usage} MB`\n**Uptime:** `{uptime_str}`", inline=True)
        embed.add_field(name="📊 Quy mô", value=f"**Servers:** `{guild_count}`\n**Users:** `{user_count:,}`", inline=True)
        
        embed.set_footer(text=f"Phiên bản: Phase 1 (Anti-Spam Focus)")
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))
