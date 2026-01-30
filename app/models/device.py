from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base

class DeviceStatusDB(Base):
    __tablename__ = "device_status"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)