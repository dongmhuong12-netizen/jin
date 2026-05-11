# constants.py 
COLOR_GENERAL = 0x010101   
COLOR_SILENCE = 0x000000   
COLOR_AUDIT = 0x111111     

# Cấu hình mặc định - Tư duy IT: Luôn có phương án dự phòng (Fallback)
DEFAULT_CONFIG = {
    "active": True,
    "check_messages": True,
    "check_links": True,
    "check_mentions": True,
    "max_mentions": 5,
    "max_messages": 7,
    "max_links": 3
}
