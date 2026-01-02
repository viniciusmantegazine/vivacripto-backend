"""
Automation API Endpoints
Endpoints para disparar e gerenciar a automação de notícias
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.base import get_async_session
from app.services.automation.news_pipeline import NewsPipeline
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


@router.post("/trigger")
async def trigger_automation(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Dispara o pipeline de automação de notícias
    
    Requer token de autorização no header:
    Authorization: Bearer {AUTOMATION_TOKEN}
    """
    # Verificar autenticação
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autorização ausente")
    
    token = authorization.replace("Bearer ", "")
    if token != settings.AUTOMATION_TOKEN:
        raise HTTPException(status_code=403, detail="Token de autorização inválido")
    
    logger.info("Automação disparada via API")
    
    # Executar pipeline
    pipeline = NewsPipeline()
    report = await pipeline.run(db)
    
    return {
        "success": report["status"] == "completed",
        "report": report
    }


@router.get("/status")
async def get_automation_status(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Retorna o status da automação
    
    Informações sobre posts publicados hoje e limite diário
    """
    from datetime import datetime
    from app.crud.crud_post import crud_post
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_posts = await crud_post.get_recent_posts(db, since=today_start)
    
    max_posts = NewsPipeline.MAX_POSTS_PER_DAY
    published_today = len(today_posts)
    remaining = max(0, max_posts - published_today)
    
    return {
        "daily_limit": max_posts,
        "published_today": published_today,
        "remaining_slots": remaining,
        "limit_reached": remaining == 0,
    }
