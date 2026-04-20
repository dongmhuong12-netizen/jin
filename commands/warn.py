from plugins.warn.manager import add_warn
from engine.rule_engine import get_action
from engine.action_resolver import execute_action

async def warn_user(event):

    user_data = add_warn(event)

    level = user_data["level"]

    action = get_action(level)

    if action:
        await execute_action(action, event)
