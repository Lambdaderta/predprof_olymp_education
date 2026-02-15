# app/api/v1/routes/courses.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import httpx
from app.core.database import db_helper
from app.api.v1.routes.auth import get_current_user 
import re
import logging
import json as json_lib
from app.models.user import User
from app.models.content import Course, Topic, ContentUnit, Lecture, Task
from app.models.learning import UserTaskProgress 
from app.core.schemas.content import CourseSummary, CourseDetail, LectureSchema, TaskSchema

logger = logging.getLogger(__name__)


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


@router.post("/tasks/{task_id}/generate-similar")
async def generate_similar_task(
    task_id: int,
    session: AsyncSession = Depends(db_helper.session_getter),
    current_user: User = Depends(get_current_user)
):
    # 1. Получаем оригинальную задачу
    stmt = select(Task).where(Task.id == task_id)
    result = await session.execute(stmt)
    original_task = result.scalar_one_or_none()
    
    if not original_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 2. Формируем промпт для модели (улучшенная инструкция)
    question = original_task.content.get("question", "")
    correct_answer = original_task.validation.get("correct_answer", "")
    explanation = original_task.explanation or ""
    difficulty = original_task.difficulty or 1
    
    prompt = f"""Ты — преподаватель олимпиадной математики. Создай НОВУЮ задачу, аналогичную приведённой ниже.

### Оригинальная задача:
Тип: {original_task.type}
Уровень сложности: {difficulty}
Вопрос: {question}
Правильный ответ: {correct_answer}
Объяснение: {explanation}

### Требования:
1. Сохрани структуру доказательства и логику решения
2. Измени числовые параметры и контекст (имена, объекты)
3. Задача должна быть корректной и иметь однозначное решение
4. Объяснение должно содержать пошаговое доказательство
5. Уровень сложности должен остаться таким же

### КРИТИЧЕСКИ ВАЖНО:
- Верни ТОЛЬКО ЧИСТЫЙ ВАЛИДНЫЙ JSON БЕЗ КАКИХ-ЛИБО ДОПОЛНИТЕЛЬНЫХ СИМВОЛОВ
- НЕ ИСПОЛЬЗУЙ markdown (```, ```json)
- НЕ ДОБАВЛЯЙ комментарии, префиксы, постфиксы
- Используй ТОЛЬКО двойные кавычки для строк
- Экранируй спецсимволы правильно (\\n, \\t и т.д.)

### Формат ответа (ТОЛЬКО ЭТОТ JSON):
{{
  "question": "Новый вопрос...",
  "correct_answer": "Новый ответ",
  "explanation": "Новое объяснение..."
}}"""

    # 3. Отправляем запрос на локальный LLM сервер
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post( 
                "http://llm-server:8000/v1/chat/completions",
                json={
                    "model": "Qwen3-4B-Instruct-2507-Q4_K_M",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                logger.error(f"LLM server error {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"LLM server error: {response.status_code}"
                )
            
            # 4. ПАРСИНГ С ЗАЩИТОЙ ОТ ГРЯЗНОГО JSON (улучшенная версия)
            llm_response = response.json()
            raw_text = llm_response["choices"][0]["message"]["content"].strip()
            
            # Шаг 1: Удаляем все блоки кода ``` ... ```
            cleaned = re.sub(r'^```(?:json|python|javascript)?\s*', '', raw_text, flags=re.MULTILINE)
            cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()
            
            # Шаг 2: Находим границы JSON объекта (первая {{ и последняя }})
            start_idx = cleaned.find('{')
            end_idx = cleaned.rfind('}')
            
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                logger.error(f"❌ Не найдены границы JSON. Первые 500 символов ответа:\n{cleaned[:500]}")
                raise ValueError("Не удалось найти структуру JSON в ответе модели")
            
            json_candidate = cleaned[start_idx:end_idx + 1]
            
            # Шаг 3: Пробуем распарсить с несколькими стратегиями восстановления
            parsed = None
            strategies = [
                ("original", json_candidate),
                ("fix_single_quotes", json_candidate.replace("'", '"')),
                ("fix_trailing_commas", re.sub(r',\s*([}\]])', r'\1', json_candidate)),
                ("fix_newlines_in_strings", re.sub(r'(?<!\\)\\n', r'\\\\n', json_candidate)),  # Экранируем \n внутри строк
            ]
            
            for strategy_name, candidate in strategies:
                try:
                    parsed = json_lib.loads(candidate)
                    logger.info(f"✅ JSON успешно распарсен стратегией: {strategy_name}")
                    break
                except json_lib.JSONDecodeError as e:
                    logger.debug(f"Стратегия {strategy_name} не сработала: {str(e)[:100]}")
                    continue
            
            if parsed is None:
                # Финальная попытка: удаляем все не-JSON символы с краёв
                candidate = re.sub(r'^[^{]*', '', json_candidate)
                candidate = re.sub(r'[^}]*$', '', candidate)
                try:
                    parsed = json_lib.loads(candidate)
                except Exception as e:
                    logger.error(f"❌ Все стратегии парсинга провалились. Оригинальный ответ (первые 1000 символов):\n{raw_text[:1000]}")
                    logger.error(f"Очищенный кандидат (первые 1000 символов):\n{json_candidate[:1000]}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Не удалось распарсить JSON от модели. Ошибка: {str(e)}"
                    )
            
            generated_data = parsed
            logger.info(f"✅ Успешно сгенерирована задача: {generated_data.get('question', '')[:60]}...")
            
    except httpx.TimeoutException:
        logger.error("LLM server timeout after 300 seconds")
        raise HTTPException(
            status_code=500,
            detail="Generation timeout. Model is slow or overloaded."
        )
    except Exception as e:
        logger.error(f"❌ Ошибка генерации задачи: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Generation failed: {str(e)[:150]}"
        )
    
    # 5. Валидация ответа модели
    required_fields = ["question", "correct_answer", "explanation"]
    missing = [f for f in required_fields if f not in generated_data]
    if missing:
        logger.error(f"❌ Отсутствуют обязательные поля: {missing}. Полученные ключи: {list(generated_data.keys())}")
        logger.error(f"Полный ответ модели: {generated_data}")
        raise HTTPException(
            status_code=500, 
            detail=f"Model response missing fields: {', '.join(missing)}"
        )
    
    # 6. Создаем новую задачу
    new_task = Task(
        unit_id=original_task.unit_id,
        lecture_id=original_task.lecture_id,
        type=original_task.type,
        content={
            "question": str(generated_data["question"]).strip()
        },
        validation={
            "correct_answer": str(generated_data["correct_answer"]).strip()
        },
        explanation=str(generated_data["explanation"]).strip(),
        difficulty=original_task.difficulty,
        tags=original_task.tags,
        requires_ai_check=original_task.requires_ai_check,
        file_upload_allowed=original_task.file_upload_allowed
    )
    
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    
    # 7. Возвращаем новую задачу
    return {
        "id": new_task.id,
        "type": new_task.type,
        "question": new_task.content.get("question", ""),
        "options": new_task.content.get("options", []),
        "correctAnswer": new_task.validation.get("correct_answer"),
        "explanation": new_task.explanation,
        "is_solved": False
    }