# cogs/antispam.py
import discord
from discord.ext import commands
import time
import re
import asyncio
from collections import defaultdict

from constants import DEFAULT_CONFIG
from utils.moderator import execute_punishment 

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Các bộ đếm tần suất gửi tin nhắn
        self.msg_cache = defaultdict(lambda: defaultdict(list))
        self.link_cache = defaultdict(lambda: defaultdict(list))
        self.mention_cache = defaultdict(lambda: defaultdict(list))
        
        # Bộ nhớ Cache cấu hình động cho từng Guild (Giải pháp tối ưu Multi-IT)
        self.config_cache = {} 
        
        # Bộ khóa chống nghẽn trùng lặp hình phạt (Giải quyết Race Condition)
        self.processing_users = set()

    async def get_guild_config(self, guild_id: int) -> dict:
        """Cơ chế Lazy Loading: Chỉ đọc DB khi cần thiết, không cào bừa bãi toàn bộ hệ thống"""
        if guild_id in self.config_cache:
            return self.config_cache[guild_id]
            
        try:
            doc = await self.bot.db.server_settings.find_one({"guild_id": guild_id})
            self.config_cache[guild_id] = {**DEFAULT_CONFIG, **(doc or {})}
        except Exception as e:
            print(f"⚠️ Thất bại khi đọc DB cấu hình cho Guild {guild_id}: {e}")
            self.config_cache[guild_id] = DEFAULT_CONFIG.copy()
            
        return self.config_cache[guild_id]

    def is_whitelisted(self, message, config):
        if message.author.id == message.guild.owner_id: return True
        if message.author.id in config.get("whitelist_users", []): return True
        if any(role.id in config.get("whitelist_roles", []) for role in message.author.roles): return True
        return False

    async def _trigger_punishment(self, message, reason, config):
        """Hàm phụ trợ: Kích hoạt trảm có khóa bảo vệ an toàn"""
        uid = message.author.id
        self.processing_users.add(uid)
        try:
            await execute_punishment(self.bot, message, reason, config)
        finally:
            # Giữ khóa thêm 2 giây để nuốt sạch các tin rác còn đang bay trên đường truyền mạng
            await asyncio.sleep(2.0)
            self.processing_users.discard(uid)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot: return
        
        gid, uid, now = message.guild.id, message.author.id, time.time()
        
        # Nếu Spammer đang bị xử lý trảm ở một luồng song song, nuốt chửng tin nhắn mới
        if uid in self.processing_users: return
        
        config = await self.get_guild_config(gid)
        if not config.get("active") or self.is_whitelisted(message, config): return

        # --- TUYẾN PHÒNG THỦ 1: CHỐNG SPAM MENTION (TAG) ---
        if config.get("check_mentions"):
            raw_tags = re.findall(r'<@!?\d+>|<@&\d+>', message.content)
            count = len(raw_tags) + (1 if message.mention_everyone else 0)
            
            if count >= config.get("max_mentions", 5):
                return await self._trigger_punishment(message, "Spam Mention", config)
            
            if count > 0:
                self.mention_cache[gid][uid].append(now)
                self.mention_cache[gid][uid] = [t for t in self.mention_cache[gid][uid] if now - t < 5.0]
                if len(self.mention_cache[gid][uid]) >= 3:
                     return await self._trigger_punishment(message, "Mention Flooding", config)
                # Fix rò rỉ RAM: Xóa Key nếu List trống
                if not self.mention_cache[gid][uid]: del self.mention_cache[gid][uid]

        # --- TUYẾN PHÒNG THỦ 2: CHỐNG FLOOD TIN NHẮN ---
        if config.get("check_messages"):
            self.msg_cache[gid][uid].append(now)
            self.msg_cache[gid][uid] = [t for t in self.msg_cache[gid][uid] if now - t < 3.0]
            
            if len(self.msg_cache[gid][uid]) >= config.get("max_messages", 7):
                return await self._trigger_punishment(message, "Message Flooding", config)
            
            # Fix rò rỉ RAM
            if not self.msg_cache[gid][uid]: del self.msg_cache[gid][uid]

        # --- TUYẾN PHÒNG THỦ 3: CHỐNG SPAM LINK ---
        if config.get("check_links"):
            if re.search(r'https?://\S+|discord\.gg/\S+', message.content.lower()):
                self.link_cache[gid][uid].append(now)
                self.link_cache[gid][uid] = [t for t in self.link_cache[gid][uid] if now - t < 5.0]
                
                if len(self.link_cache[gid][uid]) >= config.get("max_links", 3):
                    return await self._trigger_punishment(message, "Link Spam", config)
                
                # Fix rò rỉ RAM
                if not self.link_cache[gid][uid]: del self.link_cache[gid][uid]

        # Dọn dẹp Guild rỗng khỏi RAM định kỳ khi chat trôi qua
        if gid in self.mention_cache and not self.mention_cache[gid]: del self.mention_cache[gid]
        if gid in self.msg_cache and not self.msg_cache[gid]: del self.msg_cache[gid]
        if gid in self.link_cache and not self.link_cache[gid]: del self.link_cache[gid]

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
