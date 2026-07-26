"""
Testes do generate_article: preferência por full_text e descarte de artigo
quando o título SEO não pôde ser gerado (o fallback seria o título original
em INGLÊS do feed — inaceitável em portal PT-BR).
"""
import pytest

from app.services.ai.content_generator import ContentGenerator

VALID_CONTENT = (
    "## Bitcoin em alta\n\nO Bitcoin subiu nesta semana. "
    + "Contexto adicional do mercado de criptomoedas no Brasil. " * 40
)


def _news(**extra):
    news = {
        "title": "Bitcoin Hits New All-Time High",
        "description": "resumo curto do RSS",
        "source": "CoinDesk",
        "url": "https://coindesk.com/noticia",
    }
    news.update(extra)
    return news


@pytest.mark.asyncio
async def test_prefere_full_text_sobre_description(monkeypatch):
    gen = ContentGenerator()
    captured = {}

    async def fake_content(title, description, source, category="default",
                           correction_hint=None):
        captured["description"] = description
        return VALID_CONTENT

    async def fake_title(content, keyword="criptomoeda"):
        return "Bitcoin Sobe Forte Após Aprovação de ETF nos EUA"

    async def fake_meta(content, title="", keyword="criptomoeda"):
        return "Meta description de teste com tamanho adequado para SEO e CTR."

    monkeypatch.setattr(gen, "_generate_content", fake_content)
    monkeypatch.setattr(gen, "_generate_seo_title", fake_title)
    monkeypatch.setattr(gen, "_generate_meta_description", fake_meta)

    article = await gen.generate_article(
        _news(full_text="texto completo extraído da matéria original")
    )

    assert article is not None
    assert captured["description"] == "texto completo extraído da matéria original"


@pytest.mark.asyncio
async def test_sem_full_text_usa_description(monkeypatch):
    gen = ContentGenerator()
    captured = {}

    async def fake_content(title, description, source, category="default",
                           correction_hint=None):
        captured["description"] = description
        return VALID_CONTENT

    async def fake_title(content, keyword="criptomoeda"):
        return "Bitcoin Sobe Forte Após Aprovação de ETF nos EUA"

    async def fake_meta(content, title="", keyword="criptomoeda"):
        return "Meta description de teste com tamanho adequado para SEO e CTR."

    monkeypatch.setattr(gen, "_generate_content", fake_content)
    monkeypatch.setattr(gen, "_generate_seo_title", fake_title)
    monkeypatch.setattr(gen, "_generate_meta_description", fake_meta)

    article = await gen.generate_article(_news())

    assert article is not None
    assert captured["description"] == "resumo curto do RSS"


@pytest.mark.asyncio
async def test_descarta_artigo_sem_titulo_seo(monkeypatch):
    """Sem título SEO, o fallback seria o título em inglês — descartar."""
    gen = ContentGenerator()

    async def fake_content(*args, **kwargs):
        return VALID_CONTENT

    async def fake_title(*args, **kwargs):
        return None

    monkeypatch.setattr(gen, "_generate_content", fake_content)
    monkeypatch.setattr(gen, "_generate_seo_title", fake_title)

    assert await gen.generate_article(_news()) is None
