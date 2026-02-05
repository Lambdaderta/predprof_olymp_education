# app/core/admin.py
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from fastapi import Request
from starlette.responses import RedirectResponse
from app.core.security import verify_password, create_access_token # Предполагаю, что они есть в security.py
from app.core.config import settings
from app.repositories.user_repository import UserRepository
from app.core.database import db_helper
from app.models.user import User
from app.models.content import Course, Topic, ContentUnit, Lecture, Task
from app.models.learning import Enrollment

# 1. Настройка авторизации в админке
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email, password = form["username"], form["password"]

        async with db_helper.session_factory() as session:
            user_repo = UserRepository(session)
            # Т.к. репозиторий может не иметь метода get_by_email_with_password, 
            # используем базовый запрос (адаптируй под свой репозиторий если нужно)
            from sqlalchemy import select
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            # Проверяем пароль и роль
            # ВНИМАНИЕ: verify_password должен быть импортирован из app.core.security
            if user and verify_password(password, user.password_hash):
                if user.role == "admin":
                    request.session.update({"token": "admin_token"}) # В реальном проекте тут JWT
                    return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        return True

authentication_backend = AdminAuth(secret_key=settings.security.JWT_SECRET_KEY.get_secret_value())

# 2. Представления моделей (Views)

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.role, User.created_at]
    column_searchable_list = [User.email]
    column_sortable_list = [User.id, User.created_at]
    icon = "fa-solid fa-user"

class CourseAdmin(ModelView, model=Course):
    column_list = [Course.id, Course.title, Course.is_published, Course.rating_avg]
    column_searchable_list = [Course.title]
    form_excluded_columns = [Course.embedding, Course.source_data, Course.topics, Course.creator]
    icon = "fa-solid fa-graduation-cap"

class TopicAdmin(ModelView, model=Topic):
    column_list = [Topic.id, Topic.title, Topic.course]
    form_columns = [Topic.course, Topic.title, Topic.order] # Явно указываем, что заполнять
    icon = "fa-solid fa-list"

class ContentUnitAdmin(ModelView, model=ContentUnit):
    column_list = [ContentUnit.id, ContentUnit.type, ContentUnit.topic, ContentUnit.is_hidden]
    
    form_columns = [ContentUnit.topic, ContentUnit.type, ContentUnit.order_index, ContentUnit.is_hidden]
    
    icon = "fa-solid fa-box"

class LectureAdmin(ModelView, model=Lecture):
    column_list = [Lecture.id, Lecture.unit]
    
    # При создании лекции мы выбираем существующий Юнит
    form_columns = [Lecture.unit, Lecture.content_md, Lecture.tts_status, Lecture.lecture_name]
    
    icon = "fa-solid fa-book-open"

class TaskAdmin(ModelView, model=Task):
    column_list = [Task.id, Task.type, Task.lecture]
    
    # При создании задачи мы выбираем существующий Юнит
    form_columns = [Task.unit, Task.lecture, Task.type, Task.content, Task.validation, Task.difficulty, Task.explanation]
    
    icon = "fa-solid fa-pen-to-square"

class EnrollmentAdmin(ModelView, model=Enrollment):
    column_list = [Enrollment.id, Enrollment.user, Enrollment.course, Enrollment.status]
    icon = "fa-solid fa-users-rectangle"

# 3. Функция инициализации
def setup_admin(app, engine):
    admin = Admin(app, engine, authentication_backend=authentication_backend, title="EduMind Admin")
    
    admin.add_view(UserAdmin)
    admin.add_view(CourseAdmin)
    admin.add_view(TopicAdmin)
    admin.add_view(ContentUnitAdmin)
    admin.add_view(LectureAdmin)
    admin.add_view(TaskAdmin)
    admin.add_view(EnrollmentAdmin)