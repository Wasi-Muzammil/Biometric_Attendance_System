# # main.py - FastAPI Backend for ESP32 Fingerprint Attendance System
# # Following SQLAlchemy ORM pattern

# from typing import Optional , List
# from fastapi import FastAPI, HTTPException, Depends
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field
# from sqlalchemy import create_engine, Column, Integer, String, DateTime ,Boolean, tuple_, ARRAY
# from sqlalchemy.orm import declarative_base, sessionmaker, Session
# from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
# from datetime import datetime, timedelta

# # ==================== DATABASE SETUP ====================
# DATABASE_URL = "postgresql+psycopg2://Admin:Admin@db:5432/UserDB"

# engine = create_engine(DATABASE_URL, echo=True)
# Base = declarative_base()
# SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# # ==================== DATABASE MODELS ====================
# class DeviceStatusDB(Base):
#     __tablename__ = "device_status"
    
#     id = Column(Integer, primary_key=True, index=True)
#     device_id = Column(String, unique=True, nullable=False, index=True)
#     status = Column(String, nullable=False)
#     last_seen = Column(DateTime, nullable=False)
#     created_at = Column(DateTime, default=datetime.now)
#     updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# class UserInformationDB(Base):
#     __tablename__ = "user_information"
    
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String, nullable=False)
#     user_id = Column(Integer, unique=True, nullable=False, index=True)
#     slot_id = Column(PG_ARRAY(Integer), nullable=False)  # Changed to ARRAY
#     date = Column(String, nullable=False)
#     time = Column(String, nullable=False)
#     created_at = Column(DateTime, default=datetime.now)

# class AttendanceRecordDB(Base):
#     __tablename__ = "attendance_records"
    
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String, nullable=False)
#     user_id = Column(Integer, nullable=False, index=True)
#     slot_id = Column(PG_ARRAY(Integer), nullable=False)  # Added slot_id as array
#     date = Column(String, nullable=False, index=True)
#     checked_in_time = Column(String, nullable=True)
#     checked_out_time = Column(String, nullable=True)
#     is_present = Column(Boolean, default=False, nullable=False)
#     created_at = Column(DateTime, default=datetime.now)
#     updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# # Create tables
# Base.metadata.create_all(bind=engine)

# # ==================== PYDANTIC SCHEMAS ====================
# class StatusUpdateRequest(BaseModel):
#     device_id: str = Field(default="ESP32_MAIN", description="Unique device identifier")
#     status: str = Field(..., description="Device status (Online/Offline)")

# class StatusResponse(BaseModel):
#     success: bool
#     message: str
#     device_id: str
#     status: str
#     last_seen: datetime
#     last_seen_seconds_ago: int
#     is_online: bool
    
#     class Config:
#         orm_mode = True

# class DeviceStatusInfo(BaseModel):
#     device_id: str
#     status: str
#     last_seen: datetime
#     last_seen_seconds_ago: int
#     is_online: bool
    
#     class Config:
#         orm_mode = True

# # User Information Schemas
# class CreateUserRequest(BaseModel):
#     name: str = Field(..., description="User's full name")
#     id: int = Field(..., description="Unique user ID")
#     slot_id: List[int] = Field(..., description="Array of fingerprint slot IDs (4 templates)")
#     date: str = Field(..., description="Enrollment date (DD/MM format)")
#     time: str = Field(..., description="Enrollment time (HH:MM:SS format)")

# class DeleteUserRequest(BaseModel):
#     user_id: int = Field(..., description="User ID to delete")
#     slot_id: List[int] = Field(..., description="Array of fingerprint slot IDs to delete")

# class DeleteUserResponse(BaseModel):
#     success: bool
#     message: str
#     deleted_user: Optional[dict] = None
#     attendance_logs_deleted: int = 0

# class UserInfoResponse(BaseModel):
#     success: bool
#     message: str
#     user: Optional[dict] = None
    
