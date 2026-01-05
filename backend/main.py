# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import db_helper


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    
    await db_helper.dispose()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,  
)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}!",
        "status": "ok",
        "debug": settings.debug,
        "database_url": settings.db.DATABASE_URL
    }

@app.get("/health")
async def health_check():
    """Проверка состояния приложения и базы данных"""
    try:
        async with db_helper.session_factory() as session:
            result = await session.execute("SELECT 1")
            db_value = result.scalar()
        
        return {
            "status": "healthy",
            "database": "connected",
            "database_value": db_value,
            "app_name": settings.app_name,
            "debug_mode": settings.debug
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "connection failed",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )