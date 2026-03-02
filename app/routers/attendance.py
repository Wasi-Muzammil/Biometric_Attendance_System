from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import tuple_
from datetime import datetime
from app.core.database import get_db
from app.models.attendance import AttendanceRecordDB,AttendanceSyncTriggerDB
from app.schemas.attendance import (AttendanceLogRequest,AttendanceLogResponse,AttendanceBulkRequest,TriggerAttendanceSyncRequest,TriggerAttendanceSyncResponse,SyncTriggerCheck,CompleteSyncTriggerRequest,CompleteSyncTriggerResponse)

router = APIRouter(prefix="/esp32/attendance", tags=["Attendance"])



# ==================== ATTENDANCE LOG ENDPOINTS ====================

@router.post("/esp32/attendance", response_model=AttendanceLogResponse)
def log_attendance(
    data: AttendanceLogRequest,
    db: Session = Depends(get_db)
):
    """
    POST endpoint for ESP32 to log attendance
    Now stores slot_id array with attendance record
    """
    try:
        existing_record = db.query(AttendanceRecordDB).filter_by(
            user_id=data.id,
            date=data.date
        ).first()
        
        if existing_record:
            # Update check-out time
            existing_record.checked_out_time = data.time
            existing_record.updated_at = datetime.now()
            
            db.commit()
            db.refresh(existing_record)
            
            return AttendanceLogResponse(
                success=True,
                message=f"Check-out time updated for {data.name}",
                action="checked_out",
                attendance_record={
                    "name": existing_record.name,
                    "user_id": existing_record.user_id,
                    "slot_id": existing_record.slot_id,
                    "date": existing_record.date,
                    "checked_in_time": existing_record.checked_in_time,
                    "checked_out_time": existing_record.checked_out_time,
                    "is_present": existing_record.is_present
                }
            )
        else:
            # First log - check-in
            new_record = AttendanceRecordDB(
                name=data.name,
                user_id=data.id,
                slot_id=data.slot_id,  # Store slot array
                date=data.date,
                checked_in_time=data.time,
                checked_out_time=None,
                is_present=True
            )
            
            db.add(new_record)
            db.commit()
            db.refresh(new_record)
            
            return AttendanceLogResponse(
                success=True,
                message=f"{data.name} checked in successfully",
                action="checked_in",
                attendance_record={
                    "name": new_record.name,
                    "user_id": new_record.user_id,
                    "slot_id": new_record.slot_id,
                    "date": new_record.date,
                    "checked_in_time": new_record.checked_in_time,
                    "checked_out_time": new_record.checked_out_time,
                    "is_present": new_record.is_present
                }
            )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Attendance logging error: {str(e)}")

@router.get("/esp32/attendance/{user_id}/{date}")
def get_attendance_by_user_date(
    user_id: int,
    date: str,
    db: Session = Depends(get_db)
):
    """GET endpoint to retrieve attendance record for a specific user and date"""
    record = db.query(AttendanceRecordDB).filter_by(
        user_id=user_id,
        date=date
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No attendance record found for user {user_id} on {date}"
        )
    
    return {
        "name": record.name,
        "user_id": record.user_id,
        "date": record.date,
        "checked_in_time": record.checked_in_time,
        "checked_out_time": record.checked_out_time,
        "is_present": record.is_present,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat()
    }

@router.get("/esp32/attendance/date/{date}")
def get_attendance_by_date(date: str, db: Session = Depends(get_db)):
    """GET endpoint to retrieve all attendance records for a specific date"""
    records = db.query(AttendanceRecordDB).filter_by(date=date).order_by(
        AttendanceRecordDB.checked_in_time
    ).all()
    
    attendance_list = []
    for record in records:
        attendance_list.append({
            "name": record.name,
            "user_id": record.user_id,
            "date": record.date,
            "checked_in_time": record.checked_in_time,
            "checked_out_time": record.checked_out_time,
            "is_present": record.is_present
        })
    
    present_count = sum(1 for r in attendance_list if r['is_present'])
    
    return {
        "date": date,
        "total_records": len(attendance_list),
        "present_count": present_count,
        "absent_count": len(attendance_list) - present_count,
        "records": attendance_list
    }