# class UserInfo(BaseModel):
#     name: str
#     user_id: int
#     slot_id: List[int]  # Changed to List
#     date: str
#     time: str
#     created_at: datetime
    
#     class Config:
#         orm_mode = True

# # Bulk Sync Schemas
# class BulkUserData(BaseModel):
#     name: str
#     id: int
#     slot_id: List[int]  # Changed to List
#     date: str
#     time: str

# class BulkSyncRequest(BaseModel):
#     users: List[BulkUserData] = Field(..., description="List of all enrolled users from ESP32")

# class BulkSyncResponse(BaseModel):
#     success: bool
#     message: str
#     total_received: int
#     new_users_added: int
#     existing_users_skipped: int
#     errors: int
#     error_details: Optional[List[dict]] = None

# # Attendance Log Schemas
# class AttendanceLogRequest(BaseModel):
#     name: str = Field(..., description="User's full name")
#     id: int = Field(..., description="User ID")
#     slot_id: List[int] = Field(..., description="Array of fingerprint slot IDs")
#     date: str = Field(..., description="Date (DD/MM format)")
#     time: str = Field(..., description="Time (HH:MM format)")

# class AttendanceLogResponse(BaseModel):
#     success: bool
#     message: str
#     action: str  # "checked_in", "checked_out", or "updated_checkout"
#     attendance_record: Optional[dict] = None

# class AttendanceBulkRequest(BaseModel):
#     logs: List[AttendanceLogRequest]

# class SDUser(BaseModel):
#     name: str
#     id: int
#     slot_id: List[int]  # Changed to List

# class BulkUserSyncDeleteRequest(BaseModel):
#     users: list[SDUser]

# class BulkUserSyncDeleteResponse(BaseModel):
#     success: bool
#     message: str
#     total_db_users: int
#     total_sd_users: int
#     users_deleted: int
#     attendance_logs_deleted: int

# # ==================== FASTAPI APP ====================
# api = FastAPI(
#     title="ESP32 Attendance System API",
#     description="REST API for Fingerprint Attendance System",
#     version="1.0.0"
# )

# # CORS Configuration
# api.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, specify your frontend URL
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ==================== DEPENDENCY ====================
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # ==================== HELPER FUNCTIONS ====================
# OFFLINE_THRESHOLD_SECONDS = 120

# def calculate_device_status(device: DeviceStatusDB) -> dict:
#     """Calculate if device is online based on last_seen timestamp"""
#     current_time = datetime.now()
#     time_diff = (current_time - device.last_seen).total_seconds()
    
#     is_online = (time_diff < OFFLINE_THRESHOLD_SECONDS) and \
#                 (device.status.lower() == 'online')
    
#     actual_status = "Online" if is_online else "Offline"
    
#     return {
#         "device_id": device.device_id,
#         "status": actual_status,
#         "last_seen": device.last_seen,
#         "last_seen_seconds_ago": int(time_diff),
#         "is_online": is_online
#     }

# # ==================== API ENDPOINTS ====================

# @api.get("/")
# def root():
#     """API root endpoint"""
#     return {
#     }

# @api.post("/esp32/status", response_model=StatusResponse)
# def update_device_status(
#     data: StatusUpdateRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     POST endpoint for ESP32 to send heartbeat/status updates
#     ESP32 calls this every 30 seconds to maintain "Online" status
#     """
#     try:
#         # Check if device already exists
#         device = db.query(DeviceStatusDB).filter_by(
#             device_id=data.device_id
#         ).first()
        
#         current_time = datetime.now()
        
#         if device:
#             # Update existing device
#             device.status = data.status
#             device.last_seen = current_time
#             device.updated_at = current_time
#         else:
#             # Create new device entry
#             device = DeviceStatusDB(
#                 device_id=data.device_id,
#                 status=data.status,
#                 last_seen=current_time,
#             )
#             db.add(device)
        
#         db.commit()
#         db.refresh(device)
        
