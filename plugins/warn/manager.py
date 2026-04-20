from database.user_store import get_user, save_user

def add_warn(event):

    user = get_user(event["guild_id"], event["user_id"])

    user["level"] = user.get("level", 0) + 1

    save_user(event["guild_id"], event["user_id"], user)

    return user
