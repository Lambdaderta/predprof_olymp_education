# app/api/v1/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import db_helper
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.core.schemas.auth import (
    UserCreate,
    UserResponse,
    Token,
    RefreshTokenRequest,
    TelegramBindRequest,
    UserStatsResponse
)

from sqlalchemy import func, select
from app.models.learning import UserTaskProgress
from app.models.user import User
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    RateLimitError
)
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging


# OAuth2 схема для Bearer токенов
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# Настройка логгера
logger = logging.getLogger(__name__)

# Rate limiter (можно использовать Redis в продакшене)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Максимум 5 регистраций в минуту с одного IP
async def register_user(
    request: Request,
    user_create: UserCreate,
    session: AsyncSession = Depends(db_helper.session_getter)
):
    """Регистрация нового пользователя с защитой от брутфорса"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Registration attempt from IP: {client_ip} for email: {user_create.email}")
    
    try:
        user_repo = UserRepository(session)
        auth_service = AuthService(user_repo)
        user, _ = await auth_service.register_user(user_create, client_ip)
        
        logger.info(f"Successful registration for user ID: {user.id}, email: {user.email}")
        return user
    except RateLimitError as e:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"Validation error during registration: {e.detail}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        logger.error(f"Internal error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")  # Максимум 10 попыток входа в минуту с одного IP
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(db_helper.session_getter)
):
    """Логин пользователя и получение токенов"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Login attempt from IP: {client_ip} for email: {form_data.username}")
    
    try:
        user_repo = UserRepository(session)
        auth_service = AuthService(user_repo)
        _, token = await auth_service.authenticate_user(
            form_data.username,
            form_data.password,
            client_ip
        )
        
        logger.info(f"Successful login for email: {form_data.username}")
        return token
    except RateLimitError as e:
        logger.warning(f"Rate limit exceeded for login from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except AuthenticationError as e:
        logger.warning(f"Authentication failed for email: {form_data.username} from IP: {client_ip}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Internal error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/refresh", response_model=Token)
@limiter.limit("20/hour")  # Максимум 20 обновлений токена в час
async def refresh_access_token(
    request: Request,
    refresh_request: RefreshTokenRequest,
    session: AsyncSession = Depends(db_helper.session_getter)
):
    """Обновление access token с помощью refresh token"""
    try:
        user_repo = UserRepository(session)
        auth_service = AuthService(user_repo)
        return await auth_service.refresh_tokens(refresh_request.refresh_token)
    except AuthenticationError as e:
        logger.warning(f"Token refresh failed: {e.detail}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Internal error during token refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(db_helper.session_getter)
):
    """Получение информации о текущем пользователе"""
    try:
        user_repo = UserRepository(session)
        auth_service = AuthService(user_repo)
        user = await auth_service.get_current_user(token)
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/telegram-bind", response_model=UserResponse)
@limiter.limit("3/minute")  # Ограничение на привязку Telegram
async def bind_telegram_account(
    request: Request,
    telegram_bind: TelegramBindRequest,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(db_helper.session_getter)
):
    """Привязка Telegram аккаунта к пользователю"""
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Telegram binding attempt from IP: {client_ip}")
    
    try:
        user_repo = UserRepository(session)
        auth_service = AuthService(user_repo)
        current_user = await auth_service.get_current_user(token)
        updated_user = await auth_service.bind_telegram(
            current_user.id,
            telegram_bind.telegram_id
        )
        
        logger.info(f"Successful Telegram binding for user ID: {current_user.id}")
        return updated_user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValidationError as e:
        logger.warning(f"Validation error during Telegram binding: {e.detail}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except Exception as e:
        logger.error(f"Internal error during Telegram binding: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(db_helper.session_getter)
):
    # 1. Считаем решенные задачи
    tasks_query = select(func.count()).where(
        UserTaskProgress.user_id == current_user.id,
        UserTaskProgress.is_correct == True
    )
    tasks_res = await session.execute(tasks_query)
    tasks_count = tasks_res.scalar() or 0

    courses_count = 0 
    
    total_xp = tasks_count * 10

    return UserStatsResponse(
        courses_count=courses_count,
        lectures_count=0, 
        tasks_solved=tasks_count,
        total_xp=total_xp
    )