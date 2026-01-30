from pydantic import BaseModel,Field
from typing import List, Optional

# Attendance Log Schemas
class AttendanceLogRequest(BaseModel):
    name: str = Field(..., description="User's full name")
    id: int = Field(..., description="User ID")
    slot_id: List[int] = Field(..., description="Array of fingerprint slot IDs")
    date: str = Field(..., description="Date (DD/MM format)")
    time: str = Field(..., description="Time (HH:MM format)")

class AttendanceLogResponse(BaseModel):
    success: bool
    message: str
    action: str  # "checked_in", "checked_out", or "updated_checkout"
    attendance_record: Optional[dict] = None

class AttendanceBulkRequest(BaseModel):
    logs: List[AttendanceLogRequest]