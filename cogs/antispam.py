# cogs/antispam.py - Sửa lỗi Syntax ở dòng 119
import discord
from discord.ext import commands, tasks
import time
import re
from collections import defaultdict
import sys
import os

# Đảm bảo đường dẫn chuẩn
sys.path.append(os.getcwd())
try:
    from constants import COLOR_SILENCE, COLOR_AUDIT
except ImportError:
    COLOR_SILENCE, COLOR_AUDIT = 0x000000, 0x111111

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.msg_cache = defaultdict(lambda: defaultdict(list))
        self.link_cache = defaultdict(lambda: defaultdict(list))
        self.whitelist_cache = {}
        self.update_cache.start()

    def cog_unload(self):
        self.update_cache.cancel()

    @tasks.loop(minutes=2.0)
    async def update_cache(self):
        try:
            async for doc in self.bot.db.server_settings.find():
                gid = doc.get("guild_id")
                if gid:
                    self.whitelist_cache[gid] = {
                        "users": doc.get("whitelist_users", []),
                        "roles": doc.get("whitelist_roles", []),
                        "active": doc.get("antispam_active", True),
                        "check_messages": doc.get("check_messages", True),
                        "check_links": doc.get("check_links", True),
                        "check_mentions": doc.get("check_mentions", True)
                    }
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.id == self.bot.user.id:
            return

        gid = message.guild.id
        uid = message.author.id
        cache = self.whitelist_cache.get(gid, {"active": True, "users": [], "roles": []})

        if not cache.get("active"): return
        if uid in cache.get("users", []): return
        if any(role.id in cache.get("roles", []) for role in message.author.roles): return

        now = time.time()

        if cache.get("check_mentions", True):
            if (len(message.mentions) + len(message.role_mentions)) > 5:
                return await self.execute_punishment(message, "Spam Mention")

        if cache.get("check_messages", True):
            self.msg_cache[gid][uid].append(now)
            self.msg_cache[gid][uid] = [t for t in self.msg_cache[gid][uid] if now - t < 1.0]
            if len(self.msg_cache[gid][uid]) >= 5:
                return await self.execute_punishment(message, "Message Flooding")

        if cache.get("check_links", True):
            if re.search(r'https?://\S+|discord\.gg/\S+', message.content.lower()):
                self.link_cache[gid][uid].append(now)
                self.link_cache[gid][uid] = [t for t in self.link_cache[gid][uid] if now - t < 1.0]
                if len(self.link_cache[gid][uid]) >= 2:
                    return await self.execute_punishment(message, "Link Spam")

    async def execute_punishment(self, message, reason):
        member = message.author
        try:
            until = discord.utils.utcnow() + discord.utils.timedelta(days=28)
            await member.timeout(until, reason=f"Jin Anti-Spam: {reason}")
            await message.channel.purge(limit=5, check=lambda m: m.author == member)

            config = await self.bot.db.server_settings.find_one({"guild_id": message.guild.id}) or {}
            
            sil_id = config.get("silence_channel")
            if sil_id:
                chan = message.guild.get_channel(sil_id)
                if chan:
                    await chan.send(embed=discord.Embed(title="🚫 Trảm", description=f"{member.mention} bị khóa mõm 28 ngày.\nLý do: {reason}", color=COLOR_SILENCE))

            aud_id = config.get("audit_log_channel")
            if aud_id:
                chan = message.guild.get_channel(aud_id)
                if chan:
                    emb = discord.Embed(title="🚨 Audit Log", color=COLOR_AUDIT)
                    emb.add_field(name="User", value=f"{member} ({member.id})")
                    emb.add_field(name="Lý do", value=reason)
                    await chan.send(embed=emb)
        except:
            pass

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))

