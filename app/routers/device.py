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

router = APIRouter(prefix="/esp32", tags=["Device"])


@router.post("/esp32/status", response_model=StatusResponse)
def update_device_status(
    data: StatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    POST endpoint for ESP32 to send heartbeat/status updates
    ESP32 calls this every 30 seconds to maintain "Online" status
    """
    try:
        # Check if device already exists
        device = db.query(DeviceStatusDB).filter_by(
            device_id=data.device_id
        ).first()
        
        current_time = datetime.now()
        
        if device:
            # Update existing device
            device.status = data.status
            device.last_seen = current_time
            device.updated_at = current_time
        else:
            # Create new device entry
            device = DeviceStatusDB(
                device_id=data.device_id,
                status=data.status,
                last_seen=current_time,
            )
            db.add(device)
        
        db.commit()
        db.refresh(device)
        
        return StatusResponse(
            success=True,
            message="Status updated successfully",
            device_id=device.device_id,
            status=device.status,
            last_seen=device.last_seen,
            last_seen_seconds_ago=0,
            is_online=True
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/esp32/status/{device_id}", response_model=DeviceStatusInfo)
def get_device_status(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    GET endpoint to retrieve current status of a specific ESP32 device
    Frontend uses this to display device status in real-time
    """
    device = db.query(DeviceStatusDB).filter_by(
        device_id=device_id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=404,
            detail=f"Device '{device_id}' not found"
        )
    
    # Calculate current status
    status_info = calculate_device_status(device)
    
    return DeviceStatusInfo(**status_info)

@router.get("/esp32/status")
def get_all_devices_status(db: Session = Depends(get_db)):
    """
    GET endpoint to retrieve status of all registered ESP32 devices
    Useful for monitoring multiple devices
    """
    devices = db.query(DeviceStatusDB).order_by(
        DeviceStatusDB.last_seen.desc()
    ).all()
    
    device_list = []
    for device in devices:
        status_info = calculate_device_status(device)
        device_list.append(status_info)
    
    online_count = sum(1 for d in device_list if d['is_online'])
    offline_count = len(device_list) - online_count
    
    return {
        "total_devices": len(device_list),
        "online_devices": online_count,
        "offline_devices": offline_count,
        "devices": device_list
    }