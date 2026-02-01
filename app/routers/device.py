from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.models.device import DeviceStatusDB
from app.schemas.device import (
    StatusUpdateRequest,
    StatusResponse,
    DeviceStatusInfo
)
from app.utils.device_status import calculate_device_status
from app.core.config import OFFLINE_THRESHOLD_SECONDS

router = APIRouter(prefix="/esp32", tags=["Device"])


@router.post("/esp32/status", response_model=StatusResponse)
def update_device_status(
    data: StatusUpdateRequest,
    db: Session = Depends(get_db)
):
    try:
        current_time = datetime.now()

        device = db.query(DeviceStatusDB).filter_by(
            device_id=data.device_id
        ).first()

        if device:
            device.last_seen = current_time
            device.status = "Online"  # optional, cosmetic
            device.updated_at = current_time
        else:
            device = DeviceStatusDB(
                device_id=data.device_id,
                status="Online",
                last_seen=current_time,
            )
            db.add(device)

        db.commit()
        db.refresh(device)

        return StatusResponse(
            success=True,
            message="Heartbeat received",
            device_id=device.device_id,
            status="Online",
            last_seen=device.last_seen,
            last_seen_seconds_ago=0,
            is_online=True
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/esp32/status/{device_id}", response_model=DeviceStatusInfo)
def get_device_status(
    device_id: str,
    db: Session = Depends(get_db)
):
    device = db.query(DeviceStatusDB).filter_by(
        device_id=device_id
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    status_info = calculate_device_status(device)

    # OPTIONAL: sync DB if stale
    if device.status != status_info["status"]:
        device.status = status_info["status"]
        db.commit()

    return DeviceStatusInfo(**status_info)


@router.get("/esp32/status")
def get_all_devices_status(db: Session = Depends(get_db)):
    devices = db.query(DeviceStatusDB).order_by(
        DeviceStatusDB.last_seen.desc()
    ).all()

    device_list = []
    online_count = 0

    for device in devices:
        status_info = calculate_device_status(device)

        # Optional DB sync
        if device.status != status_info["status"]:
            device.status = status_info["status"]

        if status_info["is_online"]:
            online_count += 1

        device_list.append(status_info)

    db.commit()

    return {
        "total_devices": len(device_list),
        "online_devices": online_count,
        "offline_devices": len(device_list) - online_count,
        "devices": device_list
    }
