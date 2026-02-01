from datetime import datetime
from app.core.config import OFFLINE_THRESHOLD_SECONDS

def calculate_device_status(device):
    now = datetime.now()
    seconds_ago = int((now - device.last_seen).total_seconds())

    is_online = seconds_ago <= OFFLINE_THRESHOLD_SECONDS
    computed_status = "Online" if is_online else "Offline"

    return {
        "device_id": device.device_id,
        "status": computed_status,
        "last_seen": device.last_seen,
        "last_seen_seconds_ago": seconds_ago,
        "is_online": is_online
    }
