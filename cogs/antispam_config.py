import discord
from discord import app_commands
from discord.ext import commands
from constants import COLOR_GENERAL, DEFAULT_CONFIG

class AntiSpamConfig(commands.GroupCog, name="antispam"):
    def __init__(self, bot):
        self.bot = bot

    async def _update_system_cache(self, guild_id: int):
        """Helper: Ép buộc Cog AntiSpam cập nhật lại cache ngay lập tức"""
        antispam_cog = self.bot.get_cog("AntiSpam")
        if antispam_cog:
            doc = await self.bot.db.server_settings.find_one({"guild_id": guild_id})
            if doc:
                # Cập nhật trực tiếp vào RAM của Cog AntiSpam
                antispam_cog.config_cache[guild_id] = {**DEFAULT_CONFIG, **doc}

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
        await interaction.followup.send(f"✅ Module `{module}` đã được chuyển sang: **{status}**")

    @app_commands.command(name="limits", description="Thiết lập ngưỡng trừng phạt")
    @app_commands.describe(
        max_mentions="Số tag tối đa/tin (Mặc định: 5)",
        max_messages="Số tin nhắn tối đa/3s (Mặc định: 7)",
        max_links="Số link tối đa/5s (Mặc định: 3)"
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
            return await interaction.followup.send("⚠️ Cậu chưa nhập thông số nào để thay đổi.")

        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": update_data},
            upsert=True
        )
        
        await self._update_system_cache(interaction.guild.id)
        await interaction.followup.send(f"⚙️ Đã cập nhật ngưỡng trừng phạt mới.")

    @app_commands.command(name="setup-channels", description="Cấu hình kênh Silence và Audit Log")
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
        cfg_cog = self.bot.get_cog("AntiSpamConfig")
        if cfg_cog: await cfg_cog._update_system_cache(gid)

    @app_commands.command(name="add", description="Thêm User hoặc Role vào danh sách ngoại lệ")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_whitelist(self, interaction: discord.Interaction, 
                            user: discord.Member = None, 
                            role: discord.Role = None):
        await interaction.response.defer(ephemeral=True)
        
        if not user and not role:
            return await interaction.followup.send("❌ Cậu phải chọn ít nhất 1 User hoặc 1 Role.")

        update_query = {}
        if user: update_query["whitelist_users"] = user.id
        if role: update_query["whitelist_roles"] = role.id

        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$addToSet": update_query},
            upsert=True
        )
        
        await self._sync(interaction.guild.id)
        name = (user.name if user else role.name)
        await interaction.followup.send(f"✅ Đã thêm `{name}` vào danh sách miễn tử.")

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
        await interaction.followup.send(f"🗑️ Đã xóa đối tượng khỏi danh sách whitelist.")

async def setup(bot):
    await bot.add_cog(AntiSpamConfig(bot))
    await bot.add_cog(Whitelist(bot))
