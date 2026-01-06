# app/models/content.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    is_published = Column(Boolean, default=False)
    rating_avg = Column(Float, default=0.0)
    origin_type = Column(String, default="generated") # manual / generated

    topics = relationship("Topic", back_populates="course")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String, nullable=False)
    order = Column(Integer, default=0)

    course = relationship("Course", back_populates="topics")
    units = relationship("ContentUnit", back_populates="topic")

class ContentUnit(Base):
    __tablename__ = "content_units"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    type = Column(String, nullable=False) # lecture / task
    order_index = Column(Integer, default=0)
    is_hidden = Column(Boolean, default=False)

    topic = relationship("Topic", back_populates="units")
    # Используем uselist=False для связи 1-к-1
    lecture = relationship("Lecture", back_populates="unit", uselist=False)
    task = relationship("Task", back_populates="unit", uselist=False)

class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("content_units.id"), unique=True, nullable=False)
    content_md = Column(Text, nullable=False) # Markdown текст
    
    # Статус генерации озвучки
    tts_status = Column(String, default="none") # none, pending, ready, failed
    audio_file_id = Column(Integer, ForeignKey("files.id"), nullable=True)

    unit = relationship("ContentUnit", back_populates="lecture")
    audio = relationship("File") # Чтобы подтянуть ссылку на файл, если нужно

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("content_units.id"), unique=True, nullable=False)
    type = Column(String, default="quiz") # quiz / code / open
    
    # JSONB идеален для Postgres (храним структуру вопроса и валидацию)
    content = Column(JSONB, nullable=False) # {question: "...", options: []}
    validation = Column(JSONB, nullable=False) # {correct_answer: "A"}

    unit = relationship("ContentUnit", back_populates="task")