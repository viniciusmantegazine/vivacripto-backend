"""
Integracao do filtro de relevancia no NewsAggregator.

O que importa aqui e a POSICAO: o filtro roda entre a coleta e a
deduplicacao. Antes do dedup porque ele e O(n^2), e porque o agregador e o
funil unico de RSS + API.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.sources.news_aggregator import NewsAggregator


def _noticia(titulo, descricao="", fonte="Decrypt"):
    return {
        "source": fonte,
        "title": titulo,
        "description": descricao,
        "url": f"https://exemplo/{abs(hash(titulo))}",
        "published_at": None,
    }


@pytest.fixture
def aggregator():
    agg = NewsAggregator()
    agg.rss_collector = MagicMock()
    agg.rss_collector.collect_all = AsyncMock(return_value=[])
    agg.api_collector = MagicMock()
    agg.api_collector.collect_all = AsyncMock(return_value=[])
    return agg


@pytest.mark.asyncio
async def test_item_fora_de_tema_nao_chega_ao_dedup(aggregator):
    ia = _noticia(
        "Alibaba's New Qwen Image 3 AI Wants to Be Useful, Not Just Pretty",
        "Qwen Image 3.0 generates dense newspapers and infographic grids.",
    )
    cripto = _noticia("Bitcoin atinge nova maxima", "BTC sobe forte hoje.")
    aggregator.rss_collector.collect_all = AsyncMock(return_value=[ia, cripto])

    vistos = {}

    def _espia(lista):
        vistos["titulos"] = [n["title"] for n in lista]
        return lista

    aggregator._deduplicate_source_news = _espia

    resultado = await aggregator.collect_news(hours_back=24)

    assert vistos["titulos"] == ["Bitcoin atinge nova maxima"]
    assert len(resultado) == 1


@pytest.mark.asyncio
async def test_fila_toda_no_tema_passa_intacta(aggregator):
    noticias = [
        _noticia("Bitcoin atinge nova maxima", "BTC sobe."),
        _noticia("Ethereum conclui atualizacao", "ETH melhora."),
    ]
    aggregator.rss_collector.collect_all = AsyncMock(return_value=noticias)
    aggregator._deduplicate_source_news = lambda lista: lista

    resultado = await aggregator.collect_news(hours_back=24)

    assert len(resultado) == 2


@pytest.mark.asyncio
async def test_cada_descarte_e_logado(aggregator):
    """
    Este projeto ja calibrou dois thresholds fora da faixa do dado real
    (SOURCE_DEDUP_THRESHOLD a 0,65 e DEDUPLICATION_THRESHOLD a 0,80) e nos dois
    casos o sintoma foi SILENCIO. Gate mal calibrado comendo noticia e o mesmo
    modo de falha, com consequencia pior — entao cada descarte deixa rastro.
    """
    from loguru import logger

    linhas = []
    sink_id = logger.add(lambda m: linhas.append(m), level="WARNING")
    try:
        aggregator.rss_collector.collect_all = AsyncMock(
            return_value=[_noticia("Nvidia unveils new GPU for AI labs", "")]
        )
        aggregator._deduplicate_source_news = lambda lista: lista

        await aggregator.collect_news(hours_back=24)
    finally:
        logger.remove(sink_id)

    texto = "".join(linhas)
    assert "casou 'AI labs'" in texto
