"""
Schemas Pydantic para o endpoint de geração de posts sobre airdrops.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class AirdropPostRequest(BaseModel):
    """Request para POST /api/v1/airdrops/generate-post"""

    project_name: str = Field(..., min_length=2, max_length=100)
    official_url: HttpUrl
    referral_url: HttpUrl
    publish: bool = False  # default: gera preview sem publicar


class AirdropPostResponse(BaseModel):
    """Response do endpoint de airdrop (preview ou publicação).

    Todas as falhas viram HTTPException; este schema só carrega sucesso.
    """

    success: bool
    post_id: Optional[str] = None
    title: str
    slug: str
    excerpt: str
    image_url: Optional[str] = None
    word_count: int = 0
    sources_used: List[str] = []
    preview_content: Optional[str] = None
