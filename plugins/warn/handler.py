from engine.rule_engine import get_action
from engine.action_resolver import execute_action
from plugins.warn.manager import add_warn

async def handle_warn(event, bot):

    user_data = add_warn(event)

    level = user_data["level"]

    action = get_action(level)

    if action:
        await execute_action(action, event)
