# cogs/antispam.py
import discord
from discord.ext import commands, tasks
import time
import re
from collections import defaultdict
import sys
import os

# --- TƯ DUY IT: FIX LỖI IMPORT TRÊN RENDER ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from constants import COLOR_SILENCE, COLOR_AUDIT, DEFAULT_CONFIG
    from utils.time_converter import MAX_TIMEOUT_SECONDS
except ImportError:
    COLOR_SILENCE, COLOR_AUDIT = 0x000000, 0x111111
    MAX_TIMEOUT_SECONDS = 2419200
    DEFAULT_CONFIG = {
        "active": True, "check_messages": True, "check_links": True, 
        "check_mentions": True, "max_mentions": 5, "max_messages": 7, "max_links": 3
    }

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Rolling Windows Cache (IT Mindset: Lưu vết trong RAM để xử lý thời gian thực)
        self.msg_cache = defaultdict(lambda: defaultdict(list))
        self.link_cache = defaultdict(lambda: defaultdict(list))
        self.mention_cache = defaultdict(lambda: defaultdict(list))
        
        self.config_cache = {} 
        self.update_cache.start()

    def cog_unload(self):
        self.update_cache.cancel()

    @tasks.loop(minutes=2.0)
    async def update_cache(self):
        """Đồng bộ cấu hình từ MongoDB vào RAM"""
        try:
            async for doc in self.bot.db.server_settings.find():
                gid = doc.get("guild_id")
                if gid:
                    # Gộp cấu hình DB vào Default để tránh thiếu field gây lỗi code
                    self.config_cache[gid] = {**DEFAULT_CONFIG, **doc}
        except Exception as e:
            print(f"⚠️ Lỗi update cache AntiSpam: {e}")

    def is_whitelisted(self, message, config):
        """Kiểm tra ngoại lệ tuyệt đối (Owner, Whitelisted User/Role)"""
        # 1. Chủ server luôn được miễn tử
        if message.author.id == message.guild.owner_id: return True
        # 2. Check danh sách ID User ngoại lệ
        if message.author.id in config.get("whitelist_users", []): return True
        # 3. Check danh sách ID Role ngoại lệ
        if any(role.id in config.get("whitelist_roles", []) for role in message.author.roles): return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        # Lọc cơ bản: Không quét tin nhắn trong DM và không quét Bot
        if not message.guild or message.author.bot: return
        
        gid = message.guild.id
        uid = message.author.id
        now = time.time()

        # Lấy config (Fallback về Default nếu chưa có cấu hình DB)
        config = self.config_cache.get(gid, DEFAULT_CONFIG)
        if not config.get("active"): return
        
        # Check Whitelist trước khi quét logic
        if self.is_whitelisted(message, config): return

        # --- LOGIC KIỂM TRA (DETECTION LAYER) ---

        # 1. PHÁT HIỆN SPAM TAG (MENTIONS)
        if config.get("check_mentions"):
            # Regex quét mọi dạng tag: <@ID>, <@!ID>, <@&ID>
            raw_mentions = re.findall(r'<@!?(\d+)>|<@&(\d+)>', message.content)
            mention_count = len(raw_mentions)
            if message.mention_everyone: mention_count += 1
            
            # Ngưỡng trảm ngay lập tức trong 1 tin nhắn
            if mention_count >= config.get("max_mentions", 5):
                return await self.execute_punishment(message, "Spam Mention (Vượt ngưỡng tin nhắn)")

            # Kiểm tra tag rải rác (3 tin chứa tag trong vòng 5 giây)
            if mention_count > 0:
                self.mention_cache[gid][uid].append(now)
                self.mention_cache[gid][uid] = [t for t in self.mention_cache[gid][uid] if now - t < 5.0]
                if len(self.mention_cache[gid][uid]) >= 3:
                     return await self.execute_punishment(message, "Mention Flooding (Tag rải rác)")

        # 2. PHÁT HIỆN FLOOD TIN NHẮN
        if config.get("check_messages"):
            self.msg_cache[gid][uid].append(now)
            # Cửa sổ trượt 3 giây
            self.msg_cache[gid][uid] = [t for t in self.msg_cache[gid][uid] if now - t < 3.0]
            if len(self.msg_cache[gid][uid]) >= config.get("max_messages", 7):
                return await self.execute_punishment(message, "Message Flooding")

        # 3. PHÁT HIỆN SPAM LINK
        if config.get("check_links"):
            if re.search(r'https?://\S+|discord\.gg/\S+', message.content.lower()):
                self.link_cache[gid][uid].append(now)
                # Cửa sổ trượt 5 giây
                self.link_cache[gid][uid] = [t for t in self.link_cache[gid][uid] if now - t < 5.0]
                if len(self.link_cache[gid][uid]) >= config.get("max_links", 3):
                    return await self.execute_punishment(message, "Link Spam")

    async def execute_punishment(self, message, reason):
        """Hàm trảm: Thực thi Timeout + Purge + Logging"""
        member = message.author
        guild = message.guild
        config = self.config_cache.get(guild.id, DEFAULT_CONFIG)

        try:
            # --- KIỂM TRA QUYỀN HẠN (IT SECURITY CHECK) ---
            
            # 1. Admin Check: Discord API cấm timeout Admin (quản trị viên cấp cao)
            if member.guild_permissions.administrator:
                return await message.channel.send(
                    f"⚠️ **Cảnh báo:** Phát hiện {member.mention} vi phạm Antispam (`{reason}`), nhưng không thể trảm vì tài khoản này có quyền **Administrator** (Giới hạn Discord API)."
                )

            # 2. Hierarchy Check: Kiểm tra thứ bậc Role
            if member.top_role.position >= guild.me.top_role.position:
                return await message.channel.send(
                    f"❌ **Thất bại:** Không thể trảm {member.mention}.\nLý do: Role của đối tượng cao hơn hoặc ngang bằng Jin Bot."
                )

            # 3. THỰC THI TIMEOUT 28 NGÀY
            until = discord.utils.utcnow() + discord.utils.timedelta(seconds=MAX_TIMEOUT_SECONDS)
            await member.timeout(until, reason=f"Jin Anti-Spam: {reason}")

            # 4. DỌN DẸP TIN NHẮN (Purge)
            try:
                await message.channel.purge(limit=10, check=lambda m: m.author == member)
            except discord.Forbidden:
                await message.channel.send("📌 Đã timeout nhưng tớ không có quyền xóa tin nhắn của đối tượng.")

            # 5. GỬI EMBED SILENCE (Kênh hiện tại hoặc kênh Silence riêng)
            embed_silence = discord.Embed(
                title="🚫 HỆ THỐNG SILENCE",
                description=f"**Đối tượng:** {member.mention}\n**Hành vi:** {reason}\n**Hình phạt:** Timeout 28 ngày",
                color=COLOR_SILENCE
            )
            embed_silence.set_footer(text=f"ID: {member.id} | Hệ thống tự động")
            
            target_id = config.get("silence_channel")
            chan = guild.get_channel(target_id) if target_id else message.channel
            if chan: await chan.send(embed=embed_silence)

            # 6. GỬI AUDIT LOG (Nếu có setup)
            audit_id = config.get("audit_log_channel")
            if audit_id:
                audit_chan = guild.get_channel(audit_id)
                if audit_chan:
                    emb_audit = discord.Embed(title="🚨 AUDIT LOG VI PHẠM", color=COLOR_AUDIT)
                    emb_audit.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
                    emb_audit.add_field(name="Lý do", value=reason, inline=True)
                    emb_audit.add_field(name="Kênh", value=message.channel.mention, inline=True)
                    await audit_chan.send(embed=emb_audit)

        except discord.Forbidden:
            await message.channel.send(f"❌ Lỗi 403: Jin thiếu quyền **Moderate Members** để trảm {member.mention}.")
        except Exception as e:
            await message.channel.send(f"⚠️ Lỗi hệ thống: `{str(e)}`")

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
