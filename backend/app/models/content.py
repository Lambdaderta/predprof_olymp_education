# app/models/content.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import Base
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    is_published = Column(Boolean, default=False)
    rating_avg = Column(Float, default=0.0)
    origin_type = Column(String, default="generated") # manual / generated

    source_type = Column(String, default="user_generated")  # "user_generated", "pdf_upload", "request"
    source_data = Column(JSONB, nullable=True)  # оригинальные данные запроса
    is_verified = Column(Boolean, default=False)  # проверенный админом
    embedding = Column(Vector(1536), nullable=True)  # для векторного поиска
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # кто создал курс
    rating_count = Column(Integer, default=0)  # количество оценок (вместо rating_avg который уже есть)

    # Связи
    creator = relationship("User", foreign_keys=[created_by])

    topics = relationship("Topic", back_populates="course")

    def __str__(self):
        return self.title

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String, nullable=False)
    order = Column(Integer, default=0)

    course = relationship("Course", back_populates="topics")
    units = relationship("ContentUnit", back_populates="topic")

    def __str__(self):
        return f"{self.title} (Курс: {self.course_id})"

class ContentUnit(Base):
    __tablename__ = "content_units"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    type = Column(String, nullable=False) # lecture / task / exam
    order_index = Column(Integer, default=0)
    is_hidden = Column(Boolean, default=False)

    topic = relationship("Topic", back_populates="units")
    
    # 1. ЛЕКЦИЯ (Остается 1-к-1, uselist=False)
    lecture = relationship("Lecture", back_populates="unit", uselist=False)
    
    # 2. ЗАДАЧИ (Стало 1-ко-Многим, убираем uselist=False и переименовываем в tasks)
    # Было: task = relationship("Task", back_populates="unit", uselist=False)
    # Стало:
    tasks = relationship("Task", back_populates="unit") 

    def __str__(self):
        return f"{self.topic_id} (Тип: {self.type})"


class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("content_units.id"), unique=True, nullable=False)
    content_md = Column(Text, nullable=False)
    lecture_name = Column(Text, nullable=False, default="Без названия")
    tts_status = Column(String, default="none")
    audio_file_id = Column(Integer, ForeignKey("files.id"), nullable=True)

    unit = relationship("ContentUnit", back_populates="lecture")
    audio = relationship("File")

    # 3. Добавляем связь Лекции с задачами
    tasks = relationship("Task", back_populates="lecture")

    def __str__(self):
        return f"{self.lecture_name}"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    
    # 4. Юнит теперь не уникален (unique=False) и может быть пустым (nullable=True)
    unit_id = Column(Integer, ForeignKey("content_units.id"), unique=False, nullable=True)
    
    # 5. Ссылка на лекцию
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=True)

    type = Column(String, default="quiz")
    content = Column(JSONB, nullable=False)
    validation = Column(JSONB, nullable=False)

    difficulty = Column(Integer, default=1)
    explanation = Column(Text, nullable=True) 
    tags = Column(ARRAY(String), nullable=True)
    requires_ai_check = Column(Boolean, default=False)
    file_upload_allowed = Column(Boolean, default=False)

    # 6. Связи (Обрати внимание на back_populates)
    # Здесь "tasks" (множественное число), значит в ContentUnit должно быть поле tasks
    unit = relationship("ContentUnit", back_populates="tasks") 
    
    # Здесь "tasks", значит в Lecture должно быть поле tasks
    lecture = relationship("Lecture", back_populates="tasks")
    def __str__(self):
        return f"{self.content}"