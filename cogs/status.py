# cogs/status.py
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
        # TƯ DUY MULTI-IT: Khởi tạo Object Process 1 lần duy nhất để tiết kiệm System Calls.
        # Khi gọi lệnh .memory_info() ở dưới, nó vẫn lấy data real-time theo thời gian thực.
        self.process = psutil.Process(os.getpid())

    @app_commands.command(name="jin", description="Bảng điều khiển sức khỏe của Jin")
    async def jin_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) # Tránh bị timeout lệnh
        
        # 1. Tính toán Latency WS
        ws_latency = round(self.bot.latency * 1000)
        
        # 2. Ping thử vào DB để check kết nối (Có phòng thủ NoneType)
        db_status = "❤️ Mất kết nối"
        db_latency = 0
        
        if self.bot.db is not None:
            start_time = time.perf_counter()
            try:
                await self.bot.db.command("ping")
                db_status = "💚 Tốt"
                end_time = time.perf_counter()
                db_latency = round((end_time - start_time) * 1000)
            except Exception:
                pass # Bỏ qua, giữ nguyên trạng thái mất kết nối

        # 3. Thông số hệ thống chuẩn thời gian thực (Real-time)
        ram_usage = round(self.process.memory_info().rss / 1024 / 1024, 2) # MB
        uptime = datetime.datetime.now(datetime.timezone.utc) - self.start_time
        
        # Format thời gian Uptime dễ nhìn
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # 4. Thông số quy mô (Phòng thủ member_count bị None ở một số server chưa sync kịp)
        guild_count = len(self.bot.guilds)
        user_count = sum(guild.member_count for guild in self.bot.guilds if guild.member_count)

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
