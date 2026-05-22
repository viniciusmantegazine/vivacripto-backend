"""
Airdrops API Endpoint

Endpoint manual para gerar (e opcionalmente publicar) posts sobre airdrops
de projetos cripto. Combina pesquisa web + IA com guardrails NFA.
"""
import traceback
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.rate_limiter import RATE_LIMITS, limiter
from app.core.security import verify_automation_token
from app.crud.crud_post import crud_post
from app.db.base import get_db
from app.schemas.airdrop import AirdropPostRequest, AirdropPostResponse
from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator
from app.services.airdrop.web_researcher import ResearchFailedError
from app.services.automation.article_publisher import ArticlePublisher
from app.services.automation.news_pipeline import NewsPipeline
from app.services.automation.quality_validator import QualityValidator

router = APIRouter()


async def _revalidate_frontend() -> None:
    """Dispara revalidação ISR no frontend. Não-bloqueante."""
    try:
        if not settings.FRONTEND_URL:
            logger.warning("FRONTEND_URL ausente — pulando revalidação")
            return
        url = f"{settings.FRONTEND_URL}/api/revalidate"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"secret": settings.REVALIDATE_SECRET})
            if resp.status_code == 200:
                logger.info("Revalidação frontend OK")
            else:
                logger.warning(f"Revalidação retornou {resp.status_code}")
    except Exception as e:
        logger.warning(f"Revalidação falhou (ignorada): {e}")


@router.post("/generate-post", response_model=AirdropPostResponse)
@limiter.limit(RATE_LIMITS["automation"])
async def generate_airdrop_post(
    request: Request,
    body: AirdropPostRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_automation_token),
):
    """
    Gera um artigo educacional sobre um projeto cripto e seu airdrop.

    Se publish=False (default): retorna preview sem persistir.
    Se publish=True: persiste como post com categoria "Airdrop".
    """
    logger.info(
        f"Airdrop post solicitado: project={body.project_name} publish={body.publish}"
    )

    generator = AirdropPostGenerator()
    try:
        article = await generator.generate(
            project_name=body.project_name,
            official_url=str(body.official_url),
            referral_url=str(body.referral_url),
        )
    except ResearchFailedError as e:
        logger.error(f"Airdrop: pesquisa web falhou: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Não foi possível coletar fontes confiáveis sobre o projeto. "
                "Verifique o link oficial e tente novamente."
            ),
        )
    except Exception as e:
        logger.exception(f"Airdrop: erro inesperado na geração: {e}")
        detail = "Erro interno ao gerar artigo de airdrop"
        if settings.DEBUG:
            detail += f": {e}"
        raise HTTPException(status_code=500, detail=detail)

    if article is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Falha ao gerar conteúdo válido (modelo retornou nulo após retry)",
        )

    # Valida qualidade (palavras + estrutura + título + excerpt)
    validator = QualityValidator(min_words=500, max_words=750)
    is_valid, errors = validator.validate_article(article)
    if not is_valid:
        logger.warning(f"Airdrop: validação reprovou ({errors})")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Artigo não passou na validação de qualidade", "errors": errors},
        )

    # Preview
    if not body.publish:
        return AirdropPostResponse(
            success=True,
            post_id=None,
            title=article["title"],
            slug=article["slug"],
            excerpt=article.get("excerpt", ""),
            image_url=article.get("image_url"),
            word_count=article.get("word_count", 0),
            sources_used=article.get("sources_used", []),
            preview_content=article["content_markdown"],
            errors=[],
        )

    # Publish: verificar limite diário
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_posts = await crud_post.get_recent_posts(db, since=today_start)
    if len(today_posts) >= NewsPipeline.MAX_POSTS_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Limite diário de posts atingido "
                f"({len(today_posts)}/{NewsPipeline.MAX_POSTS_PER_DAY})"
            ),
        )

    publisher = ArticlePublisher()
    published = await publisher.publish_article(
        article, db, force_category_slug="airdrop"
    )
    if not published:
        raise HTTPException(
            status_code=500, detail="Falha ao gravar artigo no banco"
        )

    # Buscar post pra obter ID
    created = await crud_post.get_post_by_slug(db, article["slug"])
    post_id = str(created.id) if created else None

    # Revalidação ISR (não bloqueante)
    await _revalidate_frontend()

    logger.info(f"Airdrop post publicado: {article['title'][:50]}")
    return AirdropPostResponse(
        success=True,
        post_id=post_id,
        title=article["title"],
        slug=article["slug"],
        excerpt=article.get("excerpt", ""),
        image_url=article.get("image_url"),
        word_count=article.get("word_count", 0),
        sources_used=article.get("sources_used", []),
        preview_content=None,
        errors=[],
    )
