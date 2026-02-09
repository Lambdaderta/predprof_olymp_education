from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import db_helper
from app.models.content import Task, ContentUnit, Lecture

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/count")
async def get_task_count(
    topic_id: int = Query(None, description="ID темы для фильтрации"),
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """Получить количество доступных задач с фильтрацией по теме"""
    conditions = [
        Task.validation.is_not(None),
        Task.validation["correct_answer"].astext.is_not(None),
        Task.validation["correct_answer"].astext != ""
    ]
    
    if topic_id is None:
        stmt = select(func.count(Task.id)).where(*conditions)
    else:
        stmt_direct = (
            select(func.count(Task.id))
            .join(Task.unit)
            .where(
                ContentUnit.topic_id == topic_id,
                ContentUnit.type == "task",
                *conditions
            )
        )
        
        stmt_via_lecture = (
            select(func.count(Task.id))
            .join(Task.lecture)
            .join(Lecture.unit)
            .where(
                ContentUnit.topic_id == topic_id,
                ContentUnit.type == "lecture",
                *conditions
            )
        )
        
        count_direct = (await session.execute(stmt_direct)).scalar() or 0
        count_via_lecture = (await session.execute(stmt_via_lecture)).scalar() or 0
        total = count_direct + count_via_lecture
        return {"total": total}
    
    total = (await session.execute(stmt)).scalar() or 0
    return {"total": total}