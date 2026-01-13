"""
Automation API Endpoints
Endpoints para disparar e gerenciar a automação de notícias
"""
import traceback
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.services.automation.news_pipeline import NewsPipeline
from app.services.ai.content_generator import ContentGenerator
from app.services.automation.quality_validator import QualityValidator
from app.core.logging import logger
from app.core.security import verify_automation_token
from app.core.rate_limiter import limiter, RATE_LIMITS
from app.crud.crud_post import crud_post

router = APIRouter()


@router.post("/trigger")
@limiter.limit(RATE_LIMITS["automation"])
async def trigger_automation(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_automation_token)
):
    """
    Dispara o pipeline de automação de notícias

    Requer token de autorização no header:
    Authorization: Bearer {AUTOMATION_TOKEN}
    """
    logger.info("Automação disparada via API")

    try:
        # Executar pipeline
        pipeline = NewsPipeline()
        report = await pipeline.run(db)

        return {
            "success": report["status"] == "completed",
            "report": report
        }
    except Exception as e:
        logger.exception(f"Erro no pipeline de automação: {e}")
        from app.core.config import settings
        error_response = {
            "success": False,
            "error": "Erro interno ao executar pipeline de automação"
        }
        if settings.DEBUG:
            error_response["error_detail"] = str(e)
            error_response["traceback"] = traceback.format_exc()
        return error_response


@router.get("/status")
async def get_automation_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna o status da automação

    Informações sobre posts publicados hoje e limite diário
    """
    # Usar datetime naive (sem timezone) para compatibilidade com TIMESTAMP WITHOUT TIME ZONE
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
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


@router.post("/test-generation")
@limiter.limit(RATE_LIMITS["automation"])
async def test_content_generation(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_automation_token)
):
    """
    Endpoint de teste para gerar um artigo sem coletar notícias
    Usado para debug da validação de parágrafos
    """
    logger.info("Teste de geração de conteúdo iniciado")

    # Notícia fictícia para teste
    fake_news = {
        "source": "Test Source",
        "source_language": "en",
        "title": "Bitcoin Reaches New All-Time High Above $100,000",
        "url": "https://example.com/test",
        "description": "Bitcoin has surged past $100,000 for the first time in history, marking a significant milestone for the cryptocurrency market.",
        "published_at": datetime.now(timezone.utc),
        "collected_at": datetime.now(timezone.utc),
    }

    try:
        # Gerar conteúdo (usando categoria bitcoin para o teste)
        content_generator = ContentGenerator()
        article = await content_generator.generate_article(fake_news, category="bitcoin")

        if not article:
            return {
                "success": False,
                "error": "Falha ao gerar artigo"
            }

        # Validar qualidade
        validator = QualityValidator()
        is_valid, errors = validator.validate_article(article)

        return {
            "success": True,
            "article_generated": True,
            "validation_passed": is_valid,
            "validation_errors": errors,
            "article_preview": {
                "title": article.get("title", ""),
                "excerpt": article.get("excerpt", "")[:100],
                "content_length": len(article.get("content_markdown", "")),
                "word_count": len(article.get("content_markdown", "").split()),
                "paragraph_count": len([p for p in article.get("content_markdown", "").split('\n\n') if p.strip()]),
            }
        }

    except Exception as e:
        logger.error(f"Erro no teste de geração: {e}")
        # Em produção, não expor traceback para evitar information disclosure
        from app.core.config import settings
        error_response = {
            "success": False,
            "error": "Erro interno ao gerar conteúdo de teste"
        }
        # Apenas incluir detalhes em modo debug
        if settings.DEBUG:
            error_response["error_detail"] = str(e)
            error_response["traceback"] = traceback.format_exc()
        return error_response
