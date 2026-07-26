"""
Testes do generate_article com a chamada única.

Os testes anteriores mockavam _generate_content, _generate_seo_title e
_generate_meta_description — três métodos que deixaram de existir. Agora
mockam o único ponto de contato com o LLM: _generate_article_json.
"""
import pytest

from app.services.ai.content_generator import ContentGenerator

CONTEUDO = "## Bitcoin em alta\n\n" + "Contexto do mercado de criptomoedas no Brasil. " * 40


def _json_do_llm(**overrides):
    dados = {
        "content_markdown": CONTEUDO,
        "title": "Bitcoin Sobe Forte Após Aprovação de ETF nos EUA",
        "excerpt": "Bitcoin renova máxima em meio a forte demanda institucional por ETFs listados na bolsa americana.",
        "meta_description": "Entenda o que a alta do Bitcoin significa para o investidor brasileiro e o que observar nos próximos meses.",
    }
    dados.update(overrides)
    return dados


def _news(**extra):
    news = {
        "title": "Bitcoin Hits New All-Time High",
        "description": "resumo curto do RSS",
        "source": "CoinDesk",
        "url": "https://coindesk.com/noticia",
    }
    news.update(extra)
    return news


def _gen_com_json(monkeypatch, payload, capturado=None):
    gen = ContentGenerator()

    async def fake(title, description, source, category="default", correction_hint=None):
        if capturado is not None:
            capturado["description"] = description
            capturado["correction_hint"] = correction_hint
        return payload

    monkeypatch.setattr(gen, "_generate_article_json", fake)
    return gen


@pytest.mark.asyncio
async def test_monta_o_artigo_a_partir_do_json(monkeypatch):
    gen = _gen_com_json(monkeypatch, _json_do_llm())

    article = await gen.generate_article(_news())

    assert article["title"] == "Bitcoin Sobe Forte Após Aprovação de ETF nos EUA"
    assert article["meta_title"] == article["title"]
    assert article["slug"] == "bitcoin-sobe-forte-apos-aprovacao-de-etf-nos-eua"
    assert article["source_url"] == "https://coindesk.com/noticia"
    assert article["source_name"] == "CoinDesk"


@pytest.mark.asyncio
async def test_prefere_full_text_sobre_description(monkeypatch):
    """O texto completo da matéria original é melhor material que o resumo RSS."""
    capturado = {}
    gen = _gen_com_json(monkeypatch, _json_do_llm(), capturado)

    await gen.generate_article(_news(full_text="texto completo extraído da matéria"))

    assert capturado["description"] == "texto completo extraído da matéria"


@pytest.mark.asyncio
async def test_sem_full_text_usa_description(monkeypatch):
    capturado = {}
    gen = _gen_com_json(monkeypatch, _json_do_llm(), capturado)

    await gen.generate_article(_news())

    assert capturado["description"] == "resumo curto do RSS"


@pytest.mark.asyncio
async def test_json_nulo_descarta_o_artigo(monkeypatch):
    """Sem JSON aproveitável não há artigo — o pipeline tenta a próxima notícia."""
    gen = _gen_com_json(monkeypatch, None)

    assert await gen.generate_article(_news()) is None


@pytest.mark.asyncio
async def test_conteudo_passa_pela_sanitizacao(monkeypatch):
    """
    _sanitize_content rodava dentro de _generate_content. Ao mover a geração
    para o JSON, era fácil perder essa etapa — este teste é a guarda.
    """
    gen = _gen_com_json(
        monkeypatch,
        _json_do_llm(content_markdown="## Manchete\n\nSegundo o CoinDesk, o preço subiu."),
    )

    article = await gen.generate_article(_news())

    assert "CoinDesk" not in article["content_markdown"]


@pytest.mark.asyncio
async def test_excerpt_do_llm_e_usado_quando_esta_na_faixa(monkeypatch):
    gen = _gen_com_json(monkeypatch, _json_do_llm())

    article = await gen.generate_article(_news())

    assert article["excerpt"].startswith("Bitcoin renova máxima")


@pytest.mark.asyncio
@pytest.mark.parametrize("excerpt_ruim", [None, "curto demais", "x" * 250])
async def test_excerpt_fora_da_faixa_cai_no_fallback_mecanico(monkeypatch, excerpt_ruim):
    """
    O validador exige 80 a 200 chars. Excerpt fora disso é derivado do
    conteúdo em vez de descartar o artigo inteiro — mesmo princípio que
    motiva a consolidação.
    """
    gen = _gen_com_json(monkeypatch, _json_do_llm(excerpt=excerpt_ruim))

    article = await gen.generate_article(_news())

    assert article is not None
    assert article["excerpt"] != excerpt_ruim
    assert article["excerpt"].startswith("Contexto do mercado")


@pytest.mark.asyncio
async def test_correction_hint_e_repassado(monkeypatch):
    capturado = {}
    gen = _gen_com_json(monkeypatch, _json_do_llm(), capturado)

    await gen.generate_article(_news(), correction_hint="word count baixo")

    assert capturado["correction_hint"] == "word count baixo"
