from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import db_helper
from app.models.content import Topic, Course
from app.models.user import User
from app.core.utils import get_current_user  

router = APIRouter(prefix="/topics", tags=["topics"])

@router.get("/")
async def get_topics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(db_helper.session_getter)
):
    """Получить список опубликованных топиков с названиями курсов"""
    stmt = (
        select(Topic)
        .join(Course)
        .where(Course.is_published == True)
        .order_by(Course.title, Topic.order)
    )
    result = await session.execute(stmt)
    topics = result.scalars().all()
    
    return [
        {
            "id": topic.id,
            "title": topic.title,
            "course_id": topic.course_id,
            "course_title": topic.course.title if topic.course else "Без курса"
        }
        for topic in topics
    ]