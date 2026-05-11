# utils/moderator.py
import discord
import sys
import os

# Đảm bảo import được constants
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from constants import COLOR_SILENCE, COLOR_AUDIT
    from utils.time_converter import MAX_TIMEOUT_SECONDS
except ImportError:
    COLOR_SILENCE, COLOR_AUDIT, MAX_TIMEOUT_SECONDS = 0x000000, 0x111111, 2419200

async def execute_punishment(bot, message, reason):
    """
    Hàm trảm tập trung: Xử lý mọi hình phạt từ Antispam, Warn, v.v.
    """
    member = message.author
    guild = message.guild
    
    # Lấy config từ Cache của Cog AntiSpam (để biết kênh Silence/Audit)
    antispam_cog = bot.get_cog("AntiSpam")
    config = antispam_cog.config_cache.get(guild.id, {}) if antispam_cog else {}

    try:
        # 1. Kiểm tra quyền Administrator (Giới hạn cứng của Discord)
        if member.guild_permissions.administrator:
            return await message.channel.send(
                f"⚠️ **Antispam Detect:** Phát hiện {member.mention} vi phạm nhưng không thể trảm vì đối tượng là **Administrator**."
            )

        # 2. Kiểm tra Hierarchy (Thứ bậc Role)
        if member.top_role.position >= guild.me.top_role.position:
            return await message.channel.send(
                f"❌ **Antispam Error:** Role của {member.mention} (`pos:{member.top_role.position}`) cao hơn hoặc bằng Jin (`pos:{guild.me.top_role.position}`)."
            )

        # 3. Thực thi Timeout
        until = discord.utils.utcnow() + discord.utils.timedelta(seconds=MAX_TIMEOUT_SECONDS)
        await member.timeout(until, reason=f"Jin System: {reason}")

        # 4. Xóa tin nhắn (Purge)
        try:
            await message.channel.purge(limit=10, check=lambda m: m.author == member)
        except discord.Forbidden:
            await message.channel.send("📌 Đã timeout nhưng tớ thiếu quyền **Manage Messages** để dọn tin nhắn.")

        # 5. Gửi Embed Silence (Thông báo ra cộng đồng)
        embed_silence = discord.Embed(
            title="🚫 HỆ THỐNG TRỪNG PHẠT",
            description=f"**Đối tượng:** {member.mention}\n**Hành vi:** {reason}\n**Hình phạt:** Timeout 28 ngày",
            color=COLOR_SILENCE
        )
        target_id = config.get("silence_channel")
        chan = guild.get_channel(target_id) if target_id else message.channel
        if chan: await chan.send(embed=embed_silence)

        # 6. Gửi Audit Log (Cho Admin theo dõi)
        audit_id = config.get("audit_log_channel")
        if audit_id:
            audit_chan = guild.get_channel(audit_id)
            if audit_chan:
                emb_audit = discord.Embed(title="🚨 AUDIT LOG", color=COLOR_AUDIT)
                emb_audit.add_field(name="Người vi phạm", value=f"{member} ({member.id})", inline=False)
                emb_audit.add_field(name="Lý do", value=reason, inline=True)
                emb_audit.add_field(name="Kênh", value=message.channel.mention, inline=True)
                await audit_chan.send(embed=emb_audit)

    except discord.Forbidden:
        await message.channel.send(f"❌ Lỗi 403: Bot thiếu quyền **Moderate Members** để xử lý {member.name}.")
    except Exception as e:
        await message.channel.send(f"⚠️ Lỗi thực thi trảm: `{str(e)}`")
