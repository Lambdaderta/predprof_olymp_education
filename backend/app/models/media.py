# app/models/media.py
from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger
from .base import Base

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) 
    s3_key = Column(String, nullable=False) 
    url = Column(String, nullable=False)    # Полная публичная ссылка
    type = Column(String, nullable=False)   # image / audio
    size = Column(BigInteger, nullable=True) # Размер 