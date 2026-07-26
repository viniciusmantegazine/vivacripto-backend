"""
Testes do ranking do NewsAggregator: a deduplicação de fontes deve CONTAR
quantas fontes cobriram cada tema (source_count) e ordenar por relevância
(mais fontes primeiro; empate -> mais recente).
"""
from datetime import datetime, timedelta, timezone

from app.services.sources.news_aggregator import NewsAggregator


class _StubResult:
    def __init__(self, score):
        self.score = score


class _StubEngine:
    """Considera duplicatas textos cujo primeiro token (marcador) coincide."""

    def calculate(self, a, b):
        return _StubResult(1.0 if a.split()[0] == b.split()[0] else 0.0)


def _news(source, title, description, hours_ago):
    return {
        "source": source,
        "title": title,
        "description": description,
        "published_at": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        "url": f"https://{source.lower().replace(' ', '')}.com/x",
    }


def _aggregator_with_stub(monkeypatch):
    agg = NewsAggregator()
    monkeypatch.setattr(agg, "_get_similarity_engine", lambda: _StubEngine())
    return agg


def test_conta_fontes_e_mantem_descricao_mais_completa(monkeypatch):
    agg = _aggregator_with_stub(monkeypatch)
    items = [
        _news("CoinDesk", "TEMA1 bitcoin etf aprovado", "curta", 5),
        _news("Decrypt", "TEMA1 bitcoin etf liberado",
              "descrição bem mais longa e completa sobre o assunto", 4),
        _news("CryptoSlate", "TEMA2 ethereum upgrade", "outra coisa", 1),
    ]

    result = agg._deduplicate_source_news(items)

    assert len(result) == 2
    tema1 = next(n for n in result if n["title"].startswith("TEMA1"))
    assert tema1["source_count"] == 2
    assert set(tema1["covered_by"]) == {"CoinDesk", "Decrypt"}
    # Mantém a versão com descrição mais completa, sem perder a contagem
    assert tema1["description"].startswith("descrição bem mais longa")


def test_ordena_por_cobertura_depois_recencia(monkeypatch):
    agg = _aggregator_with_stub(monkeypatch)
    items = [
        _news("CryptoSlate", "TEMA2 ethereum upgrade", "single source", 1),  # mais recente
        _news("CoinDesk", "TEMA1 bitcoin etf", "desc a", 5),
        _news("Decrypt", "TEMA1 bitcoin etf tambem", "desc b", 4),
    ]

    result = agg._deduplicate_source_news(items)

    # TEMA1 tem 2 fontes -> vem primeiro, mesmo TEMA2 sendo mais recente
    assert result[0]["title"].startswith("TEMA1")
    assert result[0]["source_count"] == 2
    assert result[1]["source_count"] == 1


def test_sem_engine_retorna_tudo_com_count_1(monkeypatch):
    agg = NewsAggregator()
    monkeypatch.setattr(agg, "_get_similarity_engine", lambda: None)
    items = [
        _news("CoinDesk", "TEMA1 bitcoin", "a", 1),
        _news("Decrypt", "TEMA1 bitcoin igual", "b", 2),
    ]

    result = agg._deduplicate_source_news(items)

    assert len(result) == 2
    assert all(n["source_count"] == 1 for n in result)
