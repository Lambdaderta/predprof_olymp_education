# app/core/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import db_helper
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.models.user import User
import logging

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(db_helper.session_getter)
) -> User:
    """Зависимость для получения текущего пользователя из токена"""
    try:
        user_repo = UserRepository(session)
        auth_service = AuthService(user_repo)
        user = await auth_service.get_current_user(token)
        return user
    except Exception as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )