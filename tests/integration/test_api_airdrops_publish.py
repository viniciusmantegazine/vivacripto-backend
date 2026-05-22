"""
Testes de integração do modo publish do endpoint de airdrop.

Mocka a camada de persistência (crud_post, ArticlePublisher, revalidação) pra
contornar a incompatibilidade UUID/SQLite pré-existente. Verifica orquestração:
publish vs preview, daily limit, force_category_slug, revalidação, slug retry.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.airdrops import get_generator
from app.core.config import settings


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
    """Cliente HTTP com get_db e get_generator overridados (sem DB real)."""
    from app.db.base import get_db
    from app.main import app

    async def fake_get_db():
        yield MagicMock()

    mock_generator = MagicMock()

    def fake_get_generator():
        return mock_generator

    app.dependency_overrides[get_db] = fake_get_db
    app.dependency_overrides[get_generator] = fake_get_generator
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.mock_generator = mock_generator
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_publish_true_persists_post_and_returns_id(airdrop_api_client):
    """publish=True deve chamar ArticlePublisher e retornar post_id."""
    article = _make_article("https://ref.example/abc", "https://layerzero.network")
    fake_post = MagicMock()
    fake_post.id = uuid4()

    airdrop_api_client.mock_generator.generate = AsyncMock(return_value=article)

    with patch("app.api.v1.endpoints.airdrops.crud_post") as mock_crud, \
         patch("app.api.v1.endpoints.airdrops._count_airdrop_posts_since",
               new=AsyncMock(return_value=0)), \
         patch("app.api.v1.endpoints.airdrops.ArticlePublisher") as MockPublisher, \
         patch("app.api.v1.endpoints.airdrops._revalidate_frontend", AsyncMock()):

        # Slug livre na primeira tentativa
        mock_crud.get_post_by_slug = AsyncMock(side_effect=[None, fake_post])
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

    publisher_instance.publish_article.assert_awaited_once()
    call_kwargs = publisher_instance.publish_article.call_args.kwargs
    assert call_kwargs.get("force_category_slug") == "airdrop"

    # publish=True deve pedir imagem (custo OK quando vai persistir)
    gen_kwargs = airdrop_api_client.mock_generator.generate.call_args.kwargs
    assert gen_kwargs.get("generate_image") is True


@pytest.mark.asyncio
async def test_publish_blocked_when_daily_limit_reached(airdrop_api_client):
    """Se já bateu o limite diário de airdrops, publish=True retorna 429."""
    from app.api.v1.endpoints.airdrops import AIRDROP_DAILY_LIMIT

    article = _make_article("https://ref.example/abc", "https://layerzero.network")

    airdrop_api_client.mock_generator.generate = AsyncMock(return_value=article)

    with patch(
        "app.api.v1.endpoints.airdrops._count_airdrop_posts_since",
        new=AsyncMock(return_value=AIRDROP_DAILY_LIMIT),
    ), patch(
        "app.api.v1.endpoints.airdrops.ArticlePublisher"
    ) as MockPublisher, patch(
        "app.api.v1.endpoints.airdrops._revalidate_frontend", AsyncMock()
    ):
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

    airdrop_api_client.mock_generator.generate = AsyncMock(return_value=article)

    with patch("app.api.v1.endpoints.airdrops.crud_post") as mock_crud, \
         patch("app.api.v1.endpoints.airdrops._count_airdrop_posts_since",
               new=AsyncMock(return_value=0)), \
         patch("app.api.v1.endpoints.airdrops.ArticlePublisher") as MockPublisher, \
         patch("app.api.v1.endpoints.airdrops._revalidate_frontend", AsyncMock()):

        mock_crud.get_post_by_slug = AsyncMock(return_value=None)
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


@pytest.mark.asyncio
async def test_publish_appends_suffix_on_slug_collision(airdrop_api_client):
    """Se o slug gerado já existe, deve anexar -2 (ou superior) e prosseguir."""
    article = _make_article("https://ref.example/abc", "https://layerzero.network")
    original_slug = article["slug"]
    fake_post = MagicMock()
    fake_post.id = uuid4()

    airdrop_api_client.mock_generator.generate = AsyncMock(return_value=article)

    # 1ª e 2ª chamadas: slugs já existem; 3ª: livre; 4ª (final, lookup do post): retorna fake_post
    existing = MagicMock()
    with patch("app.api.v1.endpoints.airdrops.crud_post") as mock_crud, \
         patch("app.api.v1.endpoints.airdrops._count_airdrop_posts_since",
               new=AsyncMock(return_value=0)), \
         patch("app.api.v1.endpoints.airdrops.ArticlePublisher") as MockPublisher, \
         patch("app.api.v1.endpoints.airdrops._revalidate_frontend", AsyncMock()):

        mock_crud.get_post_by_slug = AsyncMock(
            side_effect=[existing, existing, None, fake_post]
        )
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
    # Slug deve ter sufixo numérico anexado
    assert data["slug"].startswith(original_slug)
    assert data["slug"] != original_slug