#         return StatusResponse(
#             success=True,
#             message="Status updated successfully",
#             device_id=device.device_id,
#             status=device.status,
#             last_seen=device.last_seen,
#             last_seen_seconds_ago=0,
#             is_online=True
#         )
        
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# @api.get("/esp32/status/{device_id}", response_model=DeviceStatusInfo)
# def get_device_status(
#     device_id: str,
#     db: Session = Depends(get_db)
# ):
#     """
#     GET endpoint to retrieve current status of a specific ESP32 device
#     Frontend uses this to display device status in real-time
#     """
#     device = db.query(DeviceStatusDB).filter_by(
#         device_id=device_id
#     ).first()
    
#     if not device:
#         raise HTTPException(
#             status_code=404,
#             detail=f"Device '{device_id}' not found"
#         )
    
#     # Calculate current status
#     status_info = calculate_device_status(device)
    
#     return DeviceStatusInfo(**status_info)

# @api.get("/esp32/status")
# def get_all_devices_status(db: Session = Depends(get_db)):
#     """
#     GET endpoint to retrieve status of all registered ESP32 devices
#     Useful for monitoring multiple devices
#     """
#     devices = db.query(DeviceStatusDB).order_by(
#         DeviceStatusDB.last_seen.desc()
#     ).all()
    
#     device_list = []
#     for device in devices:
#         status_info = calculate_device_status(device)
#         device_list.append(status_info)
    
#     online_count = sum(1 for d in device_list if d['is_online'])
#     offline_count = len(device_list) - online_count
    
#     return {
#         "total_devices": len(device_list),
#         "online_devices": online_count,
#         "offline_devices": offline_count,
#         "devices": device_list
#     }


# # ==================== USER INFORMATION ENDPOINTS ====================

# @api.post("/esp32/user", response_model=UserInfoResponse)
# def create_user(
#     data: CreateUserRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     POST endpoint for ESP32 to create new user after fingerprint enrollment
#     ESP32 sends this when a new user is successfully enrolled with 4 templates
#     """
#     try:
#         # Check if user_id already exists
#         existing_user = db.query(UserInformationDB).filter_by(
#             user_id=data.id
#         ).first()
        
#         if existing_user:
#             return UserInfoResponse(
#                 success=False,
#                 message=f"User with ID {data.id} already exists",
#                 user=None
#             )
        
#         # Check if ANY of the slot IDs are already occupied
#         for slot in data.slot_id:
#             # Query for users where slot_id array contains this slot
#             existing_slot = db.query(UserInformationDB).filter(
#                 UserInformationDB.slot_id.contains([slot])
#             ).first()
            
#             if existing_slot:
#                 return UserInfoResponse(
#                     success=False,
#                     message=f"Slot ID {slot} is already occupied by {existing_slot.name}",
#                     user=None
#                 )
        
#         # Create new user with slot_id array
#         new_user = UserInformationDB(
#             name=data.name,
#             user_id=data.id,
#             slot_id=data.slot_id,  # Now stores as array [1,2,3,4]
#             date=data.date,
#             time=data.time
#         )
        
#         db.add(new_user)
#         db.commit()
#         db.refresh(new_user)
        
#         return UserInfoResponse(
#             success=True,
#             message="User created successfully with 4 fingerprint templates",
#             user={
#                 "name": new_user.name,
#                 "user_id": new_user.user_id,
#                 "slot_id": new_user.slot_id,
#                 "date": new_user.date,
#                 "time": new_user.time
#             }
#         )
        
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# @api.delete("/esp32/user/delete", response_model=DeleteUserResponse)
# def delete_user(
#     data: DeleteUserRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     DELETE endpoint for ESP32 to delete user from database
#     Deletes user with all 4 fingerprint templates and attendance records
#     """
#     try:
#         user_to_delete = db.query(UserInformationDB).filter_by(
#             user_id=data.user_id
#         ).first()
        
#         if not user_to_delete:
#             return DeleteUserResponse(
#                 success=False,
#                 message=f"User with ID {data.user_id} not found in database",
#                 deleted_user=None,
#                 attendance_logs_deleted=0
#             )
        
#         # Verify slot_id array matches
#         if sorted(user_to_delete.slot_id) != sorted(data.slot_id):
#             return DeleteUserResponse(
#                 success=False,
#                 message=f"Slot ID mismatch: Expected {user_to_delete.slot_id}, got {data.slot_id}",
#                 deleted_user=None,
#                 attendance_logs_deleted=0
#             )
        
#         deleted_user_info = {
#             "name": user_to_delete.name,
#             "user_id": user_to_delete.user_id,
#             "slot_id": user_to_delete.slot_id,
#             "date": user_to_delete.date,
#             "time": user_to_delete.time
#         }
        
#         # Delete all attendance records
#         attendance_records = db.query(AttendanceRecordDB).filter_by(
#             user_id=data.user_id
#         ).all()
        
#         attendance_count = len(attendance_records)
        
#         for record in attendance_records:
#             db.delete(record)
        
#         # Delete user
#         db.delete(user_to_delete)
#         db.commit()
        
#         return DeleteUserResponse(
#             success=True,
#             message=f"User {deleted_user_info['name']} and all {len(data.slot_id)} fingerprint templates deleted successfully",
#             deleted_user=deleted_user_info,
#             attendance_logs_deleted=attendance_count
#         )
        
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"User deletion error: {str(e)}")


# @api.get("/esp32/user/{user_id}", response_model=UserInfo)
# def get_user_by_id(
#     user_id: int,
#     db: Session = Depends(get_db)
# ):
#     """
#     GET endpoint to retrieve user information by user_id
#     """
#     user = db.query(UserInformationDB).filter_by(
#         user_id=user_id
#     ).first()
    
#     if not user:
#         raise HTTPException(
#             status_code=404,
#             detail=f"User with ID {user_id} not found"
#         )
    
#     return UserInfo(
#         name=user.name,
#         user_id=user.user_id,
#         slot_id=user.slot_id,
#         date=user.date,
#         time=user.time,
#         created_at=user.created_at
#     )

# @api.get("/esp32/user/slot/{slot_id}")
# def get_user_by_slot(
#     slot_id: int,
#     db: Session = Depends(get_db)
# ):
#     """
#     GET endpoint to retrieve user information by ANY slot_id
#     Searches through slot_id arrays to find which user owns this slot
#     Useful when fingerprint is detected and you need user details
#     """
#     # Find user where slot_id array contains this slot
#     user = db.query(UserInformationDB).filter(
#         UserInformationDB.slot_id.contains([slot_id])
#     ).first()
    
#     if not user:
#         raise HTTPException(
#             status_code=404,
#             detail=f"No user found with slot {slot_id}"
#         )
    
#     return {
#         "name": user.name,
#         "user_id": user.user_id,
#         "slot_id": user.slot_id,
#         "scanned_slot": slot_id,  # Which specific slot was scanned
#         "date": user.date,
#         "time": user.time,
#         "created_at": user.created_at.isoformat()
#     }

# @api.post("/esp32/users/usersync", response_model=BulkSyncResponse)
# def bulk_sync_users(
#     data: BulkSyncRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     POST endpoint for ESP32 to sync all users from SD card to database
#     Handles users with multiple fingerprint templates (slot_id as array)
#     """
#     try:
#         total_received = len(data.users)
#         new_users_added = 0
#         existing_users_skipped = 0
#         errors = 0
#         error_details = []
        
#         # Get all existing user_ids
#         existing_user_ids = set(
#             uid[0] for uid in db.query(UserInformationDB.user_id).all()
#         )
        
