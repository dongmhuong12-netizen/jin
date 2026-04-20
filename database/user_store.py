import json
import os

def file_path(guild_id, user_id):
    return f"data/guilds/{guild_id}_{user_id}.json"

def get_user(guild_id, user_id):

    path = file_path(guild_id, user_id)

    if not os.path.exists(path):
        return {"level": 0}

    try:
        with open(path, "r") as f:
            return json.load(f)

    except:
        return {"level": 0}

def save_user(guild_id, user_id, data):

    path = file_path(guild_id, user_id)

    os.makedirs("data/guilds", exist_ok=True)

    with open(path, "w") as f:
        json.dump(data, f)
