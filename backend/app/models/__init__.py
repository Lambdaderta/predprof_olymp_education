# app/models/__init__.py
from .base import Base
from .user import User, UserLimits, UserRole
from .media import File
from .engagement import UserStats, Achievement, UserAchievement
from .content import Course, Topic, ContentUnit, Lecture, Task
from .learning import Enrollment, KnowledgeGraph, LearningSession, ChatMessage
from .system import BackgroundJob, Notification

# Этот список нужен, чтобы IDE и инструменты видели, что экспортируется
__all__ = [
    "Base",
    "User", "UserLimits", "UserRole",
    "File",
    "UserStats", "Achievement", "UserAchievement",
    "Course", "Topic", "ContentUnit", "Lecture", "Task",
    "Enrollment", "KnowledgeGraph", "LearningSession", "ChatMessage",
    "BackgroundJob", "Notification",
]