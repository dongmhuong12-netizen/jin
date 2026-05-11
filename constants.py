# constants.py - TRẠM QUẢN LÝ HẰNG SỐ CỦA JIN

# --- MÀU SẮC (DARK THEME) ---
# Mã 0x010101 là đen tuyền nhưng đảm bảo hiển thị đúng trên Discord
COLOR_GENERAL = 0x010101  # Đen chủ đạo cho UI/Jin
COLOR_LV1 = 0x444444      # Xám đậm
COLOR_LV2 = 0x2a2a2a      # Xám tối
COLOR_LV3 = 0x151515      # Đen mờ
COLOR_LV4 = 0x000000      # Đen tuyệt đối (Anti-spam/Ban)

# --- THÔNG SỐ DATABASE ---
DB_NAME = "Jin_Ultimate_Database"
COLL_RECORDS = "discipline_records"
COLL_CONFIGS = "server_settings"
COLL_WHITELIST = "exception_list"

# --- THỜI GIAN RESET (DECAY) - Giây ---
DECAY_L1 = 20 * 60  # 20 phút
DECAY_L2 = 30 * 60  # 30 phút
DECAY_L3 = 40 * 60  # 40 phút
