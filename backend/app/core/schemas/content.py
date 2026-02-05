# app/core/schemas/content.py
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any, Dict

# --- Schemas для списка курсов ---
class CourseSummary(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    level: str = "Средний" # Заглушка, т.к. в БД пока нет поля level
    progress: int = 0      # Заглушка, пока не считаем реальный прогресс
    rating_avg: float
    
    model_config = ConfigDict(from_attributes=True)

# --- Schemas для деталей курса ---

class TaskSchema(BaseModel):
    id: int
    type: str
    question: str
    options: List[str] = []
    correctAnswer: Any = None
    explanation: Optional[str] = None
    
    is_solved: bool = False 
    
    model_config = ConfigDict(from_attributes=True)

class LectureSchema(BaseModel):
    id: int
    title: str
    content: str
    completed: bool = False
    score: int = 0
    tasks: List[TaskSchema] = []
    lecture_name: str

    model_config = ConfigDict(from_attributes=True)

class CourseDetail(CourseSummary):
    lectures: List[LectureSchema] = []