#         # Get all existing slot IDs (flattened from arrays)
#         all_existing_slots = set()
#         all_slot_arrays = db.query(UserInformationDB.slot_id).all()
#         for slot_array in all_slot_arrays:
#             if slot_array[0]:  # Check if not None
#                 all_existing_slots.update(slot_array[0])
        
#         new_users_to_add = []
        
#         for idx, user_data in enumerate(data.users):
#             try:
#                 # Check if user already exists
#                 if user_data.id in existing_user_ids:
#                     existing_users_skipped += 1
#                     continue
                
#                 # Check if ANY slot is already occupied
#                 slot_conflict = False
#                 for slot in user_data.slot_id:
#                     if slot in all_existing_slots:
#                         errors += 1
#                         error_details.append({
#                             "index": idx,
#                             "user_id": user_data.id,
#                             "name": user_data.name,
#                             "error": f"Slot {slot} already occupied"
#                         })
#                         slot_conflict = True
#                         break
                
#                 if slot_conflict:
#                     continue
                
#                 # Prepare new user
#                 new_user = UserInformationDB(
#                     name=user_data.name,
#                     user_id=user_data.id,
#                     slot_id=user_data.slot_id,  # Array of slots
#                     date=user_data.date,
#                     time=user_data.time
#                 )
#                 new_users_to_add.append(new_user)
                
#                 # Update tracking
#                 existing_user_ids.add(user_data.id)
#                 all_existing_slots.update(user_data.slot_id)
                
#             except Exception as e:
#                 errors += 1
#                 error_details.append({
#                     "index": idx,
#                     "user_id": user_data.id if hasattr(user_data, 'id') else None,
#                     "error": str(e)
#                 })
        
#         # Bulk insert
#         if new_users_to_add:
#             db.bulk_save_objects(new_users_to_add)
#             db.commit()
#             new_users_added = len(new_users_to_add)
        
#         return BulkSyncResponse(
#             success=True,
#             message=f"Sync complete: {new_users_added} new users with {new_users_added * 4} templates added",
#             total_received=total_received,
#             new_users_added=new_users_added,
#             existing_users_skipped=existing_users_skipped,
#             errors=errors,
#             error_details=error_details if error_details else None
#         )
        
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Bulk sync error: {str(e)}")

# @api.get("/esp32/users")
# def get_all_users(db: Session = Depends(get_db)):
#     """
#     GET endpoint to retrieve all enrolled users
#     Now includes slot_id arrays
#     """
#     users = db.query(UserInformationDB).order_by(
#         UserInformationDB.created_at.desc()
#     ).all()
    
#     user_list = []
#     for user in users:
#         user_list.append({
#             "name": user.name,
#             "user_id": user.user_id,
#             "slot_id": user.slot_id,  # Returns as array [1,2,3,4]
#             "total_templates": len(user.slot_id),
#             "date": user.date,
#             "time": user.time,
#             "created_at": user.created_at.isoformat()
#         })
    
#     total_templates = sum(len(user.slot_id) for user in users)
    
#     return {
#         "total_users": len(user_list),
#         "total_fingerprint_templates": total_templates,
#         "users": user_list
#     }

# # ==================== ATTENDANCE LOG ENDPOINTS ====================

# @api.post("/esp32/attendance", response_model=AttendanceLogResponse)
# def log_attendance(
#     data: AttendanceLogRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     POST endpoint for ESP32 to log attendance
#     Now stores slot_id array with attendance record
#     """
#     try:
#         existing_record = db.query(AttendanceRecordDB).filter_by(
#             user_id=data.id,
#             date=data.date
#         ).first()
        
#         if existing_record:
#             # Update check-out time
#             existing_record.checked_out_time = data.time
#             existing_record.updated_at = datetime.now()
            
#             db.commit()
#             db.refresh(existing_record)
            
