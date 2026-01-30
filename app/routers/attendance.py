from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import tuple_
from datetime import datetime

from app.core.database import get_db
from app.models.attendance import AttendanceRecordDB
from app.schemas.attendance import (AttendanceLogRequest,AttendanceLogResponse,AttendanceBulkRequest)

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