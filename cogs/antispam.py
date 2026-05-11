# cogs/antispam.py
import discord
from discord.ext import commands, tasks
import time
import re
from collections import defaultdict
import sys
import os

# --- TƯ DUY IT: FIX LỖI IMPORT TRÊN RENDER ---
# Đoạn này giúp Bot tìm thấy file constants.py và folder utils/ ở thư mục gốc
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from constants import COLOR_SILENCE, COLOR_AUDIT, DEFAULT_CONFIG
    from utils.time_converter import MAX_TIMEOUT_SECONDS
except ImportError:
    # Dự phòng nếu đường dẫn vẫn bị lỗi để Bot không sập
    COLOR_SILENCE, COLOR_AUDIT = 0x000000, 0x111111
    MAX_TIMEOUT_SECONDS = 2419200
    DEFAULT_CONFIG = {"active": True, "max_mentions": 5, "check_mentions": True}

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.msg_cache = defaultdict(lambda: defaultdict(list))
        self.link_cache = defaultdict(lambda: defaultdict(list))
        self.mention_cache = defaultdict(lambda: defaultdict(list))
        
        self.config_cache = {} 
        self.update_cache.start()

    def cog_unload(self):
        self.update_cache.cancel()

    @tasks.loop(minutes=2.0)
    async def update_cache(self):
        """Đồng bộ cấu hình từ MongoDB vào RAM để xử lý cực nhanh"""
        try:
            # Truy vấn lấy cấu hình tất cả server
            async for doc in self.bot.db.server_settings.find():
                gid = doc.get("guild_id")
                if gid:
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

        # Lấy config từ cache RAM
        config = self.config_cache.get(gid, DEFAULT_CONFIG)
        if not config.get("active"): return
        
        # 2. Check Whitelist
        if self.is_whitelisted(message, config): return

        # --- LOGIC KIỂM TRA ---

        # A. SPAM MENTION (Fix lỗi ngó lơ bằng Regex)
        if config.get("check_mentions"):
            # Quét text thô để đếm mọi lượt tag user/role
            raw_mentions = re.findall(r'<@!?\d+>|<@&\d+>', message.content)
            mention_count = len(raw_mentions)
            if message.mention_everyone: mention_count += 1
            
            # Kiểm tra ngưỡng trong 1 tin nhắn
            if mention_count >= config.get("max_mentions", 5):
                return await self.execute_punishment(message, "Spam Mention (Exceeded limit)")

            # Kiểm tra tần suất tag (3 tin nhắn có tag trong 5 giây)
            if mention_count > 0:
                self.mention_cache[gid][uid].append(now)
                self.mention_cache[gid][uid] = [t for t in self.mention_cache[gid][uid] if now - t < 5.0]
                if len(self.mention_cache[gid][uid]) >= 3:
                     return await self.execute_punishment(message, "Mention Exhaustion")

        # B. MESSAGE FLOODING
        if config.get("check_messages"):
            self.msg_cache[gid][uid].append(now)
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
        member = message.author
        guild = message.guild
        config = self.config_cache.get(guild.id, DEFAULT_CONFIG)

        try:
            # 1. Timeout tối đa 28 ngày
            until = discord.utils.utcnow() + discord.utils.timedelta(seconds=MAX_TIMEOUT_SECONDS)
            await member.timeout(until, reason=f"Jin Anti-Spam: {reason}")

            # 2. Dọn dẹp tin nhắn vi phạm
            try:
                await message.channel.purge(limit=10, check=lambda m: m.author == member)
            except: pass

            # 3. Thông báo Silence
            embed_silence = discord.Embed(
                title="🚫 HỆ THỐNG SILENCE",
                description=f"**Đối tượng:** {member.mention}\n**Lý do:** {reason}\n**Thời hạn:** 28 ngày",
                color=COLOR_SILENCE
            )
            
            target_id = config.get("silence_channel")
            chan = guild.get_channel(target_id) if target_id else message.channel
            if chan: await chan.send(embed=embed_silence)

            # 4. Audit Log
            audit_id = config.get("audit_log_channel")
            if audit_id:
                audit_chan = guild.get_channel(audit_id)
                if audit_chan:
                    emb = discord.Embed(title="🚨 AUDIT LOG", color=COLOR_AUDIT)
                    emb.add_field(name="User", value=f"{member} (`{member.id}`)")
                    emb.add_field(name="Lý do", value=reason)
                    await audit_chan.send(embed=emb)

        except discord.Forbidden:
            print(f"❌ Không đủ quyền trảm {member.name}")
        except Exception as e:
            print(f"⚠️ Lỗi trảm: {e}")

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
