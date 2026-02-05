# app/core/security.py
import bcrypt
from jose import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.core.config import settings


def get_password_hash(password: str) -> str:
    """Хеширование пароля с помощью bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.security.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "type": "access"})
    
    # Получаем реальное значение секрета
    secret_key = settings.security.JWT_SECRET_KEY.get_secret_value()
    
    return jwt.encode(
        to_encode,
        secret_key,
        algorithm=settings.security.JWT_ALGORITHM
    )

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Создание JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.security.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_urlsafe(32)  # Уникальный идентификатор
    })
    
    # Получаем реальное значение секрета
    secret_key = settings.security.JWT_SECRET_KEY.get_secret_value()
    
    return jwt.encode(
        to_encode,
        secret_key,
        algorithm=settings.security.JWT_ALGORITHM
    )

def decode_token(token: str) -> Dict[str, Any]:
    """Декодирование и валидация JWT токена"""
    try:
        # Получаем реальное значение секрета
        secret_key = settings.security.JWT_SECRET_KEY.get_secret_value()
        
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.security.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")