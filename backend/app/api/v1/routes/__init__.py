from fastapi import APIRouter
from app.api.v1.routes import auth
from app.api.v1.routes import ws
from .courses import router as courses_router
from .topics import router as topics_router
from .pvp import router as pvp_router


api_router = APIRouter()

api_router.include_router(auth.router, tags=["auth"])

api_router.include_router(courses_router)
api_router.include_router(topics_router, prefix="/api/v1", tags=["tasks"])
api_router.include_router(pvp_router)
