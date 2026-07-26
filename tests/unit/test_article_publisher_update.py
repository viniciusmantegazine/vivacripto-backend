"""
Testes do update_article — o caminho que roda quando o DuplicateDetector
decide UPDATE_EXISTING.

Dois defeitos que estes testes fixam:

1. O update gravava apenas content_markdown e content_html, deixando título,
   excerpt e meta description do post ANTIGO junto do corpo NOVO. O conteúdo
   foi escrito para o título novo, então o post ficava incoerente — título
   dizendo uma coisa e texto dizendo outra.

2. O update não gravava source_url. O pré-filtro anti-reprocessamento procura
   por Post.source_url em posts recentes, então a URL da segunda fonte nunca
   era registrada: aquela notícia passava o filtro em TODO run seguinte, era
   regerada (1 chamada de LLM), redetectada como duplicata e atualizava o post
   outra vez — por cerca de 24h, a cada disparo do cron.

O slug NÃO é atualizado de propósito: é a URL pública do post, e trocá-la
quebraria links e histórico de SEO. Título mudar sem o slug mudar é
comportamento normal e desejado.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.automation.article_publisher import ArticlePublisher

ARTIGO_NOVO = {
    "title": "Sberbank Confirma Infraestrutura de Cripto para 2026",
    "slug": "sberbank-confirma-infraestrutura-cripto",
    "content_markdown": "## Sberbank avanca\n\n" + "palavra de conteudo " * 60,
    "excerpt": "Sberbank confirma plano de negociacao de criptomoedas para este ano no mercado russo.",
    "meta_title": "Sberbank Confirma Cripto",
    "meta_description": "Entenda o que o avanco do Sberbank em criptomoedas significa para o mercado institucional russo.",
    "source_url": "https://cointelegraph.com/sberbank-cripto",
    "source_name": "Cointelegraph",
    "category": "regulacao",
}


def _publisher_com_crud():
    """ArticlePublisher com crud_post mockado. Devolve (publisher, crud)."""
    publisher = ArticlePublisher(MagicMock())
    return publisher


async def _executa_update(artigo=None, post_id=None):
    """Roda update_article e devolve o PostUpdate que chegou ao crud."""
    artigo = artigo if artigo is not None else dict(ARTIGO_NOVO)
    post_id = post_id or str(uuid4())

    db = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    with patch("app.services.automation.article_publisher.crud_post") as crud:
        crud.update_post = AsyncMock(return_value=MagicMock())
        publisher = _publisher_com_crud()

        ok = await publisher.update_article(post_id, artigo, db)

        assert ok is True, "update_article deveria ter sucesso"
        return crud.update_post.await_args.kwargs["post_in"]


@pytest.mark.asyncio
async def test_update_grava_o_conteudo_novo():
    post_in = await _executa_update()

    assert post_in.content_markdown.startswith("## Sberbank avanca")
    assert post_in.content_html


@pytest.mark.asyncio
async def test_update_grava_o_titulo_novo():
    """
    Regressão: o título ficava o antigo, junto do corpo novo. O conteúdo é
    escrito para o título novo, então manter o antigo produz post incoerente.
    """
    post_in = await _executa_update()

    assert post_in.title == "Sberbank Confirma Infraestrutura de Cripto para 2026"


@pytest.mark.asyncio
async def test_update_grava_excerpt_e_metas_novos():
    """Todos os campos derivados do conteúdo acompanham o conteúdo."""
    post_in = await _executa_update()

    assert post_in.excerpt.startswith("Sberbank confirma plano")
    assert post_in.meta_title == "Sberbank Confirma Cripto"
    assert post_in.meta_description.startswith("Entenda o que o avanco")


@pytest.mark.asyncio
async def test_update_grava_source_url_da_nova_fonte():
    """
    Regressão: sem isso a URL da segunda fonte nunca entrava no banco, e o
    pré-filtro anti-reprocessamento (que busca por Post.source_url) deixava a
    mesma notícia ser regerada em todo run seguinte.
    """
    post_in = await _executa_update()

    assert post_in.source_url == "https://cointelegraph.com/sberbank-cripto"


@pytest.mark.asyncio
async def test_update_nao_altera_o_slug():
    """
    O slug é a URL pública. Trocá-lo quebraria links e histórico de SEO —
    título mudar sem o slug mudar é o comportamento correto.
    """
    post_in = await _executa_update()

    assert not hasattr(post_in, "slug") or post_in.slug is None


@pytest.mark.asyncio
async def test_update_trunca_meta_title_longo():
    """meta_title tem limite de 70 chars no schema; passar direto estouraria."""
    artigo = dict(ARTIGO_NOVO)
    artigo["meta_title"] = "T" * 120

    post_in = await _executa_update(artigo)

    assert len(post_in.meta_title) <= 70


@pytest.mark.asyncio
async def test_update_trunca_meta_description_longa():
    """meta_description tem limite de 160 chars no schema."""
    artigo = dict(ARTIGO_NOVO)
    artigo["meta_description"] = "D" * 300

    post_in = await _executa_update(artigo)

    assert len(post_in.meta_description) <= 160


@pytest.mark.asyncio
async def test_update_sem_source_url_nao_quebra():
    """
    Artigo sem source_url (caminho do relatório semanal, por exemplo) não pode
    fazer o update falhar.
    """
    artigo = dict(ARTIGO_NOVO)
    del artigo["source_url"]

    post_in = await _executa_update(artigo)

    assert post_in.source_url is None
