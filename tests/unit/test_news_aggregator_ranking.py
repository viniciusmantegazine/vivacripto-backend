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


class _StubEngineComScore:
    """Engine que devolve um score fixo, para exercitar o threshold."""

    def __init__(self, score):
        self._score = score

    def calculate(self, a, b):
        return _StubResult(self._score)


def test_threshold_esta_na_faixa_medida():
    """
    Regressão: com 0.65 o threshold NUNCA disparava.

    Medido sobre 3525 pares cross-fonte reais (96 notícias, janela de 72h):
    o par de mesma notícia com maior similaridade marcou 0.525, então nada
    passava de 0.65 e o ranking por source_count ficava inerte — todo
    source_count valia 1 e a ordenação degenerava para recência pura.

    Na mesma medição o primeiro falso positivo (notícias distintas) aparece
    em 0.403, e há duplicatas verdadeiras até 0.384: as faixas se sobrepõem,
    não existe corte limpo. A faixa abaixo é onde 0 falsos positivos foram
    observados com recall útil.
    """
    assert 0.40 <= NewsAggregator.SOURCE_DEDUP_THRESHOLD < 0.50


def test_par_acima_do_threshold_e_tratado_como_duplicata(monkeypatch):
    """Score plausível de mesma notícia (0.46) deve casar e somar fontes."""
    agg = NewsAggregator()
    monkeypatch.setattr(agg, "_get_similarity_engine", lambda: _StubEngineComScore(0.46))
    items = [
        _news("CoinDesk", "Sberbank lanca infra de cripto", "desc a", 5),
        _news("Cointelegraph", "Sberbank vai lancar infra de cripto", "desc b", 4),
    ]

    result = agg._deduplicate_source_news(items)

    assert len(result) == 1
    assert result[0]["source_count"] == 2


def test_par_abaixo_do_threshold_nao_e_duplicata(monkeypatch):
    """
    Score de notícias distintas (0.40) não pode casar.

    Este é o lado caro do erro: falso positivo DESCARTA uma notícia
    distinta, e o leitor nunca a vê.
    """
    agg = NewsAggregator()
    monkeypatch.setattr(agg, "_get_similarity_engine", lambda: _StubEngineComScore(0.40))
    items = [
        _news("CryptoSlate", "Panorama do mercado hoje", "desc a", 5),
        _news("Decrypt", "Polymarket sob investigacao", "desc b", 4),
    ]

    result = agg._deduplicate_source_news(items)

    assert len(result) == 2
    assert all(n["source_count"] == 1 for n in result)


def test_mesma_fonte_repetida_nao_infla_source_count(monkeypatch):
    """
    Regressão: o dedup NÃO pula pares da mesma fonte, então três artigos
    parecidos do mesmo veículo mergeavam e produziam source_count=3 com
    covered_by=['CryptoSlate','CryptoSlate','CryptoSlate'].

    Isso invertia a premissa do ranking: um veículo se repetindo (digest,
    matérias relacionadas) ganhava o topo da fila sobre notícia realmente
    coberta por múltiplas fontes.
    """
    agg = _aggregator_with_stub(monkeypatch)
    items = [
        _news("CryptoSlate", "TEMA1 panorama do mercado", "desc a", 5),
        _news("CryptoSlate", "TEMA1 panorama detalhado", "desc b bem mais longa", 4),
        _news("CryptoSlate", "TEMA1 panorama complementar", "desc c", 3),
    ]

    result = agg._deduplicate_source_news(items)

    assert len(result) == 1
    assert result[0]["source_count"] == 1, "3 artigos de 1 fonte não são 3 fontes"
    assert result[0]["covered_by"] == ["CryptoSlate"]


def test_source_count_conta_fontes_distintas(monkeypatch):
    """Fonte repetida no meio de fontes distintas não deve ser contada 2x."""
    agg = _aggregator_with_stub(monkeypatch)
    items = [
        _news("CoinDesk", "TEMA1 sberbank cripto", "desc a", 6),
        _news("Cointelegraph", "TEMA1 sberbank infra", "desc b", 5),
        _news("CoinDesk", "TEMA1 sberbank detalhes", "desc c", 4),
    ]

    result = agg._deduplicate_source_news(items)

    assert len(result) == 1
    assert result[0]["source_count"] == 2
    assert result[0]["covered_by"] == ["CoinDesk", "Cointelegraph"]


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
