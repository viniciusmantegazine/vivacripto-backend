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
from app.services.ai.weekly_report_generator import weekly_report_generator
from app.services.automation.quality_validator import QualityValidator
from app.services.automation.article_publisher import ArticlePublisher
from app.schemas.report import WeeklyReportRequest, WeeklyReportResponse
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

        # Validar qualidade (mesmos limites do pipeline de notícias normais)
        from app.core.config import settings
        validator = QualityValidator(
            min_words=settings.NEWS_MIN_WORD_COUNT,
            max_words=settings.NEWS_MAX_WORD_COUNT,
        )
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


@router.post("/weekly-report", response_model=WeeklyReportResponse)
@limiter.limit(RATE_LIMITS["automation"])
async def generate_weekly_report(
    request: Request,
    report_request: WeeklyReportRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_automation_token)
):
    """
    Gera e publica um relatório semanal de análise macro + Bitcoin.

    Este endpoint é projetado para ser chamado esporadicamente (semanalmente),
    não como parte do pipeline de automação diária.

    Usa Claude Opus para gerar análises profundas do mercado de criptomoedas.

    Requer:
    - Authorization: Bearer {AUTOMATION_TOKEN}
    - Body: WeeklyReportRequest com publish (bool)

    Se publish=True: Publica o relatório imediatamente
    Se publish=False: Retorna preview do relatório sem publicar
    """
    logger.info("Geração de relatório semanal iniciada")

    try:
        # Verificar se Claude está disponível
        if not weekly_report_generator.claude_available:
            return WeeklyReportResponse(
                success=False,
                title="",
                slug="",
                excerpt="",
                errors=["Claude não configurado. Defina ANTHROPIC_API_KEY no ambiente."]
            )

        # Gerar relatório
        report = await weekly_report_generator.generate_report()

        if not report:
            return WeeklyReportResponse(
                success=False,
                title="",
                slug="",
                excerpt="",
                errors=["Falha ao gerar relatório semanal"]
            )

        # Se não for para publicar, retorna preview
        if not report_request.publish:
            return WeeklyReportResponse(
                success=True,
                title=report["title"],
                slug=report["slug"],
                excerpt=report["excerpt"],
                image_url=report.get("image_url"),
                word_count=report.get("word_count", 0),
                preview_content=report["content_markdown"],
                errors=[]
            )

        # Publicar relatório
        publisher = ArticlePublisher()
        published = await publisher.publish_article(report, db)

        if not published:
            return WeeklyReportResponse(
                success=False,
                title=report["title"],
                slug=report["slug"],
                excerpt=report["excerpt"],
                image_url=report.get("image_url"),
                word_count=report.get("word_count", 0),
                errors=["Relatório gerado mas falha ao publicar no banco"]
            )

        # Buscar post criado para obter ID
        from app.crud.crud_post import crud_post
        created_post = await crud_post.get_post_by_slug(db, report["slug"])
        post_id = str(created_post.id) if created_post else None

        logger.info(f"Relatório semanal publicado: {report['title']}")

        return WeeklyReportResponse(
            success=True,
            post_id=post_id,
            title=report["title"],
            slug=report["slug"],
            excerpt=report["excerpt"],
            image_url=report.get("image_url"),
            word_count=report.get("word_count", 0),
            errors=[]
        )

    except Exception as e:
        logger.exception(f"Erro ao gerar relatório semanal: {e}")
        from app.core.config import settings

        errors = ["Erro interno ao gerar relatório semanal"]
        if settings.DEBUG:
            errors.append(str(e))

        return WeeklyReportResponse(
            success=False,
            title="",
            slug="",
            excerpt="",
            errors=errors
        )
