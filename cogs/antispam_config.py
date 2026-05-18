# cogs/antispam_config.py
import discord
from discord import app_commands
from discord.ext import commands
from constants import COLOR_GENERAL, DEFAULT_CONFIG

class AntiSpamConfig(commands.GroupCog, name="antispam"):
    def __init__(self, bot):
        self.bot = bot

    async def _update_system_cache(self, guild_id: int):
        """Đồng bộ RAM ngay lập tức sau khi DB thay đổi"""
        cog = self.bot.get_cog("AntiSpam")
        if cog:
            doc = await self.bot.db.server_settings.find_one({"guild_id": guild_id})
            cog.config_cache[guild_id] = {**DEFAULT_CONFIG, **(doc or {})}

    @app_commands.command(name="settings", description="Xem Dashboard cấu hình chi tiết")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def settings(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        doc = await self.bot.db.server_settings.find_one({"guild_id": interaction.guild.id}) or {}
        cfg = {**DEFAULT_CONFIG, **doc}

        emb = discord.Embed(title=f"🛡️ Cấu hình: {interaction.guild.name}", color=COLOR_GENERAL)
        def stat(k): return "✅" if cfg.get(k) else "❌"
        
        emb.add_field(name="📡 Trạng thái", value=f"Hệ thống: {stat('active')}\nTag: {stat('check_mentions')}\nFlood: {stat('check_messages')}\nLink: {stat('check_links')}")
        emb.add_field(name="⚙️ Ngưỡng chặn", value=f"Tag: `{cfg.get('max_mentions', 5)}` | Mess: `{cfg.get('max_messages', 7)}` | Link: `{cfg.get('max_links', 3)}`", inline=False)
        
        silence = f"<#{cfg.get('silence_channel')}>" if cfg.get('silence_channel') else "`Chưa set`"
        audit = f"<#{cfg.get('audit_log_channel')}>" if cfg.get('audit_log_channel') else "`Chưa set`"
        emb.add_field(name="📺 Kênh Log", value=f"Silence: {silence} | Audit: {audit}", inline=False)
        
        # Đã thay thế vòng lặp O(N) quét members bằng thông số thời gian phạt, bảo vệ Event Loop
        duration = cfg.get("punishment_duration", "10m")
        emb.add_field(name="⏱️ Hình phạt (Fallback)", value=f"Thời gian Timeout: `{duration}`", inline=False)
        
        await interaction.followup.send(embed=emb)

    @app_commands.command(name="toggle", description="Bật/Tắt module bảo vệ")
    @app_commands.choices(module=[
        app_commands.Choice(name="Toàn bộ hệ thống", value="active"),
        app_commands.Choice(name="Chặn Flood Tin nhắn", value="check_messages"),
        app_commands.Choice(name="Chặn Spam Link", value="check_links"),
        app_commands.Choice(name="Chặn Spam Tag", value="check_mentions")
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle(self, interaction: discord.Interaction, module: str, status: bool):
        await interaction.response.defer(ephemeral=True)
        key = "active" if module == "active" else module
        await self.bot.db.server_settings.update_one({"guild_id": interaction.guild.id}, {"$set": {key: status}}, upsert=True)
        await self._update_system_cache(interaction.guild.id)
        await interaction.followup.send(f"🛡️ Module `{module}` -> **{status}**")

    @app_commands.command(name="limits", description="Thiết lập ngưỡng trừng phạt")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_limits(self, interaction: discord.Interaction, max_mentions: int = None, max_messages: int = None, max_links: int = None, duration: str = None):
        await interaction.response.defer(ephemeral=True)
        up = {}
        if max_mentions: up["max_mentions"] = max_mentions
        if max_messages: up["max_messages"] = max_messages
        if max_links: up["max_links"] = max_links
        if duration: up["punishment_duration"] = duration # Khớp với logic moderator.py
        
        if not up: return await interaction.followup.send("⚠️ Cần nhập ít nhất 1 thông số.")
        await self.bot.db.server_settings.update_one({"guild_id": interaction.guild.id}, {"$set": up}, upsert=True)
        await self._update_system_cache(interaction.guild.id)
        await interaction.followup.send("⚙️ Đã cập nhật cấu hình ngưỡng và thời gian trừng phạt.")

    @app_commands.command(name="setup-channels", description="Gán kênh Silence và Audit Log")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_chans(self, interaction: discord.Interaction, silence: discord.TextChannel, audit: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id}, 
            {"$set": {"silence_channel": silence.id, "audit_log_channel": audit.id}}, upsert=True
        )
        await self._update_system_cache(interaction.guild.id)
        await interaction.followup.send(f"✅ Đã gán Silence: {silence.mention} và Audit: {audit.mention}")

class Whitelist(commands.GroupCog, name="whitelist"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add", description="Thêm ngoại lệ cho User hoặc Role")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add(self, interaction: discord.Interaction, user: discord.Member = None, role: discord.Role = None):
        await interaction.response.defer(ephemeral=True)
        if not user and not role: return await interaction.followup.send("❌ Chọn 1 Member hoặc 1 Role.")
        q = {}
        if user: q["whitelist_users"] = user.id
        if role: q["whitelist_roles"] = role.id
        await self.bot.db.server_settings.update_one({"guild_id": interaction.guild.id}, {"$addToSet": q}, upsert=True)
        
        # Đã sửa tên Cog chuẩn để đồng bộ RAM thành công
        config_cog = self.bot.get_cog("antispam")
        if config_cog: await config_cog._update_system_cache(interaction.guild.id)
            
        await interaction.followup.send("✅ Đã thêm vào Whitelist.")

    @app_commands.command(name="remove", description="Xóa ngoại lệ (Chỉ đề xuất đồ có sẵn)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove(self, it: discord.Interaction, user_id: str = None, role_id: str = None):
        await it.response.defer(ephemeral=True)
        if not user_id and not role_id: return await it.followup.send("⚠️ Chọn User/Role cần xóa.")
        pull = {}
        if user_id: pull["whitelist_users"] = int(user_id)
        if role_id: pull["whitelist_roles"] = int(role_id)
        res = await self.bot.db.server_settings.update_one({"guild_id": it.guild.id}, {"$pull": pull})
        if res.modified_count == 0: return await it.followup.send("❌ Không tìm thấy trong Whitelist.")
        
        # Đã sửa tên Cog chuẩn
        config_cog = self.bot.get_cog("antispam")
        if config_cog: await config_cog._update_system_cache(it.guild.id)
            
        await it.followup.send("🗑️ Đã xóa khỏi danh sách.")

    # --- SỬA CÚ PHÁP AUTOCOMPLETE CHUẨN DISCORD.PY V2 ---
    @remove.autocomplete('user_id')
    async def user_auto(self, it: discord.Interaction, curr: str):
        doc = await self.bot.db.server_settings.find_one({"guild_id": it.guild.id}) or {}
        ids = doc.get("whitelist_users", [])
        return [app_commands.Choice(name=it.guild.get_member(uid).display_name if it.guild.get_member(uid) else f"ID: {uid}", value=str(uid)) 
                for uid in ids if curr in str(uid)][:25]

    @remove.autocomplete('role_id')
    async def role_auto(self, it: discord.Interaction, curr: str):
        doc = await self.bot.db.server_settings.find_one({"guild_id": it.guild.id}) or {}
        ids = doc.get("whitelist_roles", [])
        return [app_commands.Choice(name=it.guild.get_role(rid).name if it.guild.get_role(rid) else f"ID: {rid}", value=str(rid)) 
                for rid in ids if curr in str(rid)][:25]

async def setup(bot):
    await bot.add_cog(AntiSpamConfig(bot))
    await bot.add_cog(Whitelist(bot))
