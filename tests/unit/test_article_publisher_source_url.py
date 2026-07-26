"""
Teste: _prepare_post_data deve propagar source_url do artigo para o
PostCreate — é o que permite o pré-filtro anti-reprocessamento do pipeline.
"""
from unittest.mock import MagicMock
from uuid import uuid4

from app.services.automation.article_publisher import ArticlePublisher


def test_prepare_post_data_persiste_source_url():
    publisher = ArticlePublisher(MagicMock())
    article = {
        "title": "Bitcoin atinge novo recorde histórico de preço em dólar",
        "slug": "bitcoin-recorde-historico",
        "content_markdown": "## Bitcoin\n\n" + "palavra de conteúdo " * 60,
        "excerpt": "Bitcoin atinge novo recorde em meio a forte demanda.",
        "meta_title": "Bitcoin bate recorde",
        "meta_description": "Bitcoin ultrapassa máxima histórica.",
        "source_url": "https://coindesk.com/noticia-original",
    }

    post_data = publisher._prepare_post_data(
        article, "<p>html</p>", None, uuid4()
    )

    assert post_data.source_url == "https://coindesk.com/noticia-original"
