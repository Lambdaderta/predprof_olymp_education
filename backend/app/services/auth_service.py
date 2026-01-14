# app/services/auth_service.py
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.repositories.user_repository import UserRepository
from app.core.schemas.auth import (
    UserCreate,
    Token,
    RefreshTokenRequest
)
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    RateLimitError
)
from app.models.user import User
import time

class RateLimiter:
    """Простой rate limiter для защиты от брутфорса"""
    def __init__(self):
        self.attempts: Dict[str, list] = {}  # {ip_or_email: [timestamps]}
        self.max_attempts = 5
        self.block_duration = timedelta(minutes=15)  # 15 минут блокировки
        self.window = timedelta(minutes=5)  # окно для подсчета попыток
    
    async def check_rate_limit(self, identifier: str) -> None:
        """Проверка лимита запросов"""
        now = datetime.now(timezone.utc)
        
        # Очистка старых записей
        if identifier in self.attempts:
            self.attempts[identifier] = [
                ts for ts in self.attempts[identifier]
                if ts > now - self.window
            ]
        
        # Проверка на блокировку
        if identifier in self.attempts:
            attempts = self.attempts[identifier]
            if len(attempts) >= self.max_attempts:
                first_attempt = min(attempts)
                if now - first_attempt < self.block_duration:
                    remaining = (first_attempt + self.block_duration - now).seconds
                    raise RateLimitError(
                        f"Too many attempts. Try again in {remaining} seconds"
                    )
        
        # Добавление новой попытки
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        self.attempts[identifier].append(now)
    
    async def clear_attempts(self, identifier: str) -> None:
        """Очистка попыток после успешной аутентификации"""
        if identifier in self.attempts:
            del self.attempts[identifier]

class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.rate_limiter = RateLimiter()
    
    async def register_user(self, user_create: UserCreate, client_ip: str) -> Tuple[User, Token]:
        """Регистрация нового пользователя с защитой от брутфорса"""
        # Проверка rate limit по IP
        await self.rate_limiter.check_rate_limit(f"register_{client_ip}")
        
        try:
            # Проверяем существование пользователя по email
            existing_user = await self.user_repository.get_by_email(user_create.email)
            if existing_user:
                # Делаем задержку для защиты от перебора email
                time.sleep(1)  # Задержка для защиты от тайминг-атак
                raise ValidationError("User with this email already exists")
            
            # Проверяем Telegram ID, если указан
            if user_create.telegram_id:
                existing_telegram_user = await self.user_repository.get_by_telegram_id(user_create.telegram_id)
                if existing_telegram_user:
                    time.sleep(1)
                    raise ValidationError("User with this telegram_id already exists")
            
            # Хешируем пароль
            password_hash = get_password_hash(user_create.password)
            
            # Создаем пользователя
            user = await self.user_repository.create(user_create, password_hash)
            
            # Генерируем токены
            token = await self._generate_tokens(user.id)
            
            # Очищаем попытки после успешной регистрации
            await self.rate_limiter.clear_attempts(f"register_{client_ip}")
            
            return user, token
        except Exception as e:
            # Увеличиваем счетчик попыток при ошибке
            raise e
    
    async def authenticate_user(self, email: str, password: str, client_ip: str) -> Tuple[User, Token]:
        """Аутентификация пользователя с защитой от брутфорса"""
        email = email.lower()
        
        # Проверка rate limit по email и IP
        await self.rate_limiter.check_rate_limit(f"login_email_{email}")
        await self.rate_limiter.check_rate_limit(f"login_ip_{client_ip}")
        
        try:
            user = await self.user_repository.get_by_email(email)
            if not user:
                # Делаем задержку для защиты от перебора email
                time.sleep(2)  # Задержка для защиты от тайминг-атак
                raise AuthenticationError("Invalid email or password")
            
            # Проверка пароля с задержкой для защиты от брутфорса
            start_time = time.time()
            is_valid = verify_password(password, user.password_hash)
            elapsed = time.time() - start_time
            
            # Защита от тайминг-атак: фиксированная задержка
            min_delay = 0.5  # 500 миллисекунд
            if elapsed < min_delay:
                time.sleep(min_delay - elapsed)
            
            if not is_valid:
                time.sleep(2)  # Дополнительная задержка при неверном пароле
                raise AuthenticationError("Invalid email or password")
            
            # Генерируем токены
            token = await self._generate_tokens(user.id)
            
            # Очищаем попытки после успешной аутентификации
            await self.rate_limiter.clear_attempts(f"login_email_{email}")
            await self.rate_limiter.clear_attempts(f"login_ip_{client_ip}")
            
            # Обновляем last_login_at
            await self.user_repository.update_last_login(user.id)
            
            return user, token
        except Exception as e:
            # При ошибке увеличиваем счетчик попыток
            raise e
    
    async def refresh_tokens(self, refresh_token: str) -> Token:
        """Обновление access token с помощью refresh token"""
        try:
            payload = decode_token(refresh_token)
        except ValueError as e:
            raise AuthenticationError(str(e))
        
        # Проверяем тип токена
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")
        
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")
        
        # Проверяем, существует ли пользователь
        user = await self.user_repository.get_by_id(int(user_id))
        if not user:
            raise AuthenticationError("User not found")
        
        # Генерируем новые токены
        return await self._generate_tokens(int(user_id))
    
    async def bind_telegram(self, user_id: int, telegram_id: int) -> User:
        """Привязка Telegram ID к пользователю"""
        # Проверяем, не занят ли этот telegram_id
        existing_user = await self.user_repository.get_by_telegram_id(telegram_id)
        if existing_user and existing_user.id != user_id:
            raise ValidationError("This telegram_id is already bound to another user")
        
        return await self.user_repository.update_telegram_id(user_id, telegram_id)
    
    async def _generate_tokens(self, user_id: int) -> Token:
        """Генерация пары access/refresh токенов"""
        access_token_expires = timedelta(
            minutes=settings.security.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        
        access_token = create_access_token(
            data={"sub": str(user_id)},
            expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            data={"sub": str(user_id)}
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(access_token_expires.total_seconds())
        )
    
    async def get_current_user(self, token: str) -> User:
        """Получение текущего пользователя из токена"""
        try:
            payload = decode_token(token)
        except ValueError as e:
            raise AuthenticationError(str(e))
        
        # Проверяем тип токена
        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type for this operation")
        
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")
        
        user = await self.user_repository.get_by_id(int(user_id))
        if not user:
            raise AuthenticationError("User not found")
        
        return user