# plugins/punishment/kick.py

async def kick_user(member, reason=None):

    try:
        await member.kick(reason=reason or "No reason provided")
    except Exception as e:
        print("KICK ERROR:", repr(e))
