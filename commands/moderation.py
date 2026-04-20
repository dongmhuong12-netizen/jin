async def unmute(member):
    await member.edit(timed_out_until=None)

async def kick(member):
    await member.kick()

async def ban(member):
    await member.ban()
