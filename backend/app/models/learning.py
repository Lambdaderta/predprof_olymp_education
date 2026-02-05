# app/models/learning.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
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


class SolutionAnalysis(Base):
    """Анализ фото решений от пользователей"""
    __tablename__ = "solution_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    image_file_id = Column(Integer, ForeignKey("files.id"), nullable=False)  # фото решения
    analysis_result = Column(JSONB, nullable=True)  # результат анализа ИИ
    status = Column(String, default="pending")  # "pending", "completed", "error"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Связи
    user = relationship("User")
    task = relationship("Task")
    image_file = relationship("File")


class LearningPlan(Base):
    """Персональные планы обучения для пользователей"""
    __tablename__ = "learning_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)  # название плана
    description = Column(Text, nullable=True)  # описание плана
    courses = Column(JSONB, nullable=False)  # [{"course_id": 1, "order": 1, "reason": "..."}, ...]
    is_active = Column(Boolean, default=True)  # активен ли план
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Связь
    user = relationship("User")

class UserTaskProgress(Base):
    __tablename__ = "user_task_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    
    is_correct = Column(Boolean, default=False)
    user_answer = Column(Text, nullable=True) 
    
    solved_at = Column(DateTime(timezone=True), server_default=func.now())
    