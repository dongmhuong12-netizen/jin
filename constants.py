# constants.py 
COLOR_GENERAL = 0x010101   
COLOR_SILENCE = 0x000000   
COLOR_AUDIT = 0x111111     

# Cấu hình mặc định - Tư duy IT: Luôn có phương án dự phòng (Fallback)
# Bổ sung các trường dữ liệu an toàn cho hệ thống Warn, Channel và Whitelist chuẩn Multi-Guild
DEFAULT_CONFIG = {
    "active": True,
    "check_messages": True,
    "check_links": True,
    "check_mentions": True,
    "max_mentions": 5,
    "max_messages": 7,
    "max_links": 3,
    "punishment_duration": "28d", # Thời gian chịu phạt dự phòng nếu Admin chưa thiết lập
    "silence_channel": None,      # Fallback trống cho kênh thông báo cộng đồng
    "audit_log_channel": None,    # Fallback trống cho kênh lưu log Admin
    "whitelist_users": [],        # Chống lỗi KeyError khi module Whitelist quét RAM
    "whitelist_roles": [],        # Chống lỗi KeyError khi module Whitelist quét RAM
    "warn_levels": {}             # Khung chứa an toàn cho bộ 20 Level Warn
}
