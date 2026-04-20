from plugins.antispam.handler import handle_antispam
from plugins.warn.handler import handle_warn

async def route_event(event, bot):

    # 1. ANTI-SPAM PRIORITY HIGHEST
    spam_blocked = await handle_antispam(event, bot)

    if spam_blocked:
        return

    # 2. WARN SYSTEM
    await handle_warn(event, bot)
