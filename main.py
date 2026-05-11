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
        # Thiết lập Intents chuẩn cho hệ thống quản trị
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!", 
            intents=intents, 
            help_command=None
        )
        
        # Khởi tạo kết nối MongoDB (Trí nhớ của bot)
        self.db_client = None
        self.db = None

    async def setup_hook(self):
        """Hàm chạy trước khi bot login: Dùng để kết nối DB và nạp module"""
        print("🛠️ Đang khởi tạo kết nối MongoDB...")
        self.db_client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.db_client.jin_database # Tên database trên Atlas
        print("✅ MongoDB Connected!")

    async def on_ready(self):
        print(f"🚀 {self.user.name} Đã Online (ID: {self.user.id})")
        print(f"🌐 Đang chạy trên quy mô Multi-server")

# --- WEB SERVER (Dành riêng cho Render) ---
async def handle(request):
    return web.Response(text="Bot jin is Online!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    # Render yêu cầu port 10000
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    print("📡 Web Server Keep-alive is Running on Port 10000")

# --- KHỞI CHẠY HỆ THỐNG ---
async def main():
    bot = JinBot()
    async with bot:
        # Chạy song song Web Server và Discord Bot (Asyncio Task)
        await asyncio.gather(
            start_web_server(),
            bot.start(TOKEN)
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
