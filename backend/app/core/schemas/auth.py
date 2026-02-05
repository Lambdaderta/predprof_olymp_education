# app/core/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict, validator
from typing import Optional
from datetime import datetime
import re

class PasswordComplexity:
    """Класс для проверки сложности пароля"""
    MIN_LENGTH = 12
    MAX_LENGTH = 64
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    @classmethod
    def validate(cls, password: str) -> None:
        """Проверка сложности пароля"""
        errors = []
        
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")
        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must be at most {cls.MAX_LENGTH} characters long")
        
        if cls.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        if cls.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        if cls.REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
            errors.append(f"Password must contain at least one special character ({cls.SPECIAL_CHARS})")
        
        # Проверка на распространенные слабые пароли
        weak_passwords = [
            "password", "123456", "12345678", "qwerty", "abc123", "password1",
            "iloveyou", "1q2w3e4r", "admin", "welcome", "monkey", "sunshine"
        ]
        if password.lower() in weak_passwords:
            errors.append("Password is too common and easily guessable")
        
        if errors:
            raise ValueError("; ".join(errors))

class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    telegram_id: Optional[int] = Field(None, description="Telegram user ID", ge=1)
    
    @validator('email')
    def validate_email(cls, v):
        """Дополнительная валидация email"""
        # Проверка на корпоративные/временные email сервисы
        disposable_domains = [
            'tempmail.com', '10minutemail.com', 'guerrillamail.com',
            'mailinator.com', 'trashmail.com', 'fakeinbox.com'
        ]
        domain = v.split('@')[-1].lower()
        
        if domain in disposable_domains:
            raise ValueError("Disposable email addresses are not allowed")
        
        # Проверка на корректный формат (дополнительно к EmailStr)
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise ValueError("Invalid email format")
        
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        """Валидация сложности пароля"""
        PasswordComplexity.validate(v)
        return v
    
    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password", min_length=8, max_length=64)
    
    @validator('email')
    def lowercase_email(cls, v):
        return v.lower()

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration time in seconds")

class TokenPayload(BaseModel):
    sub: str  # user_id
    exp: int
    type: str  # access or refresh

class UserResponse(BaseModel):
    id: int
    email: str
    telegram_id: Optional[int] = None
    role: str = "user"
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token for getting new access token")

class TelegramBindRequest(BaseModel):
    telegram_id: int = Field(..., description="Telegram user ID to bind", ge=1)

class UserStatsResponse(BaseModel):
    courses_count: int = 0
    lectures_count: int = 0
    tasks_solved: int = 0
    total_xp: int = 0