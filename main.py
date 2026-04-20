import os
import time
import sys
from core.bot import create_bot

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("Missing TOKEN")

# 🔥 DEPLOY CHECK MARKER
print("DEPLOY VERSION: 2026-04-20-ANTI_LOOP_FIX")

def run_bot():
    bot = create_bot()

    try:
        bot.run(TOKEN)

    except Exception as e:
        print("BOT CRASHED:", repr(e))

        # 🔥 CRITICAL FIX: chống login loop
        time.sleep(30)

        # exit để Render restart nhưng có delay
        sys.exit(1)

if __name__ == "__main__":
    run_bot()
