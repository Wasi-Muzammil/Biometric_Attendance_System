from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import UserInformationDB
from app.models.attendance import AttendanceRecordDB
from app.schemas.user import (UserInfoResponse,CreateUserRequest,DeleteUserResponse,DeleteUserRequest,UserInfo,BulkSyncResponse,BulkSyncRequest,BulkUserSyncDeleteResponse,BulkUserSyncDeleteRequest)

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
            time=data.time
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
                "time": new_user.time
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
            "time": user_to_delete.time
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
                    time=user_data.time
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

        # -------- Step 3: Identify users missing from SD --------
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