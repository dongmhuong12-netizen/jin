# cogs/antispam_config.py
import discord
from discord import app_commands
from discord.ext import commands
import sys
import os

# --- TƯ DUY IT: FIX LỖI IMPORT TRÊN RENDER ---
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
        """Đồng bộ RAM ngay lập tức sau khi sửa DB"""
        antispam_cog = self.bot.get_cog("AntiSpam")
        if antispam_cog:
            doc = await self.bot.db.server_settings.find_one({"guild_id": guild_id})
            if doc:
                antispam_cog.config_cache[guild_id] = {**DEFAULT_CONFIG, **doc}
            else:
                antispam_cog.config_cache[guild_id] = DEFAULT_CONFIG

    @app_commands.command(name="settings", description="Xem chi tiết thiết lập Anti-Spam của server")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def check_settings(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        gid = interaction.guild.id
        doc = await self.bot.db.server_settings.find_one({"guild_id": gid}) or {}
        config = {**DEFAULT_CONFIG, **doc}

        embed = discord.Embed(
            title=f"🛡️ Dashboard Anti-Spam | {interaction.guild.name}",
            color=COLOR_GENERAL,
            timestamp=discord.utils.utcnow()
        )

        # 1. Trạng thái Module
        def get_stat(key): return "✅ Bật" if config.get(key) else "❌ Tắt"
        status_v = (
            f"**Hệ thống chính:** {get_stat('active')}\n"
            f"**Flooding:** {get_stat('check_messages')} | **Spam Tag:** {get_stat('check_mentions')} | **Links:** {get_stat('check_links')}"
        )
        embed.add_field(name="📡 Trạng thái Module", value=status_v, inline=False)

        # 2. Ngưỡng trừng phạt
        limits_v = (
            f"**• Tag tối đa:** `{config.get('max_mentions', 5)}`/tin\n"
            f"**• Tin nhanh:** `{config.get('max_messages', 7)}`/3s\n"
            f"**• Link:** `{config.get('max_links', 3)}`/5s"
        )
        embed.add_field(name="⚙️ Ngưỡng vi phạm", value=limits_v, inline=True)

        # 3. Kênh hệ thống
        silence_ch = f"<#{config.get('silence_channel')}>" if config.get('silence_channel') else "`Chưa set`"
        audit_ch = f"<#{config.get('audit_log_channel')}>" if config.get('audit_log_channel') else "`Chưa set`"
        embed.add_field(name="📺 Kênh thông báo", value=f"**Silence:** {silence_ch}\n**Audit:** {audit_ch}", inline=True)

        # 4. Ngoại lệ (Whitelist)
        u_list = [f"<@{u}>" for u in config.get("whitelist_users", [])]
        r_list = [f"<@&{r}>" for r in config.get("whitelist_roles", [])]
        embed.add_field(name="🏳️ Ngoại lệ (Users)", value=", ".join(u_list) if u_list else "`Trống`", inline=False)
        embed.add_field(name="🛡️ Ngoại lệ (Roles)", value=", ".join(r_list) if r_list else "`Trống`", inline=False)

        # 5. Đối tượng đang bị xử lý Timeout
        punished = [f"{m.mention} (Hết hạn: <t:{int(m.timed_out_until.timestamp())}:R>)" 
                    for m in interaction.guild.members if m.timed_out_until]
        embed.add_field(name="🔨 Danh sách đang khóa mõm", value="\n".join(punished[:10]) if punished else "✅ Không có ai.", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="toggle", description="Bật/Tắt module bảo vệ")
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
        await self.bot.db.server_settings.update_one({"guild_id": interaction.guild.id}, {"$set": {key: status}}, upsert=True)
        await self._update_system_cache(interaction.guild.id)
        await interaction.followup.send(f"🛡️ Module `{module}` -> **{status}**")

    @app_commands.command(name="setup-channels", description="Gán kênh Silence và Audit Log")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_chans(self, interaction: discord.Interaction, silence: discord.TextChannel, audit: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id}, {"$set": {"silence_channel": silence.id, "audit_log_channel": audit.id}}, upsert=True
        )
        await self._update_system_cache(interaction.guild.id)
        await interaction.followup.send("✅ Cấu hình kênh thành công.")

class Whitelist(commands.GroupCog, name="whitelist"):
    def __init__(self, bot):
        self.bot = bot

    # --- AUTOCOMPLETE: CHỈ HIỆN NHỮNG GÌ CÓ TRONG DB ---
    async def user_autocomplete(self, interaction: discord.Interaction, current: str):
        doc = await self.bot.db.server_settings.find_one({"guild_id": interaction.guild.id}) or {}
        user_ids = doc.get("whitelist_users", [])
        choices = []
        for uid in user_ids:
            member = interaction.guild.get_member(uid)
            label = member.display_name if member else f"User ID: {uid}"
            if current.lower() in label.lower():
                choices.append(app_commands.Choice(name=label, value=str(uid)))
        return choices[:25]

    async def role_autocomplete(self, interaction: discord.Interaction, current: str):
        doc = await self.bot.db.server_settings.find_one({"guild_id": interaction.guild.id}) or {}
        role_ids = doc.get("whitelist_roles", [])
        choices = []
        for rid in role_ids:
            role = interaction.guild.get_role(rid)
            label = role.name if role else f"Role ID: {rid}"
            if current.lower() in label.lower():
                choices.append(app_commands.Choice(name=label, value=str(rid)))
        return choices[:25]

    @app_commands.command(name="add", description="Thêm User hoặc Role vào whitelist")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_whitelist(self, interaction: discord.Interaction, user: discord.Member = None, role: discord.Role = None):
        await interaction.response.defer(ephemeral=True)
        if not user and not role: return await interaction.followup.send("❌ Cậu phải chọn một User hoặc Role.")
        u_q = {}
        if user: u_q["whitelist_users"] = user.id
        if role: u_q["whitelist_roles"] = role.id
        await self.bot.db.server_settings.update_one({"guild_id": interaction.guild.id}, {"$addToSet": u_q}, upsert=True)
        cfg = self.bot.get_cog("AntiSpamConfig")
        if cfg: await cfg._update_system_cache(interaction.guild.id)
        await interaction.followup.send(f"✅ Đã thêm vào danh sách ngoại lệ.")

    @app_commands.command(name="remove", description="Xóa khỏi whitelist")
    @app_commands.autocomplete(user_id=user_autocomplete, role_id=role_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_whitelist(self, interaction: discord.Interaction, user_id: str = None, role_id: str = None):
        await interaction.response.defer(ephemeral=True)
        if not user_id and not role_id: return await interaction.followup.send("⚠️ Hãy chọn một đối tượng từ danh sách đề xuất.")
        
        pull_q = {}
        if user_id: pull_q["whitelist_users"] = int(user_id)
        if role_id: pull_q["whitelist_roles"] = int(role_id)
        
        # --- LOGIC IT: KIỂM TRA XEM CÓ THỰC SỰ XÓA ĐƯỢC KHÔNG ---
        res = await self.bot.db.server_settings.update_one({"guild_id": interaction.guild.id}, {"$pull": pull_q})
        
        if res.modified_count == 0:
            return await interaction.followup.send("❌ Đối tượng này không tồn tại trong danh sách whitelist của server.")

        cfg = self.bot.get_cog("AntiSpamConfig")
        if cfg: await cfg._update_system_cache(interaction.guild.id)
        await interaction.followup.send("🗑️ Đã xóa khỏi danh sách ngoại lệ thành công.")

async def setup(bot):
    await bot.add_cog(AntiSpamConfig(bot))
    await bot.add_cog(Whitelist(bot))
