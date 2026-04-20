import time

user_decay = {}

def add_decay(user_id: int, seconds: int):
    user_decay[user_id] = time.time() + seconds

def is_expired(user_id: int):
    if user_id not in user_decay:
        return True
    return time.time() > user_decay[user_id]
