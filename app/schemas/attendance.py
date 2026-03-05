from pydantic import BaseModel,Field
from typing import List, Optional
from datetime import datetime

class AttendanceLogRequest(BaseModel):
    name: str = Field(..., description="User's full name")
    id: int = Field(..., description="User ID")
    slot_id: Optional[List[int]] = Field(None, description="Fingerprint slot IDs (optional)")
    date: str = Field(..., description="Date (DD/MM format)")
    time: str = Field(..., description="Time (HH:MM format)")

class AttendanceLogResponse(BaseModel):
    success: bool
    message: str
    action: str  # "checked_in", "checked_out", or "updated_checkout"
    attendance_record: Optional[dict] = None

class AttendanceBulkRequest(BaseModel):
    logs: List[AttendanceLogRequest]

# ==================== TRIGGER SYNC SCHEMAS ====================
class TriggerAttendanceSyncRequest(BaseModel):
    device_id: str = Field(default="ESP32_MAIN", description="Device to trigger sync on")
    days: int = Field(default=7, ge=1, le=30, description="Number of days to sync (1-30)")

class TriggerAttendanceSyncResponse(BaseModel):
    success: bool
    message: str
    device_id: str
    days_requested: int
    trigger_timestamp: datetime

class SyncTriggerCheck(BaseModel):
    has_trigger: bool
    days_to_sync: int
    trigger_id: int
    message: str

class CompleteSyncTriggerRequest(BaseModel):
    trigger_id: int = Field(..., description="ID of the completed trigger")
    success: bool = Field(..., description="Whether sync was successful")
    logs_synced: int = Field(default=0, description="Number of logs uploaded")
    error_message: str = Field(default="", description="Error message if failed")

class CompleteSyncTriggerResponse(BaseModel):
    success: bool
    message: str