from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import db_helper
from app.models.content import Topic, Course

router = APIRouter(prefix="/topics", tags=["topics"])

@router.get("/")
async def get_topics(
    limit: int = Query(50, ge=1, le=100),
    course_id: int = Query(None, description="Фильтр по курсу"),
    session: AsyncSession = Depends(db_helper.session_getter)
):
    """Получить список тем (топиков) с опциональной фильтрацией по курсу"""
    stmt = select(Topic).join(Topic.course).where(Course.is_published == True)
    
    if course_id:
        stmt = stmt.where(Topic.course_id == course_id)
    
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    topics = result.scalars().all()
    
    return {
        "items": [
            {
                "id": t.id,
                "name": t.title,
                "course_id": t.course_id,
                "course_title": t.course.title if t.course else None
            } 
            for t in topics
        ],
        "total": len(topics)
    }