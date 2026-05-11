import re

def parse_duration(duration_str: str) -> int:
    """Chuyển đổi các chuỗi như '1d 2h 30m' thành tổng số giây."""
    if not duration_str or duration_str.lower() == "none": 
        return 0
    
    units = {
        'd': 86400,
        'h': 3600,
        'm': 60,
        's': 1
    }
    
    total_seconds = 0
    # Tìm các cụm số + đơn vị
    matches = re.findall(r'(\d+)([dhms])', duration_str.lower().replace(" ", ""))
    
    for value, unit in matches:
        total_seconds += int(value) * units[unit]
        
    return total_seconds

def format_seconds(seconds: int) -> str:
    """Ngược lại, biến giây thành chuỗi dễ đọc để log ra cho Admin."""
    if seconds == 0: return "None"
    
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    
    parts = []
    if d > 0: parts.append(f"{d}d")
    if h > 0: parts.append(f"{h}h")
    if m > 0: parts.append(f"{m}m")
    if s > 0: parts.append(f"{s}s")
    
    return " ".join(parts)
