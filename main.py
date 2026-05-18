# main.py
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
        
        # Tư duy IT: Khởi tạo sẵn thuộc tính để tránh AttributeError khi hệ thống chưa boot xong DB
        self.db_client = None
        self.db = None

    async def setup_hook(self):
        # 1. Kết nối MongoDB Async
        self.db_client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.db_client.Jin_Ultimate_Database
        
        # 2. Nạp các module hệ thống (Đã bổ sung cogs.warn_setup)
        exts = ['cogs.status', 'cogs.antispam', 'cogs.antispam_config', 'cogs.warn_setup']
        for ext in exts:
            try:
                await self.load_extension(ext)
                print(f"✅ Đã nạp: {ext}")
            except Exception as e:
                print(f"❌ Lỗi nạp {ext}: {e}")

        # 3. Đăng ký Persistent View cho hệ thống Warn (Giữ nút bấm sống vĩnh viễn sau khi restart)
        try:
            from cogs.warn_setup import WarnSetupView
            self.add_view(WarnSetupView(self))
            print("👁️ Đã đăng ký Persistent View cho Warn Setup thành công.")
        except Exception as e:
            print(f"⚠️ Lỗi đăng ký Persistent View: {e}")

    async def on_ready(self):
        print(f"🚀 {self.user.name} đã sẵn sàng trừng phạt.")
        await self.tree.sync()
        # Chạy task quét rác 5p/lần
        if not self.decay_cleaner.is_running():
            self.decay_cleaner.start()

    @tasks.loop(minutes=5.0)
    async def decay_cleaner(self):
        """Hệ thống tự động dọn dẹp Database (Tư duy IT tối ưu tài nguyên)"""
        if self.db is None: 
            return
            
        now = int(time.time())
        try:
            res = await self.db.discipline_records.delete_many({"reset_at": {"$lt": now, "$ne": 0}})
            if res.deleted_count > 0: 
                print(f"🧹 Đã xóa {res.deleted_count} án phạt hết hạn.")
        except Exception as e: 
            print(f"⚠️ Lỗi Cleaner: {e}")

# --- WEB SERVER KEEPALIVE CHO RENDER ---
async def handle(r): 
    return web.Response(text="Jin Anti-Spam is Live!")

async def main():
    bot = JinBot()
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 10000).start()
    
    try:
        async with bot: 
            await bot.start(TOKEN)
    finally:
        # Giải phóng Port an toàn khi bot restart/crash trên Render
        print("🛑 Đang đóng Web Server và giải phóng tài nguyên...")
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
