import os
import asyncio
import discord
from discord.ext import commands
from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient

# --- BIẾN MÔI TRƯỜNG ---
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

class JinBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!", 
            intents=intents, 
            help_command=None
        )

    async def setup_hook(self):
        """Chạy trước khi login: Kết nối DB, nạp Cogs và Sync lệnh"""
        # 1. Kết nối MongoDB
        print("🛠️ Đang khởi tạo kết nối MongoDB...")
        self.db_client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.db_client.Jin_Ultimate_Database # Tên DB khớp với constants
        print("✅ MongoDB Connected!")

        # 2. Nạp Cogs tự động (Tìm trong thư mục cogs)
        # Lưu ý: Cậu phải có thư mục tên 'cogs' và file 'status.py' trong đó
        try:
            await self.load_extension("cogs.status")
            print("📦 Đã nạp module: status.py")
        except Exception as e:
            print(f"❌ Không thể nạp module: {e}")

    async def on_ready(self):
        print(f"🚀 {self.user.name} Đã Online (ID: {self.user.id})")
        
        # 3. ĐỒNG BỘ LỆNH SLASH (QUAN TRỌNG NHẤT)
        try:
            print("🔄 Đang đồng bộ Slash Commands...")
            synced = await self.tree.sync()
            print(f"✅ Đã đồng bộ {len(synced)} lệnh thành công!")
        except Exception as e:
            print(f"❌ Lỗi đồng bộ lệnh: {e}")
        
        print(f"🌐 Đang chạy trên quy mô Multi-server")

# --- WEB SERVER (Dành riêng cho Render) ---
async def handle(request):
    return web.Response(text="Bot jin is Online!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    print("📡 Web Server (Port 10000) - Ready!")

# --- KHỞI CHẠY HỆ THỐNG ---
async def main():
    bot = JinBot()
    # Chạy Web Server trước, sau đó mới chạy Bot
    async with bot:
        await asyncio.gather(
            start_web_server(),
            bot.start(TOKEN)
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
