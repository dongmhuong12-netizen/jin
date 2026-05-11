import discord
from discord import app_commands
from discord.ext import commands
import sys
import os

# --- TƯ DUY IT: FIX LỖI IMPORT TRÊN RENDER ---
# Ép Python tìm kiếm ở thư mục gốc để thấy file constants.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from constants import COLOR_GENERAL, DEFAULT_CONFIG
except ImportError:
    COLOR_GENERAL = 0x010101
    DEFAULT_CONFIG = {
        "active": True, "check_messages": True, "check_links": True, 
        "check_mentions": True, "max_mentions": 5, "max_messages": 7, "max_links": 3
    }

class AntiSpamConfig(commands.GroupCog, name="antispam"):
    def __init__(self, bot):
        self.bot = bot

    async def _update_system_cache(self, guild_id: int):
        """
        Logic then chốt: Cập nhật RAM ngay lập tức sau khi Admin chỉnh sửa DB.
        Tránh delay 2 phút của task loop ở file antispam.py.
        """
        antispam_cog = self.bot.get_cog("AntiSpam")
        if antispam_cog:
            doc = await self.bot.db.server_settings.find_one({"guild_id": guild_id})
            if doc:
                # Merge dữ liệu mặc định với dữ liệu thực tế từ DB
                antispam_cog.config_cache[guild_id] = {**DEFAULT_CONFIG, **doc}
            else:
                antispam_cog.config_cache[guild_id] = DEFAULT_CONFIG

    @app_commands.command(name="toggle", description="Bật/Tắt các module bảo vệ")
    @app_commands.choices(module=[
        app_commands.Choice(name="Toàn bộ hệ thống", value="active"),
        app_commands.Choice(name="Chặn Flood Tin nhắn", value="check_messages"),
        app_commands.Choice(name="Chặn Spam Link", value="check_links"),
        app_commands.Choice(name="Chặn Spam Tag (Mention)", value="check_mentions")
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle(self, interaction: discord.Interaction, module: str, status: bool):
        await interaction.response.defer(ephemeral=True)
        
        key = "active" if module == "active" else module
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {key: status}},
            upsert=True
        )
        
        await self._update_system_cache(interaction.guild.id)
        await interaction.followup.send(f"🛡️ Module `{module}` đã được gán thành: **{status}**")

    @app_commands.command(name="limits", description="Thiết lập ngưỡng trừng phạt (Tư duy IT - Custom thresholds)")
    @app_commands.describe(
        max_mentions="Số tag tối đa/tin",
        max_messages="Số tin nhắn tối đa trong 3s",
        max_links="Số link tối đa trong 5s"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_limits(self, interaction: discord.Interaction, 
                           max_mentions: int = None, 
                           max_messages: int = None, 
                           max_links: int = None):
        await interaction.response.defer(ephemeral=True)
        
        update_data = {}
        if max_mentions is not None: update_data["max_mentions"] = max_mentions
        if max_messages is not None: update_data["max_messages"] = max_messages
        if max_links is not None: update_data["max_links"] = max_links

        if not update_data:
            return await interaction.followup.send("⚠️ Cậu chưa nhập thông số nào.")

        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": update_data},
            upsert=True
        )
        
        await self._update_system_cache(interaction.guild.id)
        await interaction.followup.send("⚙️ Đã cập nhật ngưỡng trừng phạt mới và đồng bộ cache RAM.")

    @app_commands.command(name="setup-channels", description="Gán kênh Silence và Audit Log")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_chans(self, interaction: discord.Interaction, silence: discord.TextChannel, audit: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"silence_channel": silence.id, "audit_log_channel": audit.id}},
            upsert=True
        )
        await self._update_system_cache(interaction.guild.id)
        await interaction.followup.send(f"✅ Đã gán Silence: {silence.mention} và Audit: {audit.mention}")

class Whitelist(commands.GroupCog, name="whitelist"):
    def __init__(self, bot):
        self.bot = bot

    async def _sync(self, gid):
        # Gọi chéo sang Cog AntiSpamConfig để đồng bộ RAM
        cfg_cog = self.bot.get_cog("AntiSpamConfig")
        if cfg_cog: await cfg_cog._update_system_cache(gid)

    @app_commands.command(name="add", description="Thêm User hoặc Role ngoại lệ")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_whitelist(self, interaction: discord.Interaction, 
                            user: discord.Member = None, 
                            role: discord.Role = None):
        await interaction.response.defer(ephemeral=True)
        
        if not user and not role:
            return await interaction.followup.send("❌ Phải chọn ít nhất 1 User hoặc 1 Role.")

        update_query = {}
        if user: update_query["whitelist_users"] = user.id
        if role: update_query["whitelist_roles"] = role.id

        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$addToSet": update_query},
            upsert=True
        )
        
        await self._sync(interaction.guild.id)
        target = user.mention if user else role.name
        await interaction.followup.send(f"✅ Đã thêm {target} vào danh sách miễn tử.")

    @app_commands.command(name="remove", description="Xóa khỏi danh sách ngoại lệ")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_whitelist(self, interaction: discord.Interaction, 
                               user: discord.Member = None, 
                               role: discord.Role = None):
        await interaction.response.defer(ephemeral=True)
        
        update_query = {}
        if user: update_query["whitelist_users"] = user.id
        if role: update_query["whitelist_roles"] = role.id

        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$pull": update_query}
        )
        
        await self._sync(interaction.guild.id)
        await interaction.followup.send("🗑️ Đã xóa đối tượng khỏi Whitelist.")

async def setup(bot):
    await bot.add_cog(AntiSpamConfig(bot))
    await bot.add_cog(Whitelist(bot))
