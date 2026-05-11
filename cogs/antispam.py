# cogs/antispam.py
import discord
from discord.ext import commands, tasks
import time
import re
from collections import defaultdict
import sys
import os

# --- TƯ DUY IT: FIX LỖI IMPORT ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from constants import DEFAULT_CONFIG
# Tách logic: Nhập khẩu hàm trảm từ file utils sắp tạo
from utils.moderator import execute_punishment 

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.msg_cache = defaultdict(lambda: defaultdict(list))
        self.link_cache = defaultdict(lambda: defaultdict(list))
        self.mention_cache = defaultdict(lambda: defaultdict(list))
        self.config_cache = {} 
        self.update_cache.start()

    @tasks.loop(minutes=2.0)
    async def update_cache(self):
        try:
            async for doc in self.bot.db.server_settings.find():
                gid = doc.get("guild_id")
                if gid: self.config_cache[gid] = {**DEFAULT_CONFIG, **doc}
        except: pass

    def is_whitelisted(self, message, config):
        if message.author.id == message.guild.owner_id: return True
        if message.author.id in config.get("whitelist_users", []): return True
        if any(role.id in config.get("whitelist_roles", []) for role in message.author.roles): return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot: return
        gid, uid, now = message.guild.id, message.author.id, time.time()
        config = self.config_cache.get(gid, DEFAULT_CONFIG)

        if not config.get("active") or self.is_whitelisted(message, config): return

        # --- CHỈ GIỮ LẠI LOGIC PHÁT HIỆN (DETECTION) ---
        if config.get("check_mentions"):
            raw_tags = re.findall(r'<@!?\d+>|<@&\d+>', message.content)
            count = len(raw_tags) + (1 if message.mention_everyone else 0)
            if count >= config.get("max_mentions", 5):
                return await execute_punishment(self.bot, message, "Spam Mention")
            if count > 0:
                self.mention_cache[gid][uid].append(now)
                self.mention_cache[gid][uid] = [t for t in self.mention_cache[gid][uid] if now - t < 5.0]
                if len(self.mention_cache[gid][uid]) >= 3:
                     return await execute_punishment(self.bot, message, "Mention Flooding")

        if config.get("check_messages"):
            self.msg_cache[gid][uid].append(now)
            self.msg_cache[gid][uid] = [t for t in self.msg_cache[gid][uid] if now - t < 3.0]
            if len(self.msg_cache[gid][uid]) >= config.get("max_messages", 7):
                return await execute_punishment(self.bot, message, "Message Flooding")

        if config.get("check_links"):
            if re.search(r'https?://\S+|discord\.gg/\S+', message.content.lower()):
                self.link_cache[gid][uid].append(now)
                self.link_cache[gid][uid] = [t for t in self.link_cache[gid][uid] if now - t < 5.0]
                if len(self.link_cache[gid][uid]) >= config.get("max_links", 3):
                    return await execute_punishment(self.bot, message, "Link Spam")

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))
