from pydantic import BaseModel, Field
from datetime import datetime

class StatusUpdateRequest(BaseModel):
    device_id: str = Field(default="ESP32_MAIN", description="Unique device identifier")
    status: str = Field(..., description="Device status (Online/Offline)")

class StatusResponse(BaseModel):
    success: bool
    message: str
    device_id: str
    status: str
    last_seen: datetime
    last_seen_seconds_ago: int
    is_online: bool
    
    class Config:
        from_attributes = True
        
class DeviceStatusInfo(BaseModel):
    device_id: str
    status: str
    last_seen: datetime
    last_seen_seconds_ago: int
    is_online: bool
    
    class Config:
        orm_mode = True