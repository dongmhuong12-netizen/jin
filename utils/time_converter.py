import re

# Constant giới hạn của Discord (28 ngày)
MAX_TIMEOUT_SECONDS = 2419200 

def parse_duration(duration_str: str) -> int:
    """Chuyển đổi chuỗi thời gian thành giây, tối đa 28 ngày."""
    if not duration_str or duration_str.lower() == "none": 
        return 0
    
    units = {
        'w': 604800, # Thêm tuần cho linh hoạt
        'd': 86400,
        'h': 3600,
        'm': 60,
        's': 1
    }
    
    total_seconds = 0
    # Cải tiến Regex để bắt được cả số thập phân (ví dụ: 1.5h)
    matches = re.findall(r'([\d.]+)([wdhms])', duration_str.lower().strip())
    
    for value, unit in matches:
        try:
            total_seconds += int(float(value) * units[unit])
        except ValueError:
            continue # Bỏ qua nếu giá trị không hợp lệ
            
    # Tư duy IT: Không bao giờ tin tưởng Input của User. 
    # Luôn giới hạn trong khoảng Discord cho phép.
    return min(total_seconds, MAX_TIMEOUT_SECONDS)

def format_seconds(seconds: int) -> str:
    """Biến giây thành chuỗi dễ đọc."""
    if seconds <= 0: return "None"
    if seconds >= MAX_TIMEOUT_SECONDS: return "28d (Max)"
    
    # Logic cũ của cậu rất ổn, giữ nguyên hoặc dùng f-string gọn hơn
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    
    parts = []
    if d > 0: parts.append(f"{d}d")
    if h > 0: parts.append(f"{h}h")
    if m > 0: parts.append(f"{m}m")
    if s > 0: parts.append(f"{s}s")
    
    return " ".join(parts) if parts else "0s"
