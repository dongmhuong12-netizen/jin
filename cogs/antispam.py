import discord
from discord.ext import commands, tasks
import time
import re
from collections import defaultdict
import sys
import os

# Import từ file constants và utils
from constants import COLOR_SILENCE, COLOR_AUDIT, DEFAULT_CONFIG
from utils.time_converter import MAX_TIMEOUT_SECONDS

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache lưu trữ tin nhắn: {guild_id: {user_id: [timestamps]}}
        self.msg_cache = defaultdict(lambda: defaultdict(list))
        self.link_cache = defaultdict(lambda: defaultdict(list))
        self.mention_cache = defaultdict(lambda: defaultdict(list))
        
        self.config_cache = {} # Lưu cấu hình server để tránh spam query Mongo
        self.update_cache.start()

    def cog_unload(self):
        self.update_cache.cancel()

    @tasks.loop(minutes=2.0)
    async def update_cache(self):
        """Đồng bộ cấu hình từ MongoDB vào RAM để xử lý cực nhanh"""
        try:
            async for doc in self.bot.db.server_settings.find():
                gid = doc.get("guild_id")
                if gid:
                    # Gộp DEFAULT_CONFIG với dữ liệu từ DB
                    self.config_cache[gid] = {**DEFAULT_CONFIG, **doc}
        except Exception as e:
            print(f"⚠️ Lỗi update cache AntiSpam: {e}")

    def is_whitelisted(self, message, config):
        """Kiểm tra ngoại lệ (Owner, User ID, Role ID)"""
        if message.author.id == message.guild.owner_id: return True
        if message.author.id in config.get("whitelist_users", []): return True
        if any(role.id in config.get("whitelist_roles", []) for role in message.author.roles): return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        # 1. Lọc điều kiện cơ bản
        if not message.guild or message.author.bot: return
        
        gid = message.guild.id
        uid = message.author.id
        now = time.time()

        # Lấy config (nếu chưa có trong cache thì dùng mặc định)
        config = self.config_cache.get(gid, DEFAULT_CONFIG)
        if not config.get("active"): return
        
        # 2. Check Whitelist
        if self.is_whitelisted(message, config): return

        # --- LOGIC KIỂM TRA (TƯ DUY IT: QUÉT TOÀN DIỆN) ---

        # A. SPAM MENTION (Sửa lỗi ngó lơ)
        if config.get("check_mentions"):
            # Đếm tất cả tag: User, Role, Everyone/Here bằng Regex để chính xác tuyệt đối
            raw_mentions = re.findall(r'<@!?\d+>|<@&\d+>', message.content)
            mention_count = len(raw_mentions)
            if message.mention_everyone: mention_count += 1
            
            # Kiểm tra ngưỡng trong 1 tin nhắn
            if mention_count >= config.get("max_mentions", 5):
                return await self.execute_punishment(message, "Spam Mention (Exceeded limit)")

            # Kiểm tra spam tag qua nhiều tin nhắn (Rolling window 5s)
            self.mention_cache[gid][uid].append(now)
            self.mention_cache[gid][uid] = [t for t in self.mention_cache[gid][uid] if now - t < 5.0]
            if len(self.mention_cache[gid][uid]) >= 3: # 3 tin nhắn chứa tag liên tục
                 return await self.execute_punishment(message, "Mention Exhaustion")

        # B. MESSAGE FLOODING (Tần suất gửi tin)
        if config.get("check_messages"):
            self.msg_cache[gid][uid].append(now)
            # Giữ lại các timestamp trong vòng 3 giây
            self.msg_cache[gid][uid] = [t for t in self.msg_cache[gid][uid] if now - t < 3.0]
            if len(self.msg_cache[gid][uid]) >= config.get("max_messages", 7):
                return await self.execute_punishment(message, "Message Flooding")

        # C. LINK SPAM
        if config.get("check_links"):
            if re.search(r'https?://\S+|discord\.gg/\S+', message.content.lower()):
                self.link_cache[gid][uid].append(now)
                self.link_cache[gid][uid] = [t for t in self.link_cache[gid][uid] if now - t < 5.0]
                if len(self.link_cache[gid][uid]) >= config.get("max_links", 3):
                    return await self.execute_punishment(message, "Link Spam")

    async def execute_punishment(self, message, reason):
        """Hàm trảm: Timeout + Clear Mess + Log"""
        member = message.author
        guild = message.guild
        config = self.config_cache.get(guild.id, DEFAULT_CONFIG)

        try:
            # 1. Thực thi Timeout 28 ngày (Max Discord)
            until = discord.utils.utcnow() + discord.utils.timedelta(seconds=MAX_TIMEOUT_SECONDS)
            await member.timeout(until, reason=f"Jin Anti-Spam: {reason}")

            # 2. Xóa tin nhắn bẩn (Tối ưu: Chỉ xóa của kẻ vi phạm)
            await message.channel.purge(limit=10, check=lambda m: m.author == member)

            # 3. Gửi Embed Silence (Kênh hiện tại hoặc kênh Silence cấu hình)
            embed_silence = discord.Embed(
                title="🚫 HỆ THỐNG SILENCE",
                description=f"**Đối tượng:** {member.mention}\n**Hành vi:** {reason}\n**Hình phạt:** Timeout 28 ngày",
                color=COLOR_SILENCE
            )
            embed_silence.set_footer(text="Hệ thống tự động bảo vệ bởi Jin Bot")
            
            target_chan_id = config.get("silence_channel")
            target_chan = guild.get_channel(target_chan_id) if target_chan_id else message.channel
            if target_chan: await target_chan.send(embed=embed_silence)

            # 4. Gửi Audit Log (Nếu có cấu hình)
            audit_id = config.get("audit_log_channel")
            if audit_id:
                audit_chan = guild.get_channel(audit_id)
                if audit_chan:
                    emb_audit = discord.Embed(title="🚨 AUDIT LOG VI PHẠM", color=COLOR_AUDIT)
                    emb_audit.add_field(name="Người vi phạm", value=f"{member} (`{member.id}`)", inline=False)
                    emb_audit.add_field(name="Lý do", value=reason, inline=True)
                    emb_audit.add_field(name="Vị trí", value=message.channel.mention, inline=True)
                    await audit_chan.send(embed=emb_audit)

        except discord.Forbidden:
            print(f"❌ Thiếu quyền xử lý {member.name} tại {guild.name}")
        except Exception as e:
            print(f"⚠️ Lỗi thực thi trảm: {e}")

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
