import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Bot is ready.")

# test command
@bot.command()
async def ping(ctx):
    await ctx.send("pong")

# ===== WARN SYSTEM (BASE STRUCTURE) =====

warn_data = {}  # sau này thay bằng database

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
        return await ctx.send("User chưa có warn nào.")

    msg = "\n".join([f"{i+1}. {w}" for i, w in enumerate(warns)])
    await ctx.send(f"Warn của {member}:\n{msg}")

bot.run(TOKEN)
