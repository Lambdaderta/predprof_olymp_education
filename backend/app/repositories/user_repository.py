# app/repositories/user_repository.py
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserLimits
from app.core.schemas.auth import UserCreate

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Получить пользователя по email"""
        stmt = select(User).where(func.lower(User.email) == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(self, user_create: UserCreate, password_hash: str) -> User:
        """Создать нового пользователя"""
        # Создаем пользователя
        db_user = User(
            email=user_create.email.lower(),
            password_hash=password_hash,
            telegram_id=user_create.telegram_id,
            role="user",  # По умолчанию обычный пользователь
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.session.add(db_user)
        await self.session.flush()  # Получаем ID без коммита
        
        # Создаем лимиты для пользователя
        reset_at = datetime.now(timezone.utc) + timedelta(days=1)
        user_limits = UserLimits(
            user_id=db_user.id,
            plan="free",
            daily_generations_left=5,
            reset_at=reset_at
        )
        self.session.add(user_limits)
        
        await self.session.commit()
        await self.session.refresh(db_user)
        return db_user
    
    async def update_telegram_id(self, user_id: int, telegram_id: int) -> User:
        """Обновить Telegram ID пользователя"""
        stmt = update(User).where(User.id == user_id).values(
            telegram_id=telegram_id,
            updated_at=datetime.now(timezone.utc)
        ).returning(User)
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()
    
    async def update_password(self, user_id: int, new_password_hash: str) -> User:
        """Обновить пароль пользователя"""
        stmt = update(User).where(User.id == user_id).values(
            password_hash=new_password_hash,
            updated_at=datetime.now(timezone.utc)
        ).returning(User)
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()
    
    async def update_last_login(self, user_id: int) -> None:
        """Обновить время последнего входа"""
        stmt = update(User).where(User.id == user_id).values(
            last_login_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def get_user_with_limits(self, user_id: int) -> Optional[tuple[User, UserLimits]]:
        """Получить пользователя вместе с лимитами"""
        stmt = select(User, UserLimits).join(
            UserLimits, User.id == UserLimits.user_id
        ).where(User.id == user_id)
        
        result = await self.session.execute(stmt)
        return result.first()