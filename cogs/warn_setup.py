# cogs/warn_setup.py
import discord
from discord import app_commands
from discord.ext import commands
from utils.time_converter import parse_duration, format_seconds

class WarnLevelModal(discord.ui.Modal):
    def __init__(self, level_num, bot):
        super().__init__(title=f"Setup Warn Level {level_num}")
        self.level_num = level_num
        self.bot = bot

        # Các ô nhập liệu
        self.mode = discord.ui.TextInput(
            label="Punishment Mode",
            placeholder="mute / kick / ban / none",
            default="none",
            min_length=3, max_length=4
        )
        self.duration = discord.ui.TextInput(
            label="Punishment Duration (e.g: 30m, 1h, 1d)",
            placeholder="Chỉ áp dụng cho Mute. Nhập 'none' nếu là Kick/Ban",
            required=False
        )
        self.reset = discord.ui.TextInput(
            label="Reset Duration (Treo án - e.g: 2h, 1d)",
            placeholder="Thời gian để án phạt tự biến mất",
            required=True
        )
        self.strikes = discord.ui.TextInput(
            label="Strikes Required",
            placeholder="Số lần nhắc nhở trước khi phạt (e.g: 3)",
            default="1"
        )
        self.message = discord.ui.TextInput(
            label="Custom Message",
            style=discord.TextStyle.paragraph,
            placeholder="Dùng {user}, {level}, {reason}, {strikes_left}",
            default="{user} has been warned for {reason}. Strikes: {strikes_left} left.",
            required=False
        )

        # Thêm vào Modal
        self.add_item(self.mode)
        self.add_item(self.duration)
        self.add_item(self.reset)
        self.add_item(self.strikes)
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Kiểm tra Mode nhập vào
        valid_modes = ["mute", "kick", "ban", "none"]
        mode_val = self.mode.value.lower().strip()
        if mode_val not in valid_modes:
            return await interaction.response.send_message(f"❌ Sai Mode phạt! Chỉ được nhập: {', '.join(valid_modes)}", ephemeral=True)

        # 2. Convert thời gian an toàn
        punish_sec = parse_duration(self.duration.value)
        reset_sec = parse_duration(self.reset.value)
        
        # 3. Lưu vào MongoDB
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {f"warn_levels.{self.level_num}": {
                "mode": mode_val,
                "duration": punish_sec,
                "reset": reset_sec,
                "strikes": int(self.strikes.value if self.strikes.value.isdigit() else 1),
                "text": self.message.value
            }}},
            upsert=True
        )

        # 4. TƯ DUY MULTI-IT: Đồng bộ RAM nóng ngay lập tức để hệ thống nhận diện luật mới
        config_cog = self.bot.get_cog("antispam")
        if config_cog:
            await config_cog._update_system_cache(interaction.guild.id)

        await interaction.response.send_message(f"✅ Level {self.level_num} updated! Reset time: {format_seconds(reset_sec)}", ephemeral=True)

class WarnSetupView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

        # Tạo Dropdown chọn từ 1 đến 20
        options = [discord.SelectOption(label=f"Level {i}", value=str(i)) for i in range(1, 21)]
        
        # Bổ sung custom_id để Discord ghi nhớ View này vĩnh viễn xuyên suốt các lần restart bot
        self.select = discord.ui.Select(
            custom_id="jin_warn_setup_dropdown",
            placeholder="Choose a Warn Level to configure...", 
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        level_num = self.select.values[0]
        await interaction.response.send_modal(WarnLevelModal(level_num, self.bot))

class WarnSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="warn-setup", description="Configure the 20-level warn system")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_command(self, interaction: discord.Interaction):
        view = WarnSetupView(self.bot)
        embed = discord.Embed(
            title="Jin Discipline Configuration",
            description="Select a level from the dropdown below to set up its punishment, decay time, and custom messages.",
            color=0x010101
        )
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(WarnSetup(bot))
