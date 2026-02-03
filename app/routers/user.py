from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import UserInformationDB,AdminInformationDB
from app.models.attendance import AttendanceRecordDB
from app.utils.admin import *
from app.schemas.user import (UserInfoResponse,CreateUserRequest,DeleteUserResponse,DeleteUserRequest,UserInfo,BulkSyncResponse,BulkSyncRequest,BulkUserSyncDeleteResponse,BulkUserSyncDeleteRequest,AdminCreateRequest,AdminLoginRequest,AdminLoginResponse,AdminUpdateRequest,UserUpdateRequest)
from datetime import datetime
router = APIRouter(prefix="/esp32/user", tags=["User"])


# ==================== USER INFORMATION ENDPOINTS ====================

@router.post("/esp32/user", response_model=UserInfoResponse)
def create_user(
    data: CreateUserRequest,
    db: Session = Depends(get_db)
):
    """
    POST endpoint for ESP32 to create new user after fingerprint enrollment
    ESP32 sends this when a new user is successfully enrolled with 4 templates
    """
    try:
        # Check if user_id already exists
        existing_user = db.query(UserInformationDB).filter_by(
            user_id=data.id
        ).first()
        
        if existing_user:
            return UserInfoResponse(
                success=False,
                message=f"User with ID {data.id} already exists",
                user=None
            )
        
        # Check if ANY of the slot IDs are already occupied
        for slot in data.slot_id:
            # Query for users where slot_id array contains this slot
            existing_slot = db.query(UserInformationDB).filter(
                UserInformationDB.slot_id.contains([slot])
            ).first()
            
            if existing_slot:
                return UserInfoResponse(
                    success=False,
                    message=f"Slot ID {slot} is already occupied by {existing_slot.name}",
                    user=None
                )
        
        # Create new user with slot_id array
        new_user = UserInformationDB(
            name=data.name,
            user_id=data.id,
            slot_id=data.slot_id,  # Now stores as array [1,2,3,4]
            date=data.date,
            time=data.time,
            salary=None
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserInfoResponse(
            success=True,
            message="User created successfully with 4 fingerprint templates",
            user={
                "name": new_user.name,
                "user_id": new_user.user_id,
                "slot_id": new_user.slot_id,
                "date": new_user.date,
                "time": new_user.time,
                "salary": new_user.salary 
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/esp32/user/delete", response_model=DeleteUserResponse)
def delete_user(
    data: DeleteUserRequest,
    db: Session = Depends(get_db)
):
    """
    DELETE endpoint for ESP32 to delete user from database
    Deletes user with all 4 fingerprint templates and attendance records
    """
    try:
        user_to_delete = db.query(UserInformationDB).filter_by(
            user_id=data.user_id
        ).first()
        
        if not user_to_delete:
            return DeleteUserResponse(
                success=False,
                message=f"User with ID {data.user_id} not found in database",
                deleted_user=None,
                attendance_logs_deleted=0
            )
        
        # Verify slot_id array matches
        if sorted(user_to_delete.slot_id) != sorted(data.slot_id):
            return DeleteUserResponse(
                success=False,
                message=f"Slot ID mismatch: Expected {user_to_delete.slot_id}, got {data.slot_id}",
                deleted_user=None,
                attendance_logs_deleted=0
            )
        
        deleted_user_info = {
            "name": user_to_delete.name,
            "user_id": user_to_delete.user_id,
            "slot_id": user_to_delete.slot_id,
            "date": user_to_delete.date,
            "time": user_to_delete.time,
            "salary": user_to_delete.salary
        }
        
        # Delete all attendance records
        attendance_records = db.query(AttendanceRecordDB).filter_by(
            user_id=data.user_id
        ).all()
        
        attendance_count = len(attendance_records)
        
        for record in attendance_records:
            db.delete(record)
        
        # Delete user
        db.delete(user_to_delete)
        db.commit()
        
        return DeleteUserResponse(
            success=True,
            message=f"User {deleted_user_info['name']} and all {len(data.slot_id)} fingerprint templates deleted successfully",
            deleted_user=deleted_user_info,
            attendance_logs_deleted=attendance_count
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"User deletion error: {str(e)}")


@router.get("/esp32/user/{user_id}", response_model=UserInfo)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    GET endpoint to retrieve user information by user_id
    """
    user = db.query(UserInformationDB).filter_by(
        user_id=user_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {user_id} not found"
        )
    
    return UserInfo(
        name=user.name,
        user_id=user.user_id,
        slot_id=user.slot_id,
        date=user.date,
        time=user.time,
        salary=user.salary,
        created_at=user.created_at
    )

@router.get("/esp32/user/slot/{slot_id}")
def get_user_by_slot(
    slot_id: int,
    db: Session = Depends(get_db)
):
    """
    GET endpoint to retrieve user information by ANY slot_id
    Searches through slot_id arrays to find which user owns this slot
    Useful when fingerprint is detected and you need user details
    """
    # Find user where slot_id array contains this slot
    user = db.query(UserInformationDB).filter(
        UserInformationDB.slot_id.contains([slot_id])
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"No user found with slot {slot_id}"
        )
    
    return {
        "name": user.name,
        "user_id": user.user_id,
        "slot_id": user.slot_id,
        "scanned_slot": slot_id,  # Which specific slot was scanned
        "date": user.date,
        "time": user.time,
        "salary": user.salary,
        "created_at": user.created_at.isoformat()
    }

@router.post("/esp32/users/usersync", response_model=BulkSyncResponse)
def bulk_sync_users(
    data: BulkSyncRequest,
    db: Session = Depends(get_db)
):
    """
    POST endpoint for ESP32 to sync all users from SD card to database
    Handles users with multiple fingerprint templates (slot_id as array)
    """
    try:
        total_received = len(data.users)
        new_users_added = 0
        existing_users_skipped = 0
        errors = 0
        error_details = []
        
        # Get all existing user_ids
        existing_user_ids = set(
            uid[0] for uid in db.query(UserInformationDB.user_id).all()
        )
        
        # Get all existing slot IDs (flattened from arrays)
        all_existing_slots = set()
        all_slot_arrays = db.query(UserInformationDB.slot_id).all()
        for slot_array in all_slot_arrays:
            if slot_array[0]:  # Check if not None
                all_existing_slots.update(slot_array[0])
        
        new_users_to_add = []
        
        for idx, user_data in enumerate(data.users):
            try:
                # Check if user already exists
                if user_data.id in existing_user_ids:
                    existing_users_skipped += 1
                    continue
                
                # Check if ANY slot is already occupied
                slot_conflict = False
                for slot in user_data.slot_id:
                    if slot in all_existing_slots:
                        errors += 1
                        error_details.append({
                            "index": idx,
                            "user_id": user_data.id,
                            "name": user_data.name,
                            "error": f"Slot {slot} already occupied"
                        })
                        slot_conflict = True
                        break
                
                if slot_conflict:
                    continue
                
                # Prepare new user
                new_user = UserInformationDB(
                    name=user_data.name,
                    user_id=user_data.id,
                    slot_id=user_data.slot_id,  # Array of slots
                    date=user_data.date,
                    time=user_data.time,
                    salary=None
                )
                new_users_to_add.append(new_user)
                
                # Update tracking
                existing_user_ids.add(user_data.id)
                all_existing_slots.update(user_data.slot_id)
                
            except Exception as e:
                errors += 1
                error_details.append({
                    "index": idx,
                    "user_id": user_data.id if hasattr(user_data, 'id') else None,
                    "error": str(e)
                })
        
        # Bulk insert
        if new_users_to_add:
            db.bulk_save_objects(new_users_to_add)
            db.commit()
            new_users_added = len(new_users_to_add)
        
        return BulkSyncResponse(
            success=True,
            message=f"Sync complete: {new_users_added} new users with {new_users_added * 4} templates added",
            total_received=total_received,
            new_users_added=new_users_added,
            existing_users_skipped=existing_users_skipped,
            errors=errors,
            error_details=error_details if error_details else None
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk sync error: {str(e)}")

@router.get("/esp32/users")
def get_all_users(db: Session = Depends(get_db)):
    """
    GET endpoint to retrieve all enrolled users
    Now includes slot_id arrays
    """
    users = db.query(UserInformationDB).order_by(
        UserInformationDB.created_at.desc()
    ).all()
    
    user_list = []
    for user in users:
        user_list.append({
            "name": user.name,
            "user_id": user.user_id,
            "slot_id": user.slot_id,  # Returns as array [1,2,3,4]
            "total_templates": len(user.slot_id),
            "date": user.date,
            "time": user.time,
            "salary": user.salary,
            "created_at": user.created_at.isoformat()
        })
    
    total_templates = sum(len(user.slot_id) for user in users)
    
    return {
        "total_users": len(user_list),
        "total_fingerprint_templates": total_templates,
        "users": user_list
    }

@router.delete("/esp32/users/sync-delete", response_model=BulkUserSyncDeleteResponse)
def bulk_sync_delete_users(
    data: BulkUserSyncDeleteRequest,
    db: Session = Depends(get_db)
):
    """
    Bulk user reconciliation endpoint.

    ESP32 sends ALL users currently present on SD card.
    Any user existing in DB but missing from SD card is DELETED.
    """

    try:
        sd_users = data.users

        # Safety check
        if not sd_users:
            raise HTTPException(
                status_code=400,
                detail="SD user list is empty. Aborting for safety."
            )

        # -------- Step 1: Build lookup from SD card --------
        sd_user_ids = {user.id for user in sd_users}

        # -------- Step 2: Fetch all DB users --------
        db_users = db.query(UserInformationDB).all()

        users_to_delete = []
        attendance_to_delete = 0

        for db_user in db_users:
            if db_user.user_id not in sd_user_ids:
                users_to_delete.append(db_user)

        # -------- Step 4: Delete attendance + users --------
        for user in users_to_delete:
            # Delete attendance records
            attendance_records = db.query(AttendanceRecordDB).filter_by(
                user_id=user.user_id
            ).all()

            attendance_to_delete += len(attendance_records)

            for record in attendance_records:
                db.delete(record)

            # Delete user
            db.delete(user)

        db.commit()

        return BulkUserSyncDeleteResponse(
            success=True,
            message="Database reconciled successfully with SD card",
            total_db_users=len(db_users),
            total_sd_users=len(sd_users),
            users_deleted=len(users_to_delete),
            attendance_logs_deleted=attendance_to_delete
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Bulk user sync-delete error: {str(e)}"
        )
    
# Helper to seed default admin if not exists
def seed_default_admin(db: Session):
    admin = db.query(AdminInformationDB).filter_by(username="admin").first()
    if not admin:
        new_admin = AdminInformationDB(
            username="admin",
            password="admin@123",
            role="ADMIN"
        )
        db.add(new_admin)
        db.commit()

# ==================== ADMIN ENDPOINTS ====================

@router.post("/admin/login", response_model=AdminLoginResponse)
def admin_login(
    data: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Admin login endpoint
    Validates credentials from admin_information table
    """
    try:
        # Find admin by username
        admin = db.query(AdminInformationDB).filter_by(
            username=data.username
        ).first()
        
        if not admin:
            return AdminLoginResponse(
                success=False,
                message="Invalid username or password",
                token=None,
                admin=None
            )
        
        # Verify password
        if not verify_password(data.password, admin.password):
            return AdminLoginResponse(
                success=False,
                message="Invalid username or password",
                token=None,
                admin=None
            )
        
        # Successful login
        return AdminLoginResponse(
            success=True,
            message="Login successful",
            token=f"admin_session_{admin.id}",  # Simple token
            admin={
                "id": admin.id,
                "username": admin.username,
                "role": admin.role
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@router.post("/admin/create")
def create_admin(
    data: AdminCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create new admin account
    """
    try:
        # Check if username exists
        existing = db.query(AdminInformationDB).filter_by(
            username=data.username
        ).first()
        
        if existing:
            return {
                "success": False,
                "message": f"Username '{data.username}' already exists"
            }
        
        # Hash password
        hashed_pwd = hash_password(data.password)
        
        # Create admin
        new_admin = AdminInformationDB(
            username=data.username,
            password=hashed_pwd,
            role=data.role
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        return {
            "success": True,
            "message": "Admin created successfully",
            "admin": {
                "id": new_admin.id,
                "username": new_admin.username,
                "role": new_admin.role
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Admin creation error: {str(e)}")

@router.put("/admin/update")
def update_admin(
    data: AdminUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update admin information
    """
    try:
        admin = db.query(AdminInformationDB).filter_by(
            id=data.admin_id
        ).first()
        
        if not admin:
            return {
                "success": False,
                "message": f"Admin with ID {data.admin_id} not found"
            }
        
        # Update fields
        if data.username:
            # Check if new username is taken
            existing = db.query(AdminInformationDB).filter(
                AdminInformationDB.username == data.username,
                AdminInformationDB.id != data.admin_id
            ).first()
            
            if existing:
                return {
                    "success": False,
                    "message": f"Username '{data.username}' already exists"
                }
            
            admin.username = data.username
        
        if data.password:
            admin.password = hash_password(data.password)
        
        if data.role:
            admin.role = data.role
        
        admin.updated_at = datetime.now()
        
        db.commit()
        
        return {
            "success": True,
            "message": "Admin updated successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Admin update error: {str(e)}")

@router.get("/admin/list")
def list_admins(db: Session = Depends(get_db)):
    """
    Get all admin accounts
    """
    try:
        admins = db.query(AdminInformationDB).all()
        
        admin_list = []
        for admin in admins:
            admin_list.append({
                "id": admin.id,
                "username": admin.username,
                "role": admin.role,
                "created_at": admin.created_at.isoformat()
            })
        
        return {
            "total_admins": len(admin_list),
            "admins": admin_list
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ==================== USER UPDATE ENDPOINT ====================

@router.put("/admin/user/update")
def update_user_admin(
    data: UserUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update user information (admin endpoint)
    Allows updating name, slot_id array, date, time, salary
    """
    try:
        user = db.query(UserInformationDB).filter_by(
            user_id=data.user_id
        ).first()

        if not user:
            return {
                "success": False,
                "message": f"User with ID {data.user_id} not found"
            }

        if data.name:
            user.name = data.name

        if data.slot_id is not None:
            for slot in data.slot_id:
                existing_slot = db.query(UserInformationDB).filter(
                    UserInformationDB.slot_id.contains([slot]),
                    UserInformationDB.user_id != data.user_id
                ).first()

                if existing_slot:
                    return {
                        "success": False,
                        "message": f"Slot {slot} is already used by {existing_slot.name}"
                    }

            user.slot_id = data.slot_id

        if data.date:
            user.date = data.date

        if data.time:
            user.time = data.time

        # ✅ NEW (NO LOGIC CHANGE)
        if data.salary is not None:
            user.salary = data.salary

        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "message": f"User {user.name} updated successfully",
            "user": {
                "name": user.name,
                "user_id": user.user_id,
                "slot_id": user.slot_id,
                "date": user.date,
                "time": user.time,
                "salary": user.salary
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"User update error: {str(e)}")


# ==================== DASHBOARD STATS ENDPOINT ====================

@router.get("/admin/stats/dashboard")
def get_dashboard_statistics(db: Session = Depends(get_db)):
    """
    Get dashboard statistics for admin panel
    Returns: total users, today's attendance stats
    """
    try:
        # Total users
        total_users = db.query(UserInformationDB).count()
        
        # Today's date in DD/MM format
        today = datetime.now().strftime("%d/%m")
        
        # Today's attendance records
        today_records = db.query(AttendanceRecordDB).filter_by(
            date=today
        ).all()
        
        # Count check-ins and check-outs
        checked_in = 0
        checked_out = 0
        
        for record in today_records:
            if record.checked_in_time:
                checked_in += 1
            if record.checked_out_time:
                checked_out += 1
        
        return {
            "total_users": total_users,
            "today_records": len(today_records),
            "checked_in": checked_in,
            "checked_out": checked_out,
            "date": today
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")

# ==================== INITIALIZATION ENDPOINT ====================

@router.post("/admin/init")
def initialize_default_admin(db: Session = Depends(get_db)):
    """
    Initialize default admin account (run once during setup)
    Creates: username='admin', password='admin@123'
    """
    try:
        # Check if any admin exists
        existing_admin = db.query(AdminInformationDB).first()
        
        if existing_admin:
            return {
                "success": False,
                "message": "Admin already exists. Use /admin/create for additional admins."
            }
        
        # Create default admin
        default_admin = AdminInformationDB(
            username="admin",
            password=hash_password("admin@123"),
            role="super_admin"
        )
        
        db.add(default_admin)
        db.commit()
        
        return {
            "success": True,
            "message": "Default admin created successfully",
            "credentials": {
                "username": "admin",
                "password": "admin@123",
                "note": "CHANGE THIS PASSWORD IMMEDIATELY!"
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Initialization error: {str(e)}")

# ==================== ATTENDANCE RANGE ENDPOINT ====================

@router.get("/admin/attendance/range")
def get_attendance_range(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    """
    Get attendance records for a date range
    
    Args:
        start_date: Start date in DD/MM format
        end_date: End date in DD/MM format
    
    Returns:
        All attendance records in the range
    """
    try:
        # Since dates are stored as strings (DD/MM), we need to fetch and filter
        all_records = db.query(AttendanceRecordDB).order_by(
            AttendanceRecordDB.date
        ).all()
        
        # Filter records (simple string comparison for DD/MM format)
        filtered_records = []
        
        for record in all_records:
            if start_date <= record.date <= end_date:
                filtered_records.append({
                    "name": record.name,
                    "user_id": record.user_id,
                    "slot_id": record.slot_id,
                    "date": record.date,
                    "checked_in_time": record.checked_in_time,
                    "checked_out_time": record.checked_out_time,
                    "is_present": record.is_present
                })
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_records": len(filtered_records),
            "records": filtered_records
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Range query error: {str(e)}")
