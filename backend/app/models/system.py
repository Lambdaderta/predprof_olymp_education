# app/models/system.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func, Text
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base

class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type = Column(String, nullable=False) # gen_tts, gen_course, ai_check
    status = Column(String, default="pending") # pending, processing, done, error
    
    payload = Column(JSONB) # Входные данные для RunPod
    result = Column(JSONB)  # Ответ от RunPod
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, default="info") # info, success, warning
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())