# cogs/antispam.py
import discord
from discord.ext import commands, tasks
import time
import re
from collections import defaultdict
import sys
import os

# --- TƯ DUY IT: FIX LỖI IMPORT TRÊN RENDER ---
# Giúp Bot tìm thấy file constants.py và folder utils/ ở thư mục gốc khi chạy trên Linux/Render
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from constants import COLOR_SILENCE, COLOR_AUDIT, DEFAULT_CONFIG
    from utils.time_converter import MAX_TIMEOUT_SECONDS
except ImportError:
    # Dự phòng để tránh sập Bot nếu môi trường chưa ổn định
    COLOR_SILENCE, COLOR_AUDIT = 0x000000, 0x111111
    MAX_TIMEOUT_SECONDS = 2419200
    DEFAULT_CONFIG = {
        "active": True, "check_messages": True, "check_links": True, 
        "check_mentions": True, "max_mentions": 5, "max_messages": 7, "max_links": 3
    }

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache RAM để xử lý tốc độ cao (Rolling Windows)
        self.msg_cache = defaultdict(lambda: defaultdict(list))
        self.link_cache = defaultdict(lambda: defaultdict(list))
        self.mention_cache = defaultdict(lambda: defaultdict(list))
        
        self.config_cache = {} # Lưu cấu hình từ MongoDB
        self.update_cache.start()

    def cog_unload(self):
        self.update_cache.cancel()

    @tasks.loop(minutes=2.0)
    async def update_cache(self):
        """Đồng bộ cấu hình từ MongoDB vào RAM mỗi 2 phút"""
        try:
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

        # Lấy config từ cache RAM (ưu tiên tốc độ)
        config = self.config_cache.get(gid, DEFAULT_CONFIG)
        if not config.get("active"): return
        
        # 2. Check Whitelist
        if self.is_whitelisted(message, config): return

        # --- LOGIC KIỂM TRA (GẮT - QUÉT TOÀN DIỆN) ---

        # A. SPAM MENTION (Sửa lỗi bot ngó lơ bằng Regex)
        if config.get("check_mentions"):
            # Quét text thô để bắt mọi lượt tag <@ID>, <@!ID>, <@&ID>
            raw_mentions = re.findall(r'<@!?\d+>|<@&\d+>', message.content)
            mention_count = len(raw_mentions)
            if message.mention_everyone: mention_count += 1
            
            # Ngưỡng trảm trong 1 tin nhắn
            if mention_count >= config.get("max_mentions", 5):
                return await self.execute_punishment(message, "Spam Mention (Exceeded limit)")

            # Kiểm tra tần suất tag qua nhiều tin nhắn (3 tin có tag trong 5 giây)
            if mention_count > 0:
                self.mention_cache[gid][uid].append(now)
                self.mention_cache[gid][uid] = [t for t in self.mention_cache[gid][uid] if now - t < 5.0]
                if len(self.mention_cache[gid][uid]) >= 3:
                     return await self.execute_punishment(message, "Mention Exhaustion")

        # B. MESSAGE FLOODING (Spam tin nhắn nhanh)
        if config.get("check_messages"):
            self.msg_cache[gid][uid].append(now)
            self.msg_cache[gid][uid] = [t for t in self.msg_cache[gid][uid] if now - t < 3.0]
            if len(self.msg_cache[gid][uid]) >= config.get("max_messages", 7):
                return await self.execute_punishment(message, "Message Flooding")

        # C. LINK SPAM (Gửi link liên tục)
        if config.get("check_links"):
            if re.search(r'https?://\S+|discord\.gg/\S+', message.content.lower()):
                self.link_cache[gid][uid].append(now)
                self.link_cache[gid][uid] = [t for t in self.link_cache[gid][uid] if now - t < 5.0]
                if len(self.link_cache[gid][uid]) >= config.get("max_links", 3):
                    return await self.execute_punishment(message, "Link Spam")

    async def execute_punishment(self, message, reason):
        """Hàm trảm: Timeout + Xóa tin + Log lỗi chi tiết"""
        member = message.author
        guild = message.guild
        config = self.config_cache.get(guild.id, DEFAULT_CONFIG)

        try:
            # 1. Kiểm tra quyền Administrator (Giới hạn cứng của Discord)
            if member.guild_permissions.administrator:
                return await message.channel.send(
                    f"⚠️ Không thể trảm {member.mention} vì đối tượng có quyền **Administrator**.\n"
                    f"Discord cấm timeout Admin bất kể Role bot cao đến đâu."
                )

            # 2. Kiểm tra Hierarchy (Vị trí Role)
            if member.top_role.position >= guild.me.top_role.position:
                return await message.channel.send(
                    f"❌ Thất bại: Role của {member.mention} cao hơn hoặc bằng Jin.\n"
                    f"Thứ bậc Role: `{member.top_role.position}` >= `{guild.me.top_role.position}`"
                )

            # 3. Thực thi Timeout 28 ngày
            until = discord.utils.utcnow() + discord.utils.timedelta(seconds=MAX_TIMEOUT_SECONDS)
            await member.timeout(until, reason=f"Jin Anti-Spam: {reason}")

            # 4. Dọn dẹp tin nhắn bẩn
            try:
                await message.channel.purge(limit=10, check=lambda m: m.author == member)
            except discord.Forbidden:
                await message.channel.send("📌 Đã khóa mõm nhưng Jin thiếu quyền **Manage Messages** để dọn tin.")

            # 5. Gửi Embed Silence
            embed_silence = discord.Embed(
                title="🚫 HỆ THỐNG SILENCE",
                description=f"**Đối tượng:** {member.mention}\n**Hành vi:** {reason}\n**Hình phạt:** Timeout 28 ngày",
                color=COLOR_SILENCE
            )
            target_id = config.get("silence_channel")
            chan = guild.get_channel(target_id) if target_id else message.channel
            if chan: await chan.send(embed=embed_silence)

            # 6. Audit Log (Gửi vào kênh log nếu có)
            audit_id = config.get("audit_log_channel")
            if audit_id:
                audit_chan = guild.get_channel(audit_id)
                if audit_chan:
                    emb = discord.Embed(title="🚨 AUDIT LOG", color=COLOR_AUDIT)
                    emb.add_field(name="User", value=f"{member} (`{member.id}`)")
                    emb.add_field(name="Lý do", value=reason)
                    await audit_chan.send(embed=emb)

        except discord.Forbidden:
            await message.channel.send(f"❌ Lỗi 403: Discord từ chối lệnh trảm đối với {member.name}.")
        except Exception as e:
            await message.channel.send(f"⚠️ Lỗi hệ thống: `{str(e)}`")

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
