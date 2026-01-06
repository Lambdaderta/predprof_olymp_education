# app/models/learning.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import relationship
from .base import Base

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    status = Column(String, default="active") # active / completed / dropped
    started_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course")

class KnowledgeGraph(Base):
    __tablename__ = "knowledge_graph"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    mastery = Column(Integer, default=0) # 0-100%
    status = Column(String, default="locked") # locked, open, passed

class LearningSession(Base):
    """
    Контекст чата по конкретной задаче
    """
    __tablename__ = "learning_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("content_units.id"), nullable=False)
    status = Column(String, default="active") # active, closed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id"), nullable=False)
    role = Column(String, nullable=False) # user / ai
    content = Column(Text, nullable=False)
    
    # Если юзер скинул фото (для Serverless Vision)
    image_file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("LearningSession", back_populates="messages")