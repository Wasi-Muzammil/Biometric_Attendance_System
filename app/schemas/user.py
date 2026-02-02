from pydantic import BaseModel,Field
from typing import List, Optional
from datetime import datetime

# User Information Schemas
class CreateUserRequest(BaseModel):
    name: str = Field(..., description="User's full name")
    id: int = Field(..., description="Unique user ID")
    slot_id: List[int] = Field(..., description="Array of fingerprint slot IDs (4 templates)")
    date: str = Field(..., description="Enrollment date (DD/MM format)")
    time: str = Field(..., description="Enrollment time (HH:MM:SS format)")
    salary: Optional[float] = Field(None, description="Daily salary (optional)")

class DeleteUserRequest(BaseModel):
    user_id: int = Field(..., description="User ID to delete")
    slot_id: List[int] = Field(..., description="Array of fingerprint slot IDs to delete")

class DeleteUserResponse(BaseModel):
    success: bool
    message: str
    deleted_user: Optional[dict] = None
    attendance_logs_deleted: int = 0

class UserInfoResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None
    
class UserInfo(BaseModel):
    name: str
    user_id: int
    slot_id: List[int]  
    date: str
    time: str
    salary: Optional[float] = None  
    created_at: datetime
    
    class Config:
        orm_mode = True

# Bulk Sync Schemas
class BulkUserData(BaseModel):
    name: str
    id: int
    slot_id: List[int]  # Changed to List
    date: str
    time: str

class BulkSyncRequest(BaseModel):
    users: List[BulkUserData] = Field(..., description="List of all enrolled users from ESP32")

class BulkSyncResponse(BaseModel):
    success: bool
    message: str
    total_received: int
    new_users_added: int
    existing_users_skipped: int
    errors: int
    error_details: Optional[List[dict]] = None

class SDUser(BaseModel):
    name: str
    id: int
    slot_id: List[int]  # Changed to List

class BulkUserSyncDeleteRequest(BaseModel):
    users: list[SDUser]

class BulkUserSyncDeleteResponse(BaseModel):
    success: bool
    message: str
    total_db_users: int
    total_sd_users: int
    users_deleted: int
    attendance_logs_deleted: int

class AdminLoginRequest(BaseModel):
    username: str = Field(..., description="Admin username")
    password: str = Field(..., description="Admin password")

class AdminLoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    admin: Optional[dict] = None

class AdminCreateRequest(BaseModel):
    username: str = Field(..., description="New admin username")
    password: str = Field(..., description="New admin password")
    role: str = Field(default="admin", description="Admin role")

class AdminUpdateRequest(BaseModel):
    admin_id: int = Field(..., description="Admin ID to update")
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

class UserUpdateRequest(BaseModel):
    user_id: int = Field(..., description="User ID to update")
    name: Optional[str] = None
    slot_id: Optional[list[int]] = None
    date: Optional[str] = None
    time: Optional[str] = None
    salary: Optional[float] = None