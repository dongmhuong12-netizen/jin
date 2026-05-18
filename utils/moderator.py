# utils/moderator.py
import discord
from constants import COLOR_SILENCE, COLOR_AUDIT
from utils.time_converter import parse_duration, format_seconds

async def execute_punishment(bot, message, reason, config: dict):
    """
    Hàm trảm tập trung: Xử lý mọi hình phạt từ Antispam, Warn, v.v.
    Đã được nâng cấp chuẩn Multi-IT: Độc lập, không phụ thuộc chéo, xử lý thời gian động.
    """
    member = message.author
    guild = message.guild

    try:
        # 1. Kiểm tra quyền Administrator (Giới hạn cứng của Discord)
        if member.guild_permissions.administrator:
            try:
                return await message.channel.send(
                    f"⚠️ **Antispam Detect:** Phát hiện {member.mention} vi phạm nhưng không thể trảm vì đối tượng là **Administrator**.",
                    delete_after=10
                )
            except discord.Forbidden:
                return # Tránh crash nếu bot bị tước quyền nhắn tin

        # 2. Kiểm tra Hierarchy (Thứ bậc Role)
        if member.top_role.position >= guild.me.top_role.position:
            try:
                return await message.channel.send(
                    f"❌ **Antispam Error:** Role của {member.mention} (`pos:{member.top_role.position}`) cao hơn hoặc bằng Jin (`pos:{guild.me.top_role.position}`).",
                    delete_after=10
                )
            except discord.Forbidden:
                return

        # 3. Thực thi Timeout động từ Cấu hình Server (Fallback 10 phút)
        duration_str = config.get("punishment_duration", "10m")
        seconds = parse_duration(duration_str)
        if seconds <= 0: 
            seconds = 600 

        until = discord.utils.utcnow() + discord.utils.timedelta(seconds=seconds)
        await member.timeout(until, reason=f"Jin System: {reason}")

        # 4. Xóa tin nhắn (Purge)
        try:
            await message.channel.purge(limit=10, check=lambda m: m.author == member)
        except discord.Forbidden:
            pass # Lỗi vặt thiếu quyền xóa tin thì bỏ qua để chạy tiếp mạch thông báo

        # 5. Gửi Embed Silence (Thông báo ra cộng đồng)
        formatted_time = format_seconds(seconds)
        embed_silence = discord.Embed(
            title="🚫 HỆ THỐNG TRỪNG PHẠT",
            description=f"**Đối tượng:** {member.mention}\n**Hành vi:** {reason}\n**Hình phạt:** Timeout {formatted_time}",
            color=COLOR_SILENCE
        )
        target_id = config.get("silence_channel")
        chan = guild.get_channel(target_id) if target_id else message.channel
        if chan: 
            try:
                await chan.send(embed=embed_silence)
            except discord.Forbidden:
                pass

        # 6. Gửi Audit Log (Cho Admin theo dõi)
        audit_id = config.get("audit_log_channel")
        if audit_id:
            audit_chan = guild.get_channel(audit_id)
            if audit_chan:
                emb_audit = discord.Embed(title="🚨 AUDIT LOG", color=COLOR_AUDIT)
                emb_audit.add_field(name="Người vi phạm", value=f"{member} ({member.id})", inline=False)
                emb_audit.add_field(name="Lý do", value=reason, inline=True)
                emb_audit.add_field(name="Thời gian", value=formatted_time, inline=True)
                emb_audit.add_field(name="Kênh", value=message.channel.mention, inline=False)
                try:
                    await audit_chan.send(embed=emb_audit)
                except discord.Forbidden:
                    pass

    except discord.Forbidden:
        try:
            await message.channel.send(f"❌ Lỗi 403: Bot thiếu quyền **Moderate Members** để xử lý {member.name}.")
        except discord.Forbidden:
            pass
    except Exception as e:
        print(f"⚠️ Lỗi thực thi trảm tại execute_punishment: {e}")
