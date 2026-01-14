# app/core/exceptions.py
from fastapi import HTTPException, status

class AppException(Exception):
    """Базовое исключение для приложения"""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

class AuthenticationError(AppException):
    """Ошибка аутентификации"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail)

class AuthorizationError(AppException):
    """Ошибка авторизации"""
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)

class ValidationError(AppException):
    """Ошибка валидации данных"""
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)

class NotFoundError(AppException):
    """Ресурс не найден"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail)

class DatabaseError(AppException):
    """Ошибка базы данных"""
    def __init__(self, detail: str = "Database error"):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)

class RateLimitError(AppException):
    """Ошибка превышения лимита запросов"""
    def __init__(self, detail: str = "Too many requests"):
        super().__init__(status.HTTP_429_TOO_MANY_REQUESTS, detail)