import discord
import asyncio
from core.event_pipeline.preprocessor import preprocess
from core.event_pipeline.router import route_event

intents = discord.Intents.all()

class Bot(discord.Client):

    def __init__(self):
        super().__init__(intents=intents)
        self._ready = False

    async def on_ready(self):
        if self._ready:
            return

        self._ready = True
        print(f"BOT ONLINE: {self.user}")

    async def on_message(self, message):

        if message.author.bot:
            return

        try:
            event = preprocess(message)
            await route_event(event, self)

        except Exception as e:
            print("EVENT ERROR:", repr(e))


def create_bot():
    return Bot()
