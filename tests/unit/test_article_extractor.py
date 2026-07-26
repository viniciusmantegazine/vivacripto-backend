"""
Testes do ArticleExtractor: extração do texto completo da notícia original.
Toda falha deve resultar em None (o pipeline segue com o resumo do RSS).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("trafilatura")

from app.services.sources.article_extractor import (
    MAX_TEXT_CHARS,
    ArticleExtractor,
)


def _with_fetch(monkeypatch, ext, html):
    async def fake_fetch(url):
        return html
    monkeypatch.setattr(ext, "_fetch", fake_fetch)


@pytest.mark.asyncio
async def test_url_vazia_retorna_none():
    ext = ArticleExtractor()
    assert await ext.extract("") is None


@pytest.mark.asyncio
async def test_fetch_falhou_retorna_none(monkeypatch):
    ext = ArticleExtractor()
    _with_fetch(monkeypatch, ext, None)
    assert await ext.extract("https://exemplo.com/noticia") is None


@pytest.mark.asyncio
async def test_extracao_curta_descartada(monkeypatch):
    """Texto < 200 chars = extração falhou (paywall, página de erro)."""
    ext = ArticleExtractor()
    _with_fetch(monkeypatch, ext, "<html><body>x</body></html>")
    monkeypatch.setattr(
        "app.services.sources.article_extractor.trafilatura.extract",
        lambda *a, **k: "texto curto demais",
    )
    assert await ext.extract("https://exemplo.com/noticia") is None


@pytest.mark.asyncio
async def test_texto_valido_e_truncamento(monkeypatch):
    ext = ArticleExtractor()
    _with_fetch(monkeypatch, ext, "<html><body>ok</body></html>")
    texto_longo = "palavra " * 3000  # ~24k chars
    monkeypatch.setattr(
        "app.services.sources.article_extractor.trafilatura.extract",
        lambda *a, **k: texto_longo,
    )

    result = await ext.extract("https://exemplo.com/noticia")

    assert result is not None
    assert len(result) == MAX_TEXT_CHARS
    assert result.startswith("palavra")
