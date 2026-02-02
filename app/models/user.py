from sqlalchemy import Column, Integer, String, DateTime,Numeric
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
from app.core.database import Base

class UserInformationDB(Base):
    __tablename__ = "user_information"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    slot_id = Column(ARRAY(Integer), nullable=False)  
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    salary = Column(Numeric, nullable=True, default=None)
    created_at = Column(DateTime, default=datetime.now)

class AdminInformationDB(Base):
    __tablename__ = "admin_information"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False) # Plain text for now as requested
    role = Column(String, default="ADMIN")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)