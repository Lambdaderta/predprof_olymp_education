# app/models/engagement.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from .base import Base

class UserStats(Base):
    __tablename__ = "user_stats"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    total_xp = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    max_streak = Column(Integer, default=0)
    problems_solved = Column(Integer, default=0)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="stats")

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True) 
    title = Column(String, nullable=False)
    description = Column(String)
    icon_url = Column(String)
    xp_reward = Column(Integer, default=10)

class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement")