# app/api/v1/routes/courses.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import db_helper
from app.api.v1.routes.auth import get_current_user 
from app.models.user import User
from app.models.content import Course, Topic, ContentUnit, Lecture, Task
from app.models.learning import UserTaskProgress 
from app.core.schemas.content import CourseSummary, CourseDetail, LectureSchema, TaskSchema

router = APIRouter(prefix="/courses", tags=["courses"])

router = APIRouter(prefix="/courses", tags=["courses"])

@router.get("/", response_model=list[CourseSummary])
async def get_courses(
    session: AsyncSession = Depends(db_helper.session_getter)
):
    stmt = select(Course).where(Course.is_published == True)
    result = await session.execute(stmt)
    courses = result.scalars().all()
    return courses

@router.get("/{course_id}", response_model=CourseDetail)
async def get_course_details(
    course_id: int,
    session: AsyncSession = Depends(db_helper.session_getter),
    current_user: User = Depends(get_current_user) # Теперь нам нужен юзер!
):
    # 1. Загружаем курс (код тот же)
    stmt = (
        select(Course)
        .where(Course.id == course_id)
        .options(
            selectinload(Course.topics)
            .selectinload(Topic.units)
            .options(
                selectinload(ContentUnit.tasks),
                selectinload(ContentUnit.lecture).selectinload(Lecture.tasks)
            )
        )
    )
    result = await session.execute(stmt)
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 2. ЗАГРУЖАЕМ ПРОГРЕСС ПОЛЬЗОВАТЕЛЯ
    # Ищем все решенные задачи этого юзера
    progress_stmt = select(UserTaskProgress.task_id).where(
        UserTaskProgress.user_id == current_user.id,
        UserTaskProgress.is_correct == True
    )
    progress_result = await session.execute(progress_stmt)
    solved_task_ids = set(progress_result.scalars().all()) # Множество ID решенных задач

    lectures_list = []
    sorted_topics = sorted(course.topics, key=lambda t: t.order)
    
    for topic in sorted_topics:
        sorted_units = sorted(topic.units, key=lambda u: u.order_index)
        for unit in sorted_units:
            
            # Логика сбора задач (как была раньше)
            if unit.type == 'lecture' and unit.lecture:
                unique_tasks_map = {}
                for t in unit.lecture.tasks: unique_tasks_map[t.id] = t
                for t in unit.tasks: unique_tasks_map[t.id] = t
                
                raw_tasks = list(unique_tasks_map.values())
                
                tasks_data = [
                    TaskSchema(
                        id=t.id,
                        type=t.type,
                        question=t.content.get("question", ""),
                        options=t.content.get("options", []),
                        correctAnswer=t.validation.get("correct_answer"),
                        explanation=t.explanation,
                        
                        # ПРОВЕРЯЕМ, РЕШЕНА ЛИ ЗАДАЧА
                        is_solved=(t.id in solved_task_ids) 
                    ) for t in raw_tasks
                ]

                lectures_list.append(LectureSchema(
                    id=unit.lecture.id,
                    title=f"{topic.title}", 
                    lecture_name=unit.lecture.lecture_name, # <-- ТВОЕ НОВОЕ ПОЛЕ
                    content=unit.lecture.content_md,
                    completed=(len(tasks_data) > 0 and all(t.is_solved for t in tasks_data)), # Лекция пройдена, если все задачи решены
                    score=0,
                    tasks=tasks_data
                ))

            elif unit.tasks:
                tasks_data = [
                    TaskSchema(
                        id=t.id,
                        type=t.type,
                        question=t.content.get("question", ""),
                        options=t.content.get("options", []),
                        correctAnswer=t.validation.get("correct_answer"),
                        explanation=t.explanation,
                        is_solved=(t.id in solved_task_ids)
                    ) for t in unit.tasks
                ]
                
                lectures_list.append(LectureSchema(
                    id=unit.id * 10000,
                    title=f"Практика: {topic.title}",
                    lecture_name=f"Практика: {topic.title}", # Заглушка для экзаменов
                    content="Задания для закрепления.",
                    completed=all(t.is_solved for t in tasks_data),
                    score=0,
                    tasks=tasks_data
                ))

    return CourseDetail(
        id=course.id,
        title=course.title,
        description=course.description,
        rating_avg=course.rating_avg,
        lectures=lectures_list
    )

# --- НОВЫЙ ЭНДПОИНТ: СОХРАНЕНИЕ ОТВЕТА ---
@router.post("/tasks/{task_id}/solve")
async def solve_task(
    task_id: int,
    answer_data: dict = Body(...), # { "answer": "...", "is_correct": true }
    session: AsyncSession = Depends(db_helper.session_getter),
    current_user: User = Depends(get_current_user)
):
    is_correct = answer_data.get("is_correct", False)
    user_answer = str(answer_data.get("answer", ""))

    # Сохраняем прогресс
    # Можно использовать upsert, но для простоты добавим запись
    # Если нужно хранить только последний ответ - сначала удали старый или обнови
    
    # Проверим, решал ли уже (чтобы не дублировать успешные решения)
    stmt = select(UserTaskProgress).where(
        UserTaskProgress.user_id == current_user.id,
        UserTaskProgress.task_id == task_id
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.is_correct = is_correct
        existing.user_answer = user_answer
        # existing.solved_at = func.now() # Можно обновить время
    else:
        new_progress = UserTaskProgress(
            user_id=current_user.id,
            task_id=task_id,
            is_correct=is_correct,
            user_answer=user_answer
        )
        session.add(new_progress)
    
    await session.commit()
    return {"status": "success"}