#             return AttendanceLogResponse(
#                 success=True,
#                 message=f"Check-out time updated for {data.name}",
#                 action="checked_out",
#                 attendance_record={
#                     "name": existing_record.name,
#                     "user_id": existing_record.user_id,
#                     "slot_id": existing_record.slot_id,
#                     "date": existing_record.date,
#                     "checked_in_time": existing_record.checked_in_time,
#                     "checked_out_time": existing_record.checked_out_time,
#                     "is_present": existing_record.is_present
#                 }
#             )
#         else:
#             # First log - check-in
#             new_record = AttendanceRecordDB(
#                 name=data.name,
#                 user_id=data.id,
#                 slot_id=data.slot_id,  # Store slot array
#                 date=data.date,
#                 checked_in_time=data.time,
#                 checked_out_time=None,
#                 is_present=True
#             )
            
#             db.add(new_record)
#             db.commit()
#             db.refresh(new_record)
            
#             return AttendanceLogResponse(
#                 success=True,
#                 message=f"{data.name} checked in successfully",
#                 action="checked_in",
#                 attendance_record={
#                     "name": new_record.name,
#                     "user_id": new_record.user_id,
#                     "slot_id": new_record.slot_id,
#                     "date": new_record.date,
#                     "checked_in_time": new_record.checked_in_time,
#                     "checked_out_time": new_record.checked_out_time,
#                     "is_present": new_record.is_present
#                 }
#             )
        
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Attendance logging error: {str(e)}")

# @api.get("/esp32/attendance/{user_id}/{date}")
# def get_attendance_by_user_date(
#     user_id: int,
#     date: str,
#     db: Session = Depends(get_db)
# ):
#     """GET endpoint to retrieve attendance record for a specific user and date"""
#     record = db.query(AttendanceRecordDB).filter_by(
#         user_id=user_id,
#         date=date
#     ).first()
    
#     if not record:
#         raise HTTPException(
#             status_code=404,
#             detail=f"No attendance record found for user {user_id} on {date}"
#         )
    
#     return {
#         "name": record.name,
#         "user_id": record.user_id,
#         "date": record.date,
#         "checked_in_time": record.checked_in_time,
#         "checked_out_time": record.checked_out_time,
#         "is_present": record.is_present,
#         "created_at": record.created_at.isoformat(),
#         "updated_at": record.updated_at.isoformat()
#     }

# @api.get("/esp32/attendance/date/{date}")
# def get_attendance_by_date(date: str, db: Session = Depends(get_db)):
#     """GET endpoint to retrieve all attendance records for a specific date"""
#     records = db.query(AttendanceRecordDB).filter_by(date=date).order_by(
#         AttendanceRecordDB.checked_in_time
#     ).all()
    
#     attendance_list = []
#     for record in records:
#         attendance_list.append({
#             "name": record.name,
#             "user_id": record.user_id,
#             "date": record.date,
#             "checked_in_time": record.checked_in_time,
#             "checked_out_time": record.checked_out_time,
#             "is_present": record.is_present
#         })
    
#     present_count = sum(1 for r in attendance_list if r['is_present'])
    
#     return {
#         "date": date,
#         "total_records": len(attendance_list),
#         "present_count": present_count,
#         "absent_count": len(attendance_list) - present_count,
#         "records": attendance_list
#     }

# @api.post("/esp32/attendance/bulk")
# def log_bulk_attendance(
#     data: AttendanceBulkRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     Bulk attendance upload from ESP32 SD card.

#     Logic:
#     - Same as single attendance API
#     - Optimized for 100s of logs
#     - Single DB commit
#     """

#     try:
#         logs = data.logs

#         if not logs:
#             return {"success": True, "message": "No logs received", "processed": 0}

#         # Preload existing records for optimization
#         user_date_pairs = {(log.id, log.date) for log in logs}

#         existing_records = db.query(AttendanceRecordDB).filter(
#             tuple_(
#                 AttendanceRecordDB.user_id,
#                 AttendanceRecordDB.date
#             ).in_(user_date_pairs)
#         ).all()

