from sqlalchemy import select, func, join
from app.models.content import Task, ContentUnit  # ← Добавьте импорт ContentUnit
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import db_helper
from app.models.content import Topic, Course
from app.models.user import User
from app.core.utils import get_current_user  


router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/count")
async def get_tasks_count(
    topic_id: int | None = None,  # ← Теперь по топику
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(db_helper.session_getter)
):
    """Получить количество задач по топику (или общее)"""
    stmt = select(func.count(Task.id)).where(
        Task.validation.is_not(None),
        Task.validation["correct_answer"].astext.is_not(None)
    )
    
    # 🔑 Фильтрация по топику через ContentUnit
    if topic_id is not None:
        stmt = stmt.join(ContentUnit).where(ContentUnit.topic_id == topic_id)
    
    result = await session.execute(stmt)
    total = result.scalar() or 0
    
    return {
        "total": total,
        "topic_id": topic_id,
        "available": total,
        "message": f"Доступно {total} задач" + (f" по топику ID {topic_id}" if topic_id else "")
    }