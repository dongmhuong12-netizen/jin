import discord
from discord.ext import commands
import os
import sys

# ===== LOAD TOKEN =====
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("ERROR: TOKEN is missing or not loaded")
    sys.exit(1)

# ===== INTENTS =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== READY =====
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Bot is ready.")

# ===== TEST COMMAND =====
@bot.command()
async def ping(ctx):
    await ctx.send("pong")

# ===== WARN SYSTEM (BASE) =====
warn_data = {}

def get_user_warns(guild_id, user_id):
    return warn_data.get(guild_id, {}).get(user_id, [])

def add_warn(guild_id, user_id, reason):
    warn_data.setdefault(guild_id, {}).setdefault(user_id, []).append(reason)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    add_warn(ctx.guild.id, member.id, reason)
    warns = get_user_warns(ctx.guild.id, member.id)

    await ctx.send(
        f"{member.mention} đã bị warn.\n"
        f"Lý do: {reason}\n"
        f"Tổng warn: {len(warns)}"
    )

@bot.command()
async def warns(ctx, member: discord.Member):
    warns = get_user_warns(ctx.guild.id, member.id)

    if not warns:
        await ctx.send("User chưa có warn nào.")
        return

    msg = "\n".join([f"{i+1}. {w}" for i, w in enumerate(warns)])
    await ctx.send(f"Warn của {member}:\n{msg}")

# ===== RUN BOT (DEBUG SAFE) =====
try:
    bot.run(TOKEN)
except Exception as e:
    print(f"BOT CRASHED: {e}")
    raise e
