from fastapi import APIRouter

from app.api.routes import demo, health, imports, properties

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(properties.router)
api_router.include_router(imports.router)
api_router.include_router(demo.router)
