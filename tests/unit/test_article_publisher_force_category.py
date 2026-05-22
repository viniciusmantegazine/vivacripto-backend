"""
Testa o override de categoria no ArticlePublisher para uso em airdrops.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.db.models import Category
from app.services.automation.article_publisher import ArticlePublisher


@pytest_asyncio.fixture
async def airdrop_category(db_session) -> Category:
    cat = Category(id=uuid4(), name="Airdrop", slug="airdrop")
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)
    return cat


@pytest.mark.asyncio
async def test_publish_uses_forced_category_slug(db_session, airdrop_category):
    """Quando force_category_slug é passado, classifier não é usado."""
    article = {
        "title": "LayerZero: o que e o protocolo e como participar do airdrop",
        "slug": "layerzero-protocolo-airdrop",
        "content_markdown": "## Sobre\n\nLayerZero is a protocol.\n\nDetails here.",
        "excerpt": "Conheca o LayerZero, protocolo de interoperabilidade entre blockchains.",
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "Conheca o LayerZero, protocolo de interoperabilidade. Veja como "
            "participar do airdrop pelo site oficial."
        ),
    }

    mock_image_gen = MagicMock()
    mock_image_gen.generate_and_upload_image = AsyncMock(return_value="https://img/test.jpg")
    publisher = ArticlePublisher(image_generator=mock_image_gen)

    with patch(
        "app.services.automation.article_publisher.category_classifier"
    ) as mock_classifier:
        result = await publisher.publish_article(
            article, db_session, force_category_slug="airdrop"
        )

    assert result is True, "Article should publish successfully"
    mock_classifier.classify.assert_not_called()


@pytest.mark.asyncio
async def test_publish_falls_back_to_classifier_when_no_force(db_session, airdrop_category):
    """Sem force_category_slug, classifier ainda é chamado (comportamento atual)."""
    article = {
        "title": "Bitcoin atinge nova maxima historica em 2026",
        "slug": "bitcoin-maxima-2026",
        "content_markdown": "## Maxima\n\nBitcoin reached.\n\nDetails.",
        "excerpt": "Bitcoin atingiu nova maxima historica acima de US$ 150 mil dolares.",
        "meta_title": "Bitcoin maxima",
        "meta_description": (
            "Bitcoin atinge nova maxima historica acima de US$ 150 mil em 2026, "
            "marcando milestone significativo."
        ),
    }

    mock_image_gen = MagicMock()
    mock_image_gen.generate_and_upload_image = AsyncMock(return_value="https://img/test.jpg")
    publisher = ArticlePublisher(image_generator=mock_image_gen)

    with patch(
        "app.services.automation.article_publisher.category_classifier"
    ) as mock_classifier:
        mock_classifier.classify.return_value = "airdrop"
        mock_classifier.get_category_name.return_value = "Airdrop"
        await publisher.publish_article(article, db_session)

    mock_classifier.classify.assert_called_once()
