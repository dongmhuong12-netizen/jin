WARN_RULES = {
    1: {"action": "warn"},
    2: {"action": "mute", "duration": 600},
    3: {"action": "kick"},
    4: {"action": "ban"}
}

def get_action(level):
    return WARN_RULES.get(level)
