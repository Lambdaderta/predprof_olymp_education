# main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from contextlib import asynccontextmanager
from sqlalchemy import text 
import logging
from app.core.admin import setup_admin 
from app.api.v1.routes import api_router
from app.api.v1.routes import ws 
from app.core.config import settings
from app.core.database import db_helper
from app.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    NotFoundError,
    DatabaseError,
    RateLimitError
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Контекстный менеджер для жизненного цикла приложения"""
    # Startup
    logger.info(f"🚀 Starting {settings.app_name} in {'DEBUG' if settings.debug else 'PRODUCTION'} mode")
    
    # Маскируем пароль в URL для логов
    masked_db_url = settings.db.DATABASE_URL
    if settings.db.DB_PASSWORD:
        masked_db_url = masked_db_url.replace(
            settings.db.DB_PASSWORD.get_secret_value(), 
            "***"
        )
    logger.info(f"📝 Database: {masked_db_url}")
    logger.info(f"🔐 JWT Algorithm: {settings.security.JWT_ALGORITHM}")
    
    # Проверка подключения к базе данных при старте
    try:
        async with db_helper.session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            db_value = result.scalar()
        logger.info("✅ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

    setup_admin(app, db_helper.engine)
    
    yield
    
    # Shutdown
    await db_helper.dispose()
    logger.info("👋 Application shutdown complete")

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,  
    redoc_url="/redoc" if settings.debug else None,  
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(api_router, prefix="/api/v1")
app.include_router(ws.router)

@app.get("/", summary="Root endpoint", tags=["root"])
async def root():
    """Корневой эндпоинт API"""
    return {
        "message": f"Welcome to {settings.app_name} API",
        "docs": {
            "swagger": "/docs",
            "redoc": "/redoc"
        } if settings.debug else None,
        "environment": "development" if settings.debug else "production",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health", summary="Health check", tags=["health"])
async def health_check():
    """Проверка здоровья приложения"""
    try:
        # Проверяем подключение к БД
        async with db_helper.session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            db_value = result.scalar()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": "development" if settings.debug else "production",
            "database": "connected",
            "database_ping": db_value,
            "app_name": settings.app_name,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connection failed",
            "error": str(e) if settings.debug else "Database connection error"
        }

# Глобальный обработчик исключений
@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    """Глобальный обработчик кастомных исключений"""
    logger.error(f"AppException: {exc.detail} (type: {type(exc).__name__})")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": type(exc).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Глобальный обработчик всех исключений"""
    logger.exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": "InternalServerError",
            "timestamp": datetime.utcnow().isoformat(),
            "debug_info": str(exc) if settings.debug else None
        }
    )

# Обработчик для 404 ошибок
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Not Found",
            "error": "NotFoundError",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# @app.websocket("/ws/pvp/{client_id}")
# async def websocket_endpoint(websocket: WebSocket, client_id: int):
#     await manager.connect(websocket)
#     try:
#         while True:
#             data = await websocket.receive_text()
#             # Логика игры: проверка ответа, обновление счета
#             await manager.broadcast(f"Client #{client_id} scored!")
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning",
        access_log=False  # Логи доступа лучше настраивать через Nginx или подобное
    )