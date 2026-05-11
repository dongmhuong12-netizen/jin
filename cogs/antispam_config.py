# cogs/antispam_config.py
import discord
from discord import app_commands
from discord.ext import commands
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from constants import COLOR_GENERAL

class AntiSpamConfig(commands.GroupCog, name="antispam"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="toggle", description="Bật/Tắt hệ thống Anti-Spam của Jin")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle(self, interaction: discord.Interaction, status: bool):
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"antispam_active": status}},
            upsert=True
        )
        msg = "Đã BẬT" if status else "Đã TẮT"
        await interaction.response.send_message(f"🛡️ Hệ thống Anti-Spam {msg}.", ephemeral=True)

    @app_commands.command(name="setup-channels", description="Gán kênh Silence và Audit Log")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_chans(self, interaction: discord.Interaction, silence_channel: discord.TextChannel, audit_channel: discord.TextChannel):
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"silence_channel": silence_channel.id, "audit_log_channel": audit_channel.id}},
            upsert=True
        )
        await interaction.response.send_message("✅ Cập nhật các kênh báo cáo thành công.", ephemeral=True)

class Whitelist(commands.GroupCog, name="whitelist"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add-user", description="Thêm ID User/Bot vào Whitelist")
    async def add_u(self, interaction: discord.Interaction, user_id: str):
        if not user_id.isdigit(): return await interaction.response.send_message("❌ ID không hợp lệ.", ephemeral=True)
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$addToSet": {"whitelist_users": int(user_id)}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Đã thêm User `{user_id}` vào danh sách ngoại lệ.", ephemeral=True)

    @app_commands.command(name="add-role", description="Thêm ID Role vào Whitelist")
    async def add_r(self, interaction: discord.Interaction, role_id: str):
        if not role_id.isdigit(): return await interaction.response.send_message("❌ ID không hợp lệ.", ephemeral=True)
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$addToSet": {"whitelist_roles": int(role_id)}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Đã thêm Role `{role_id}` vào danh sách ngoại lệ.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AntiSpamConfig(bot))
    await bot.add_cog(Whitelist(bot))

