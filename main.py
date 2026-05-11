import os
import asyncio
import discord
from discord.ext import commands
from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient

# CONFIG
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

class JinBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        
        # Kết nối Database dùng chung cho toàn bộ Cogs
        self.db_client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.db_client.jin_database

    async def setup_hook(self):
        # Tự động load file warns.py từ thư mục cogs
        await self.load_extension("cogs.warns")
        print("✔ Module Warns: Loaded")

    async def on_ready(self):
        print(f"--- {self.user} IS ONLINE ---")

# KEEP ALIVE (Render)
async def handle(request):
    return web.Response(text="Jin is awake")

async def start_web():
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

async def main():
    bot = JinBot()
    async with bot:
        await asyncio.gather(
            start_web(),
            bot.start(TOKEN)
        )

if __name__ == "__main__":
    asyncio.run(main())
