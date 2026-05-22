"""
Testes de integração do modo publish do endpoint de airdrop.

Mocka a camada de persistência (crud_post, ArticlePublisher, revalidação) pra
contornar a incompatibilidade UUID/SQLite pré-existente. Verifica orquestração:
publish vs preview, daily limit, force_category_slug, revalidação.
"""
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Patch create_async_engine ANTES de qualquer import que carregue app.db.base
import sqlalchemy.ext.asyncio as _sa_async
_orig_create_engine = _sa_async.create_async_engine

def _safe_create_engine(*args, **kwargs):
    kwargs.pop("pool_size", None)
    kwargs.pop("max_overflow", None)
    kwargs["url"] = "sqlite+aiosqlite:///:memory:" if "url" not in kwargs and args else kwargs.get("url")
    return _orig_create_engine("sqlite+aiosqlite:///:memory:", **{k: v for k, v in kwargs.items() if k in ("echo", "future")})

_sa_async.create_async_engine = _safe_create_engine

from app.core.config import settings  # noqa: E402


def _make_article(referral: str, official: str) -> dict:
    """Cria um artigo bem-formado que passa pelo QualityValidator (500–750 palavras)."""
    body = (
        "## Sobre o projeto\n\n"
        + "Texto sobre crypto e blockchain explicando o protocolo de forma neutra. " * 30
        + "\n\n## O programa de airdrop\n\n"
        + "Texto sobre o airdrop. " * 25
        + f"\n\n## Como participar\n\nAcesse [aqui]({referral}) para se cadastrar. " * 5
        + "\n\n## Informações importantes\n\n"
        + f"O link de cadastro acima é um link de referência. Site oficial: [{official}]({official}). "
        + "Este conteudo não constitui recomendação de investimento."
    )
    return {
        "title": "LayerZero airdrop: o que e o protocolo e como participar em 2026",
        "slug": "layerzero-protocolo-airdrop-2026",
        "excerpt": "Conheca o LayerZero, protocolo de interoperabilidade entre blockchains agora aqui.",
        "content_markdown": body,
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "LayerZero, protocolo de interoperabilidade. Veja como participar do "
            "programa de airdrop pelo site oficial e cadastre-se."
        ),
        "image_url": "https://img/x.jpg",
        "sources_used": ["https://layerzero.network"],
        "word_count": 600,
    }


@pytest_asyncio.fixture
async def airdrop_api_client():
    """Cliente HTTP com get_db override mockado."""
    from app.db.base import get_db
    from app.main import app

    async def fake_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = fake_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_publish_true_persists_post_and_returns_id(airdrop_api_client):
    """publish=True deve chamar ArticlePublisher e retornar post_id."""
    article = _make_article("https://ref.example/abc", "https://layerzero.network")
    fake_post = MagicMock()
    fake_post.id = uuid4()

    with patch("app.api.v1.endpoints.airdrops.AirdropPostGenerator") as MockGen, \
         patch("app.api.v1.endpoints.airdrops.crud_post") as mock_crud, \
         patch("app.api.v1.endpoints.airdrops.ArticlePublisher") as MockPublisher, \
         patch("app.api.v1.endpoints.airdrops._revalidate_frontend", AsyncMock()):

        MockGen.return_value.generate = AsyncMock(return_value=article)
        mock_crud.get_recent_posts = AsyncMock(return_value=[])  # 0 posts hoje
        mock_crud.get_post_by_slug = AsyncMock(return_value=fake_post)
        publisher_instance = MockPublisher.return_value
        publisher_instance.publish_article = AsyncMock(return_value=True)

        response = await airdrop_api_client.post(
            "/api/v1/airdrops/generate-post",
            json={
                "project_name": "LayerZero",
                "official_url": "https://layerzero.network",
                "referral_url": "https://ref.example/abc",
                "publish": True,
            },
            headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True
    assert data["post_id"] == str(fake_post.id)
    assert data.get("preview_content") in (None, "")

    # ArticlePublisher.publish_article foi chamado com force_category_slug="airdrop"
    publisher_instance.publish_article.assert_awaited_once()
    call_kwargs = publisher_instance.publish_article.call_args.kwargs
    assert call_kwargs.get("force_category_slug") == "airdrop"


@pytest.mark.asyncio
async def test_publish_blocked_when_daily_limit_reached(airdrop_api_client):
    """Se já tem 10 posts hoje, publish=True retorna 429."""
    from app.services.automation.news_pipeline import NewsPipeline

    article = _make_article("https://ref.example/abc", "https://layerzero.network")
    fake_posts = [MagicMock() for _ in range(NewsPipeline.MAX_POSTS_PER_DAY)]

    with patch("app.api.v1.endpoints.airdrops.AirdropPostGenerator") as MockGen, \
         patch("app.api.v1.endpoints.airdrops.crud_post") as mock_crud, \
         patch("app.api.v1.endpoints.airdrops.ArticlePublisher") as MockPublisher, \
         patch("app.api.v1.endpoints.airdrops._revalidate_frontend", AsyncMock()):

        MockGen.return_value.generate = AsyncMock(return_value=article)
        mock_crud.get_recent_posts = AsyncMock(return_value=fake_posts)
        publisher_instance = MockPublisher.return_value
        publisher_instance.publish_article = AsyncMock(return_value=True)

        response = await airdrop_api_client.post(
            "/api/v1/airdrops/generate-post",
            json={
                "project_name": "LayerZero",
                "official_url": "https://layerzero.network",
                "referral_url": "https://ref.example/abc",
                "publish": True,
            },
            headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
        )

    assert response.status_code == 429
    publisher_instance.publish_article.assert_not_called()


@pytest.mark.asyncio
async def test_publish_failure_returns_500(airdrop_api_client):
    """Se ArticlePublisher retorna False (falha DB), endpoint deve dar 500."""
    article = _make_article("https://ref.example/abc", "https://layerzero.network")

    with patch("app.api.v1.endpoints.airdrops.AirdropPostGenerator") as MockGen, \
         patch("app.api.v1.endpoints.airdrops.crud_post") as mock_crud, \
         patch("app.api.v1.endpoints.airdrops.ArticlePublisher") as MockPublisher, \
         patch("app.api.v1.endpoints.airdrops._revalidate_frontend", AsyncMock()):

        MockGen.return_value.generate = AsyncMock(return_value=article)
        mock_crud.get_recent_posts = AsyncMock(return_value=[])
        publisher_instance = MockPublisher.return_value
        publisher_instance.publish_article = AsyncMock(return_value=False)

        response = await airdrop_api_client.post(
            "/api/v1/airdrops/generate-post",
            json={
                "project_name": "LayerZero",
                "official_url": "https://layerzero.network",
                "referral_url": "https://ref.example/abc",
                "publish": True,
            },
            headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
        )

    assert response.status_code == 500
