"""
Airdrops API Endpoint

Endpoint manual para gerar (e opcionalmente publicar) posts sobre airdrops
de projetos cripto. Combina pesquisa web + IA com guardrails NFA.
"""
import traceback

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.rate_limiter import RATE_LIMITS, limiter
from app.core.security import verify_automation_token
from app.db.base import get_db
from app.schemas.airdrop import AirdropPostRequest, AirdropPostResponse
from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator
from app.services.airdrop.web_researcher import ResearchFailedError
from app.services.automation.quality_validator import QualityValidator

router = APIRouter()


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

    # publish=True será tratado em task posterior; por enquanto, sempre preview
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
