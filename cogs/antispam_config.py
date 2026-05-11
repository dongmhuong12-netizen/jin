# cogs/antispam_config.py
import discord
from discord import app_commands
from discord.ext import commands
import sys
import os

sys.path.append(os.getcwd())
try:
    from constants import COLOR_GENERAL
except ImportError:
    COLOR_GENERAL = 0x010101

class AntiSpamConfig(commands.GroupCog, name="antispam"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="toggle", description="Bật/Tắt chi tiết Anti-Spam")
    @app_commands.choices(type=[
        app_commands.Choice(name="Hệ thống", value="active"),
        app_commands.Choice(name="Tin nhắn", value="check_messages"),
        app_commands.Choice(name="Link", value="check_links"),
        app_commands.Choice(name="Tag", value="check_mentions")
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle(self, interaction: discord.Interaction, status: bool, type: str = "active"):
        await interaction.response.defer(ephemeral=True)
        key = "antispam_active" if type == "active" else type
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {key: status}},
            upsert=True
        )
        await interaction.followup.send(f"🛡️ {type} đã gán: {status}")

    @app_commands.command(name="setup-channels", description="Gán kênh báo cáo")
    async def set_chans(self, interaction: discord.Interaction, silence: discord.TextChannel, audit: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"silence_channel": silence.id, "audit_log_channel": audit.id}},
            upsert=True
        )
        await interaction.followup.send("✅ Đã gán kênh.")

class Whitelist(commands.GroupCog, name="whitelist"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add-user", description="Thêm User")
    async def add_u(self, interaction: discord.Interaction, user_id: str):
        await interaction.response.defer(ephemeral=True)
        if not user_id.isdigit(): return await interaction.followup.send("ID sai.")
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$addToSet": {"whitelist_users": int(user_id)}},
            upsert=True
        )
        await interaction.followup.send(f"✅ Thêm User {user_id}")

    @app_commands.command(name="add-role", description="Thêm Role")
    async def add_r(self, interaction: discord.Interaction, role_id: str):
        await interaction.response.defer(ephemeral=True)
        if not role_id.isdigit(): return await interaction.followup.send("ID sai.")
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$addToSet": {"whitelist_roles": int(role_id)}},
            upsert=True
        )
        await interaction.followup.send(f"✅ Thêm Role {role_id}")

async def setup(bot):
    await bot.add_cog(AntiSpamConfig(bot))
    await bot.add_cog(Whitelist(bot))


