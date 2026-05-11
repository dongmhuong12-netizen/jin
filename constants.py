DEFAULT_CONFIG = {
    "active": True,
    "check_messages": True,
    "check_links": True,
    "check_mentions": True,
    
    # Ngưỡng mặc định nếu DB chưa có
    "max_mentions": 5,      # Quá 5 tags là vả
    "max_messages": 7,      # Quá 7 tin nhắn/5s là vả
    "max_links": 3,         # Quá 3 links là vả
    "timeout_duration": 2419200 # 28 ngày tính bằng giây
}
