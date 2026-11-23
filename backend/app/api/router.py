from fastapi import APIRouter

from app.api.routes import (
    analysis,
    analytics,
    demo,
    health,
    imports,
    insights,
    properties,
    reviews,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(properties.router)
api_router.include_router(imports.router)
api_router.include_router(demo.router)
api_router.include_router(analysis.router)
api_router.include_router(analytics.router)
api_router.include_router(reviews.router)
api_router.include_router(insights.router)