#         # Convert to lookup dictionary
#         record_map = {
#             (r.user_id, r.date): r for r in existing_records
#         }

#         created = 0
#         updated = 0

#         for log in logs:
#             key = (log.id, log.date)

#             if key in record_map:
#                 # Update checkout time
#                 record = record_map[key]
#                 record.checked_out_time = log.time
#                 record.updated_at = datetime.now()
#                 updated += 1
#             else:
#                 # First log of the day
#                 new_record = AttendanceRecordDB(
#                     name=log.name,
#                     user_id=log.id,
#                     date=log.date,
#                     checked_in_time=log.time,
#                     checked_out_time=None,
#                     is_present=True
#                 )
#                 db.add(new_record)
#                 record_map[key] = new_record
#                 created += 1

#         db.commit()

#         return {
#             "success": True,
#             "message": "Bulk attendance processed successfully",
#             "total_logs": len(logs),
#             "created_records": created,
#             "updated_records": updated
#         }

#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Bulk attendance logging error: {str(e)}"
#         )

# @api.delete("/esp32/users/sync-delete", response_model=BulkUserSyncDeleteResponse)
# def bulk_sync_delete_users(
#     data: BulkUserSyncDeleteRequest,
#     db: Session = Depends(get_db)
# ):
#     """
#     Bulk user reconciliation endpoint.

#     ESP32 sends ALL users currently present on SD card.
#     Any user existing in DB but missing from SD card is DELETED.
#     """

#     try:
#         sd_users = data.users

#         # Safety check
#         if not sd_users:
#             raise HTTPException(
#                 status_code=400,
#                 detail="SD user list is empty. Aborting for safety."
#             )

#         # -------- Step 1: Build lookup from SD card --------
#         sd_user_ids = {user.id for user in sd_users}

#         # -------- Step 2: Fetch all DB users --------
#         db_users = db.query(UserInformationDB).all()

#         users_to_delete = []
#         attendance_to_delete = 0

#         # -------- Step 3: Identify users missing from SD --------
#         for db_user in db_users:
#             if db_user.user_id not in sd_user_ids:
#                 users_to_delete.append(db_user)

#         # -------- Step 4: Delete attendance + users --------
#         for user in users_to_delete:
#             # Delete attendance records
#             attendance_records = db.query(AttendanceRecordDB).filter_by(
#                 user_id=user.user_id
#             ).all()

#             attendance_to_delete += len(attendance_records)

#             for record in attendance_records:
#                 db.delete(record)

#             # Delete user
#             db.delete(user)

#         db.commit()

#         return BulkUserSyncDeleteResponse(
#             success=True,
#             message="Database reconciled successfully with SD card",
#             total_db_users=len(db_users),
#             total_sd_users=len(sd_users),
#             users_deleted=len(users_to_delete),
#             attendance_logs_deleted=attendance_to_delete
#         )

#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Bulk user sync-delete error: {str(e)}"
#         )

# @api.get("/health")
# def health_check():
#     """Health check endpoint"""
#     try:
#         # Test database connection
#         db = SessionLocal()
#         db.execute("SELECT 1")
#         db.close()
        
#         return {
#             "status": "healthy",
#             "database": "connected",
#             "timestamp": datetime.now().isoformat()
#         }
#     except Exception as e:
#         return {
#             "status": "unhealthy",
#             "database": "disconnected",
#             "error": str(e),
#             "timestamp": datetime.now().isoformat()
#         }




from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.routers import device, user, attendance

Base.metadata.create_all(bind=engine)


# ==================== FASTAPI APP ====================
app = FastAPI(
    title="ESP32 Attendance System API",
    description="REST API for Fingerprint Attendance System",
    version="1.0.0"
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(device.router)
app.include_router(user.router)
app.include_router(attendance.router)

@app.get("/")
def root():
    return {"status": "FastAPI running on Vercel 🚀"}

@app.get("/health")
def health():
    return {"status": "healthy"}

