# bot/audit/logger.py

import time
from audit.sink import write_log

class AuditLogger:

    def log(self, guild_id: int, event_type: str, data: dict):

        payload = {
            "timestamp": time.time(),
            "guild_id": guild_id,
            "type": event_type,
            "data": data
        }

        write_log(payload)
