# app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime, func, BigInteger, ForeignKey, Boolean, Enum as PyEnum
from sqlalchemy.orm import relationship
import enum
from .base import Base

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

class UserPlan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False) 
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)
    role = Column(String, default="user") 
    avatar_url = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    limits = relationship("UserLimits", back_populates="user", uselist=False)
    stats = relationship("UserStats", back_populates="user", uselist=False)
    enrollments = relationship("Enrollment", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

class UserLimits(Base):
    __tablename__ = "user_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    plan = Column(String, default="free") 
    daily_generations_left = Column(Integer, default=5)
    reset_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="limits")