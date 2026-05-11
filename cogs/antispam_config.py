# cogs/antispam_config.py
import discord
from discord import app_commands
from discord.ext import commands
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from constants import COLOR_GENERAL, DEFAULT_CONFIG

class AntiSpamConfig(commands.GroupCog, name="antispam"):
    def __init__(self, bot):
        self.bot = bot

    async def _update_system_cache(self, guild_id: int):
        cog = self.bot.get_cog("AntiSpam")
        if cog:
            doc = await self.bot.db.server_settings.find_one({"guild_id": guild_id})
            cog.config_cache[guild_id] = {**DEFAULT_CONFIG, **doc} if doc else DEFAULT_CONFIG

    @app_commands.command(name="settings", description="Xem Dashboard cấu hình của server")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def settings(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        doc = await self.bot.db.server_settings.find_one({"guild_id": interaction.guild.id}) or {}
        cfg = {**DEFAULT_CONFIG, **doc}

        emb = discord.Embed(title=f"🛡️ Cấu hình: {interaction.guild.name}", color=COLOR_GENERAL)
        def stat(k): return "✅ Bật" if cfg.get(k) else "❌ Tắt"
        
        emb.add_field(name="📡 Modules", value=f"Main: {stat('active')}\nTag: {stat('check_mentions')}\nMess: {stat('check_messages')}", inline=False)
        
        u_list = [f"<@{u}>" for u in cfg.get("whitelist_users", [])]
        emb.add_field(name="🏳️ Whitelist (Users)", value=", ".join(u_list) if u_list else "Trống", inline=False)
        
        punished = [m.mention for m in interaction.guild.members if m.timed_out_until]
        emb.add_field(name="🔨 Đang bị vả", value=", ".join(punished[:10]) if punished else "Sạch sẽ", inline=False)
        
        await interaction.followup.send(embed=emb)

    @app_commands.command(name="toggle", description="Bật/Tắt module")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle(self, interaction: discord.Interaction, module: str, status: bool):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.server_settings.update_one({"guild_id": interaction.guild.id}, {"$set": {module: status}}, upsert=True)
        await self._update_system_cache(interaction.guild.id)
        await interaction.followup.send(f"✅ Đã gán `{module}` thành {status}")

class Whitelist(commands.GroupCog, name="whitelist"):
    def __init__(self, bot):
        self.bot = bot

    async def user_auto(self, it: discord.Interaction, current: str):
        doc = await self.bot.db.server_settings.find_one({"guild_id": it.guild.id}) or {}
        ids = doc.get("whitelist_users", [])
        return [app_commands.Choice(name=it.guild.get_member(uid).display_name if it.guild.get_member(uid) else f"ID: {uid}", value=str(uid)) 
                for uid in ids if current in str(uid)][:25]

    @app_commands.command(name="remove", description="Xóa ngoại lệ (Chỉ hiện đồ trong DB)")
    @app_commands.autocomplete(user_id=user_auto)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove(self, it: discord.Interaction, user_id: str):
        await it.response.defer(ephemeral=True)
        res = await self.bot.db.server_settings.update_one({"guild_id": it.guild.id}, {"$pull": {"whitelist_users": int(user_id)}})
        
        if res.modified_count == 0:
            return await it.followup.send("❌ User này không tồn tại trong danh sách Whitelist.")
        
        cfg_cog = self.bot.get_cog("AntiSpamConfig")
        if cfg_cog: await cfg_cog._update_system_cache(it.guild.id)
        await it.followup.send("🗑️ Đã xóa thành công.")

async def setup(bot):
    await bot.add_cog(AntiSpamConfig(bot))
    await bot.add_cog(Whitelist(bot))
