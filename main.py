import os
import asyncio
import discord
from discord.ext import commands, tasks
from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient
import time

TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

class JinBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        # Kết nối MongoDB
        self.db_client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.db_client.Jin_Ultimate_Database
        
        # Nạp Cogs
        extensions = ['cogs.status', 'cogs.warn_setup']
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"✅ Loaded {ext}")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")

    async def on_ready(self):
        print(f"🚀 {self.user.name} is Online")
        await self.tree.sync()
        # Bắt đầu vòng lặp quét ngầm
        if not self.decay_cleaner.is_running():
            self.decay_cleaner.start()

    @tasks.loop(minutes=5.0)
    async def decay_cleaner(self):
        """Hệ thống tự động dọn dẹp án phạt hết hạn (5 phút/lần)"""
        current_time = int(time.time())
        try:
            # Xóa tất cả record có reset_at nhỏ hơn thời gian hiện tại
            result = await self.db.discipline_records.delete_many({
                "reset_at": {"$lt": current_time, "$ne": 0}
            })
            if result.deleted_count > 0:
                print(f"🧹 Cleaned up {result.deleted_count} expired warn records.")
        except Exception as e:
            print(f"⚠️ Decay Cleaner Error: {e}")

# --- WEB SERVER & STARTUP ---
async def handle(request): return web.Response(text="Jin is Live!")

async def main():
    bot = JinBot()
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 10000).start()
    
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