@router.post("/esp32/attendance/bulk")
def log_bulk_attendance(
    data: AttendanceBulkRequest,
    db: Session = Depends(get_db)
):
    """
    Bulk attendance upload from ESP32 SD card.

    Logic:
    - Same as single attendance API
    - Optimized for 100s of logs
    - Single DB commit
    """

    try:
        logs = data.logs

        if not logs:
            return {"success": True, "message": "No logs received", "processed": 0}

        # Preload existing records for optimization
        user_date_pairs = {(log.id, log.date) for log in logs}

        existing_records = db.query(AttendanceRecordDB).filter(
            tuple_(
                AttendanceRecordDB.user_id,
                AttendanceRecordDB.date
            ).in_(user_date_pairs)
        ).all()

        # Convert to lookup dictionary
        record_map = {
            (r.user_id, r.date): r for r in existing_records
        }

        created = 0
        updated = 0

        for log in logs:
            key = (log.id, log.date)

            if key in record_map:
                # Update checkout time
                record = record_map[key]
                record.checked_out_time = log.time
                record.updated_at = datetime.now()
                updated += 1
            else:
                # First log of the day
                new_record = AttendanceRecordDB(
                    name=log.name,
                    user_id=log.id,
                    date=log.date,
                    checked_in_time=log.time,
                    checked_out_time=None,
                    is_present=True
                )
                db.add(new_record)
                record_map[key] = new_record
                created += 1

        db.commit()

        return {
            "success": True,
            "message": "Bulk attendance processed successfully",
            "total_logs": len(logs),
            "created_records": created,
            "updated_records": updated
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Bulk attendance logging error: {str(e)}"
        )
    

# ==================== TRIGGER ENDPOINT ====================
@router.post("/esp32/trigger-attendance-sync", response_model=TriggerAttendanceSyncResponse)
def trigger_attendance_sync(
    data: TriggerAttendanceSyncRequest,
    db: Session = Depends(get_db)
):
    """
    POST endpoint to trigger N-days attendance sync on ESP32
    
    Frontend calls this endpoint to request ESP32 to upload
    attendance logs from the last N days.
    
    The trigger is stored in database, and ESP32 polls for it.
    """
    try:
        # Store the trigger request in a sync_triggers table
        trigger = AttendanceSyncTriggerDB(
            device_id=data.device_id,
            days_to_sync=data.days,
            status="pending",
            triggered_at=datetime.now()
        )
        
        db.add(trigger)
        db.commit()
        db.refresh(trigger)
        
        return TriggerAttendanceSyncResponse(
            success=True,
            message=f"Sync trigger sent to {data.device_id} for last {data.days} days",
            device_id=data.device_id,
            days_requested=data.days,
            trigger_timestamp=trigger.triggered_at
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Trigger error: {str(e)}")
    
@router.get("/esp32/check-sync-trigger/{device_id}", response_model=SyncTriggerCheck)
def check_sync_trigger(
    device_id: str,
    db: Session = Depends(get_db)
):
    """
    GET endpoint for ESP32 to check if there's a pending sync trigger
    
    ESP32 polls this endpoint every 30 seconds to see if frontend
    has requested an N-days sync.
    """
    # Find the latest pending trigger for this device
    trigger = db.query(AttendanceSyncTriggerDB).filter_by(
        device_id=device_id,
        status="pending"
    ).order_by(
        AttendanceSyncTriggerDB.triggered_at.desc()
    ).first()
    
    if trigger:
        return SyncTriggerCheck(
            has_trigger=True,
            days_to_sync=trigger.days_to_sync,
            trigger_id=trigger.id,
            message=f"Sync requested for last {trigger.days_to_sync} days"
        )
    else:
        return SyncTriggerCheck(
            has_trigger=False,
            days_to_sync=0,
            trigger_id=0,
            message="No pending sync triggers"
        )
    
@router.post("/esp32/complete-sync-trigger", response_model=CompleteSyncTriggerResponse)
def complete_sync_trigger(
    data: CompleteSyncTriggerRequest,
    db: Session = Depends(get_db)
):
    """
    POST endpoint for ESP32 to report sync completion
    
    ESP32 calls this after executing the triggered sync to update status
    """
    try:
        trigger = db.query(AttendanceSyncTriggerDB).filter_by(
            id=data.trigger_id
        ).first()
        
        if not trigger:
            raise HTTPException(status_code=404, detail="Trigger not found")
        
        # Update trigger status
        trigger.status = "completed" if data.success else "failed"
        trigger.completed_at = datetime.now()
        trigger.logs_synced = data.logs_synced
        trigger.error_message = data.error_message if not data.success else None
        
        db.commit()
        
        return CompleteSyncTriggerResponse(
            success=True,
            message=f"Trigger {data.trigger_id} marked as {trigger.status}"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Completion error: {str(e)}")