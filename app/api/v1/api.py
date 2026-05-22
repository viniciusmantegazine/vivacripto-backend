"""
Main API v1 router
"""
from fastapi import APIRouter
from app.api.v1.endpoints import airdrops, automation, health, newsletter, posts

api_router = APIRouter()

api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(newsletter.router, prefix="/newsletter", tags=["newsletter"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(airdrops.router, prefix="/airdrops", tags=["airdrops"])
