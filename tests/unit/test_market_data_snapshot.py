"""
Testes do collect_snapshot — o subconjunto de dados de mercado que serve ao
pipeline de notícias.

collect_all() leva 7,0s, dos quais 5,9s são cinco buscas no DuckDuckGo para
contexto macro (Fed, CPI, S&P, DXY, ETF). Isso é material de análise semanal;
para um artigo de notícia é ruído caro. collect_snapshot faz só as 3 chamadas
HTTP (1,1s).

O teste que mais importa aqui é o primeiro: ele é o que impede alguém de
"simplificar" collect_snapshot chamando collect_all e trazer os 5,9s de volta.
"""
import pytest

from app.services.ai.market_data_collector import MarketDataCollector


@pytest.fixture
def collector() -> MarketDataCollector:
    return MarketDataCollector()


def _mock_fetches(monkeypatch, collector, precos="PREÇOS: BTC US$ 64.640",
                  glob="GLOBAL: cap US$ 2.1T", fng="FEAR & GREED: 54 (neutro)",
                  macro="MACRO: Fed manteve juros"):
    """Substitui os quatro coletores. Devolve o registro de quem foi chamado."""
    chamados = []

    async def _precos(client):
        chamados.append("precos")
        return precos

    async def _glob(client):
        chamados.append("global")
        return glob

    async def _fng(client):
        chamados.append("fng")
        return fng

    async def _macro():
        chamados.append("macro")
        return macro

    monkeypatch.setattr(collector, "_fetch_crypto_prices", _precos)
    monkeypatch.setattr(collector, "_fetch_global_crypto", _glob)
    monkeypatch.setattr(collector, "_fetch_fear_greed", _fng)
    monkeypatch.setattr(collector, "_search_macro_context", _macro)
    return chamados


@pytest.mark.asyncio
async def test_snapshot_nao_dispara_a_busca_macro(monkeypatch, collector):
    """
    Guarda dos 5,9s. Se alguém reescrever collect_snapshot como um alias de
    collect_all, este teste acusa.
    """
    chamados = _mock_fetches(monkeypatch, collector)

    await collector.collect_snapshot()

    assert "macro" not in chamados, f"macro foi chamado: {chamados}"
    assert set(chamados) == {"precos", "global", "fng"}


@pytest.mark.asyncio
async def test_snapshot_traz_as_tres_secoes(monkeypatch, collector):
    _mock_fetches(monkeypatch, collector)

    resultado = await collector.collect_snapshot()

    assert "PREÇOS" in resultado
    assert "GLOBAL" in resultado
    assert "FEAR & GREED" in resultado
    assert "MACRO" not in resultado


@pytest.mark.asyncio
async def test_snapshot_tem_cabecalho_com_timestamp(monkeypatch, collector):
    """O artigo precisa saber que o dado é do momento, não histórico."""
    _mock_fetches(monkeypatch, collector)

    resultado = await collector.collect_snapshot()

    assert "DADOS DE MERCADO COLETADOS EM" in resultado
    assert "UTC" in resultado


@pytest.mark.asyncio
async def test_snapshot_devolve_none_quando_tudo_falha(monkeypatch, collector):
    """
    NÃO devolve o texto de fallback do collect_all ("NOTA: não foi possível...
    use seu conhecimento mais recente"). Aquele texto é escrito para o
    relatório semanal; num artigo de notícia viraria licença para o modelo
    especular com conhecimento de treino, que é o oposto do guardrail.
    """
    _mock_fetches(monkeypatch, collector, precos=None, glob=None, fng=None)

    assert await collector.collect_snapshot() is None


@pytest.mark.asyncio
async def test_snapshot_com_falha_parcial_devolve_o_que_coletou(monkeypatch, collector):
    """Preço ok e Fear & Greed fora do ar ainda é dado útil."""
    _mock_fetches(monkeypatch, collector, glob=None, fng=None)

    resultado = await collector.collect_snapshot()

    assert resultado is not None
    assert "PREÇOS" in resultado
    assert "FEAR & GREED" not in resultado


@pytest.mark.asyncio
async def test_collect_all_continua_trazendo_o_macro(monkeypatch, collector):
    """
    Guarda do relatório semanal: ele é o consumidor legítimo do macro, e o
    refactor não pode tirá-lo por engano.
    """
    chamados = _mock_fetches(monkeypatch, collector)

    resultado = await collector.collect_all()

    assert "macro" in chamados
    assert "MACRO" in resultado


@pytest.mark.asyncio
async def test_collect_all_mantem_o_texto_de_fallback(monkeypatch, collector):
    """O contrato do relatório semanal em falha total não muda: string, não None."""
    _mock_fetches(monkeypatch, collector, precos=None, glob=None, fng=None, macro=None)

    resultado = await collector.collect_all()

    assert isinstance(resultado, str)
    assert "Não foi possível coletar" in resultado
