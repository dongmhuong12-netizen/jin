#cogs/antispam.py 
import discord
from discord.ext import commands, tasks
import time
import re
from collections import defaultdict
import sys
import os

# Đảm bảo Python tìm thấy constants.py ở thư mục cha
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from constants import COLOR_SILENCE, COLOR_AUDIT

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # RAM Cache để xử lý tốc độ cao cho Multi-server
        self.msg_cache = defaultdict(lambda: defaultdict(list))
        self.link_cache = defaultdict(lambda: defaultdict(list))
        self.whitelist_cache = {} # {guild_id: {"users": [], "roles": [], "active": True}}
        
        self.update_cache.start()

    def cog_unload(self):
        self.update_cache.cancel()

    @tasks.loop(minutes=2.0)
    async def update_cache(self):
        """Đồng bộ Whitelist từ MongoDB vào RAM mỗi 2 phút."""
        try:
            async for doc in self.bot.db.server_settings.find():
                gid = doc.get("guild_id")
                self.whitelist_cache[gid] = {
                    "users": doc.get("whitelist_users", []),
                    "roles": doc.get("whitelist_roles", []),
                    "active": doc.get("antispam_active", True)
                }
        except Exception as e:
            print(f"⚠️ Cache Update Error: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        # KHÔNG miễn nhiễm cho Bot. Chỉ miễn nhiễm ID/Role trong trí nhớ.
        if not message.guild or message.author.id == self.bot.user.id:
            return

        gid = message.guild.id
        uid = message.author.id
        
        # Lấy dữ liệu cấu hình từ RAM
        cache = self.whitelist_cache.get(gid, {"active": True, "users": [], "roles": []})
        if not cache["active"]: return

        # KIỂM TRA NGOẠI LỆ (User ID hoặc Role ID)
        if uid in cache["users"]: return
        if any(role.id in cache["roles"] for role in message.author.roles): return

        # 1. CẢM BIẾN MENTION (Check tag trong 1 tin)
        total_mentions = len(message.mentions) + len(message.role_mentions)
        if total_mentions > 5:
            return await self.execute_punishment(message, "Mass Mention Spam")

        # 2. CẢM BIẾN TỐC ĐỘ (Message & Link)
        now = time.time()
        
        # Spam Tin nhắn (5 tin/1s)
        self.msg_cache[gid][uid].append(now)
        self.msg_cache[gid][uid] = [t for t in self.msg_cache[gid][uid] if now - t < 1.0]
        if len(self.msg_cache[gid][uid]) >= 5:
            return await self.execute_punishment(message, "Message Flooding")

        # Spam Link (2 link/1s)
        if re.search(r'https?://\S+|discord\.gg/\S+', message.content.lower()):
            self.link_cache[gid][uid].append(now)
            self.link_cache[gid][uid] = [t for t in self.link_cache[gid][uid] if now - t < 1.0]
            if len(self.link_cache[gid][uid]) >= 2:
                return await self.execute_punishment(message, "Link Spamming")

    async def execute_punishment(self, message, reason):
        member = message.author
        guild = message.guild
        
        try:
            # Trảm: Timeout 28 ngày
            until = discord.utils.utcnow() + discord.utils.timedelta(days=28)
            await member.timeout(until, reason=f"Jin Anti-Spam: {reason}")
            
            # Dọn rác (Purge)
            await message.channel.purge(limit=5, check=lambda m: m.author == member)

            # Lấy kênh Log từ Database
            config = await self.bot.db.server_settings.find_one({"guild_id": guild.id}) or {}
            
            # Kênh Khóa mõm (Public)
            silence_id = config.get("silence_channel")
            if silence_id:
                chan = guild.get_channel(silence_id)
                if chan:
                    embed = discord.Embed(title="🚫 Truy cập bị từ chối", 
                                        description=f"{member.mention} đã bị khóa mõm 28 ngày.\n**Lý do:** {reason}", 
                                        color=COLOR_SILENCE)
                    await chan.send(embed=embed)

            # Kênh Audit Log (Ẩn)
            audit_id = config.get("audit_log_channel")
            if audit_id:
                chan = guild.get_channel(audit_id)
                if chan:
                    embed = discord.Embed(title="🚨 Audit Log: Anti-Spam", color=COLOR_AUDIT)
                    embed.add_field(name="Kẻ vi phạm", value=f"{member} ({member.id})", inline=False)
                    embed.add_field(name="Vi phạm", value=reason, inline=True)
                    embed.add_field(name="Nội dung", value=f"


