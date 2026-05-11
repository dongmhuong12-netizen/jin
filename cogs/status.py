import discord
from discord import app_commands
from discord.ext import commands
import time
from constants import COLOR_GENERAL # Gọi màu đen tuyền từ file constants

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="jin", description="Kiểm tra tốc độ xử lý của Jin")
    async def jin_status(self, interaction: discord.Interaction):
        # 1. Tính toán Tín hiệu (Websocket Latency)
        ws_latency = round(self.bot.latency * 1000)

        # 2. Tính toán Tốc độ xử lý (API Latency)
        start_time = time.time()
        # Gửi một phản hồi tạm thời để lấy mốc thời gian
        await interaction.response.send_message("Đang kiểm tra...", ephemeral=True)
        end_time = time.time()
        api_latency = round((end_time - start_time) * 1000)

        # 3. Tạo Embed "Đen tuyền"
        embed = discord.Embed(
            title="Jin đây",
            description=(
                f"**Tốc độ xử lý (api):** `{api_latency}ms`\n"
                f"**Tín hiệu (ws):** `{ws_latency}ms`"
            ),
            color=COLOR_GENERAL
        )
        
        # Cập nhật lại tin nhắn với Embed
        await interaction.edit_original_response(content=None, embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))
