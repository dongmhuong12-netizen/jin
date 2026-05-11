import discord
from discord.ext import commands, tasks
import time
import re
from collections import defaultdict
import sys
import os

# Cách gọi constants chuẩn IT cho môi trường Linux/Render
sys.path.append(os.getcwd())
try:
    from constants import COLOR_SILENCE, COLOR_AUDIT
except ImportError:
    COLOR_SILENCE = 0x000000
    COLOR_AUDIT = 0x111111

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # RAM Cache phân tách theo Server (Multi-server)
        self.msg_cache = defaultdict(lambda: defaultdict(list))
        self.link_cache = defaultdict(lambda: defaultdict(list))
        self.whitelist_cache = {}
        self.update_cache.start()

    def cog_unload(self):
        self.update_cache.cancel()

    @tasks.loop(minutes=2.0)
    async def update_cache(self):
        """Đồng bộ Whitelist từ DB vào RAM mỗi 2 phút."""
        try:
            async for doc in self.bot.db.server_settings.find():
                gid = doc.get("guild_id")
                if gid:
                    self.whitelist_cache[gid] = {
                        "users": doc.get("whitelist_users", []),
                        "roles": doc.get("whitelist_roles", []),
                        "active": doc.get("antispam_active", True)
                    }
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        # Vả cả Bot, chỉ trừ chính mình và tin nhắn cá nhân
        if not message.guild or message.author.id == self.bot.user.id:
            return

        gid = message.guild.id
        uid = message.author.id
        
        # Lấy dữ liệu cấu hình từ RAM
        cache = self.whitelist_cache.get(gid, {"active": True, "users": [], "roles": []})
        if not cache.get("active", True): return

        # KIỂM TRA NGOẠI LỆ (ID Người dùng hoặc ID Role)
        if uid in cache.get("users", []): return
        if any(role.id in cache.get("roles", []) for role in message.author.roles): return

        # 1. CẢM BIẾN MENTION (Check tag trong 1 tin)
        total_mentions = len(message.mentions) + len(message.role_mentions)
        if total_mentions > 5:
            await self.execute_punishment(message, "Mass Mention Spam")
            return

        # 2. CẢM BIẾN TỐC ĐỘ (Message & Link)
        now = time.time()
        
        # Tin nhắn (5 tin/1s)
        self.msg_cache[gid][uid].append(now)
        self.msg_cache[gid][uid] = [t for t in self.msg_cache[gid][uid] if now - t < 1.0]
        if len(self.msg_cache[gid][uid]) >= 5:
            await self.execute_punishment(message, "Message Flooding")
            return

        # Link (2 link/1s)
        if re.search(r'https?://\S+|discord\.gg/\S+', message.content.lower()):
            self.link_cache[gid][uid].append(now)
            self.link_cache[gid][uid] = [t for t in self.link_cache[gid][uid] if now - t < 1.0]
            if len(self.link_cache[gid][uid]) >= 2:
                await self.execute_punishment(message, "Link Spamming")
                return

    async def execute_punishment(self, message, reason):
        member = message.author
        guild = message.guild
        try:
            # Khóa mõm 28 ngày
            until = discord.utils.utcnow() + discord.utils.timedelta(days=28)
            await member.timeout(until, reason=f"Jin Anti-Spam: {reason}")
            
            # Xóa rác
            await message.channel.purge(limit=5, check=lambda m: m.author == member)

            # Lấy cấu hình kênh log
            config = await self.bot.db.server_settings.find_one({"guild_id": guild.id}) or {}
            
            # Thông báo công khai (Màu đen tuyệt đối)
            silence_id = config.get("silence_channel")
            if silence_id:
                chan = guild.get_channel(silence_id)
                if chan:
                    embed = discord.Embed(
                        title="🚫 Quyền truy cập bị thu hồi", 
                        description=f"{member.mention} đã bị khóa mõm 28 ngày.\n**Lý do:** {reason}", 
                        color=COLOR_SILENCE
                    )
                    await chan.send(embed=embed)

            # Nhật ký ẩn (Audit Log)
            audit_id = config.get("audit_log_channel")
            if audit_id:
                chan = guild.get_channel(audit_id)
                if chan:
                    embed = discord.Embed(title="🚨 Audit Log: Anti-Spam", color=COLOR_AUDIT)
                    embed.add_field(name="Kẻ vi phạm", value=f"{member} ({member.id})", inline=False)
                    embed.add_field(name="Vi phạm", value=reason, inline=True)
                    embed.add_field(name="Nội dung", value=f"


