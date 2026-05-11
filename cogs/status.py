import discord
from discord import app_commands
from discord.ext import commands
import time
import os
import sys

# Logic IT: Dẫn đường cho Python tìm thấy file constants.py ở thư mục gốc
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__fill__), '..')))
from constants import COLOR_GENERAL

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="jin", description="Kiểm tra tốc độ xử lý của Jin")
    async def jin_status(self, interaction: discord.Interaction):
        ws_latency = round(self.bot.latency * 1000)
        
        start_time = time.time()
        await interaction.response.send_message("Đang kiểm tra...", ephemeral=True)
        end_time = time.time()
        
        api_latency = round((end_time - start_time) * 1000)

        embed = discord.Embed(
            title="Jin đây",
            description=(
                f"**Tốc độ xử lý (api):** `{api_latency}ms`\n"
                f"**Tín hiệu (ws):** `{ws_latency}ms`"
            ),
            color=COLOR_GENERAL
        )
        
        await interaction.edit_original_response(content=None, embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))
