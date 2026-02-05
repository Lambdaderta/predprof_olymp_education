# app/models/pvp.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import Base

class PVPMatch(Base):
    __tablename__ = "pvp_matches"

    id = Column(Integer, primary_key=True, index=True)
    
    # Игроки
    player1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    player2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Счет
    player1_score = Column(Integer, default=0)
    player2_score = Column(Integer, default=0)
    
    # Рейтинги до матча
    player1_rating_before = Column(Integer, nullable=False)
    player2_rating_before = Column(Integer, nullable=False)
    
    # Рейтинги после матча (может быть NULL если матч отменен)
    player1_rating_after = Column(Integer, nullable=True)
    player2_rating_after = Column(Integer, nullable=True)
    
    # Статус матча
    status = Column(String, default="active")  # active, finished, cancelled, error
    
    # Результат (вычисляется по счету)
    result = Column(String, nullable=True)  # player1_win, player2_win, draw
    
    # Задачи в матче (для анализа)
    tasks_used = Column(JSONB, nullable=True)
    
    # Время
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    # Причина отмены (если есть)
    cancellation_reason = Column(String, nullable=True)
    
    # Связи
    player1 = relationship("User", foreign_keys=[player1_id])
    player2 = relationship("User", foreign_keys=[player2_id])