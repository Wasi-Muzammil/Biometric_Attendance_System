from datetime import datetime
from app.core.config import OFFLINE_THRESHOLD_SECONDS

def calculate_device_status(device):
    now = datetime.now()
    diff = int((now - device.last_seen).total_seconds())

    is_online = diff < OFFLINE_THRESHOLD_SECONDS and device.status.lower() == "online"

    return {
        "device_id": device.device_id,
        "status": "Online" if is_online else "Offline",
        "last_seen": device.last_seen,
        "last_seen_seconds_ago": diff,
        "is_online": is_online
    }
