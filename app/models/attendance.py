from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
from app.core.database import Base

class AttendanceRecordDB(Base):
    __tablename__ = "attendance_records"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    slot_id = Column(ARRAY(Integer), nullable=False)  # Added slot_id as array
    date = Column(String, nullable=False, index=True)
    checked_in_time = Column(String, nullable=True)
    checked_out_time = Column(String, nullable=True)
    is_present = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class AttendanceSyncTriggerDB(Base):
    __tablename__ = "attendance_sync_triggers"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, nullable=False, index=True)
    days_to_sync = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # 'pending', 'completed', 'failed'
    triggered_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    logs_synced = Column(Integer, default=0)
    error_message = Column(String, nullable=True)