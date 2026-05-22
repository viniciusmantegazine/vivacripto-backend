"""
Testa o override de categoria no ArticlePublisher para uso em airdrops.

Foca em `_get_or_create_category` em isolamento (mocking AsyncSession),
evitando dependência de fixtures de DB real — o suite tem incompatibilidade
pré-existente entre UUID do Postgres e SQLite usado nos testes.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.db.models import Category
from app.services.automation.article_publisher import ArticlePublisher


def _mock_db_with_existing_category(category: Category) -> MagicMock:
    """Mocka AsyncSession.execute() retornando a categoria fornecida."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = category
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _mock_db_without_category() -> MagicMock:
    """Mocka AsyncSession.execute() retornando None (categoria nova)."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_get_or_create_category_uses_forced_slug_skipping_classifier():
    """Quando force_category_slug é passado, classifier.classify() NÃO é chamado."""
    publisher = ArticlePublisher(image_generator=MagicMock())
    existing = Category(id=uuid4(), name="Airdrop", slug="airdrop")
    db = _mock_db_with_existing_category(existing)

    article = {
        "title": "LayerZero airdrop",
        "content_markdown": "x",
        "excerpt": "y",
    }

    with patch(
        "app.services.automation.article_publisher.category_classifier"
    ) as mock_classifier:
        category = await publisher._get_or_create_category(
            article, db, force_category_slug="airdrop"
        )

    assert category is existing
    mock_classifier.classify.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_category_falls_back_to_classifier_when_no_force():
    """Sem force_category_slug, classifier.classify() é chamado (comportamento original)."""
    publisher = ArticlePublisher(image_generator=MagicMock())
    existing = Category(id=uuid4(), name="Bitcoin", slug="bitcoin")
    db = _mock_db_with_existing_category(existing)

    article = {
        "title": "Bitcoin nova maxima",
        "content_markdown": "x",
        "excerpt": "y",
    }

    with patch(
        "app.services.automation.article_publisher.category_classifier"
    ) as mock_classifier:
        mock_classifier.classify.return_value = "bitcoin"
        mock_classifier.get_category_name.return_value = "Bitcoin"
        category = await publisher._get_or_create_category(article, db)

    assert category is existing
    mock_classifier.classify.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_category_creates_when_forced_slug_not_in_db():
    """Quando force_category_slug aponta pra slug inexistente, cria nova Category."""
    publisher = ArticlePublisher(image_generator=MagicMock())
    db = _mock_db_without_category()

    article = {
        "title": "x",
        "content_markdown": "y",
        "excerpt": "z",
    }

    with patch(
        "app.services.automation.article_publisher.category_classifier"
    ) as mock_classifier:
        mock_classifier.get_category_name.return_value = None
        category = await publisher._get_or_create_category(
            article, db, force_category_slug="newcategory"
        )

    assert category.slug == "newcategory"
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    mock_classifier.classify.assert_not_called()


def test_publish_article_signature_accepts_force_category_slug():
    """Sanity check: a assinatura pública aceita o novo kwarg."""
    import inspect

    sig = inspect.signature(ArticlePublisher.publish_article)
    assert "force_category_slug" in sig.parameters
    param = sig.parameters["force_category_slug"]
    assert param.default is None


@pytest.mark.asyncio
async def test_publish_article_public_path_with_force_slug_skips_classifier():
    """
    Testa o caminho público publish_article com force_category_slug,
    mockando crud_post.create_post (não testa persistência real, mas
    valida que a orquestração chama classifier=None e force=airdrop).
    """
    mock_image_gen = MagicMock()
    mock_image_gen.generate_and_upload_image = AsyncMock(return_value="https://img/x.jpg")
    publisher = ArticlePublisher(image_generator=mock_image_gen)

    existing = Category(id=uuid4(), name="Airdrop", slug="airdrop")
    db = _mock_db_with_existing_category(existing)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    article = {
        "title": "Layerzero airdrop tem cadastro aberto para token nativo",
        "slug": "layerzero-airdrop-cadastro-aberto",
        "content_markdown": "## Sobre\n\nx\n\nx",
        "excerpt": "Layerzero abriu cadastro para o seu airdrop de token nativo do projeto.",
        "meta_title": "Layerzero airdrop",
        "meta_description": (
            "Layerzero abriu cadastro para o seu airdrop de token nativo do projeto agora."
        ),
    }

    mock_post = MagicMock()
    with patch(
        "app.services.automation.article_publisher.category_classifier"
    ) as mock_classifier, patch(
        "app.services.automation.article_publisher.crud_post.create_post",
        new=AsyncMock(return_value=mock_post),
    ):
        ok = await publisher.publish_article(
            article, db, force_category_slug="airdrop"
        )

    assert ok is True
    mock_classifier.classify.assert_not_called()
    db.commit.assert_awaited_once()
