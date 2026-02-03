"""
Pydantic schemas for Weekly Report
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WeeklyReportRequest(BaseModel):
    """Request schema for weekly report generation"""

    publish: bool = Field(
        default=True,
        description="Se True, publica imediatamente. Se False, retorna preview sem publicar."
    )


class WeeklyReportResponse(BaseModel):
    """Response schema for weekly report generation"""

    success: bool
    post_id: Optional[str] = None
    title: str
    slug: str
    excerpt: str
    image_url: Optional[str] = None
    word_count: int = 0
    preview_content: Optional[str] = Field(
        None,
        description="Conteúdo em Markdown (apenas se publish=False)"
    )
    errors: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class WeeklyReportStatus(BaseModel):
    """Status of weekly report generation capability"""

    claude_available: bool = Field(
        description="Se a API do Claude está configurada e disponível"
    )
    last_report_date: Optional[datetime] = Field(
        None,
        description="Data do último relatório semanal gerado"
    )
    reports_this_week: int = Field(
        default=0,
        description="Número de relatórios gerados esta semana"
    )
