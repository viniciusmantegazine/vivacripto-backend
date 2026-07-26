"""
Testes da chamada única de geração.

Antes: três chamadas sequenciais (conteúdo, título SEO, meta description).
Se a segunda falhava, o artigo inteiro era descartado junto com a chamada de
conteúdo que já custara ~2500 tokens de saída. Agora é uma transação: ou vem
tudo, ou não vem nada.
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.content_generator import ContentGenerator

ARTIGO_JSON = json.dumps({
    "content_markdown": "## Manchete\n\n" + "palavra de conteudo " * 60,
    "title": "Bitcoin Atinge Máxima Histórica Após Aprovação de ETF",
    "excerpt": "Bitcoin renova máxima em meio a forte demanda institucional por ETFs listados.",
    "meta_description": "Entenda o que a nova máxima do Bitcoin significa para o investidor brasileiro e o que observar adiante.",
})


def _gerador_gemini(resposta_texto=ARTIGO_JSON, erro=None):
    """ContentGenerator com Gemini falso. Devolve (gen, chamadas)."""
    gen = ContentGenerator()
    chamadas = []

    async def generate_content(**kwargs):
        chamadas.append(kwargs)
        if erro is not None:
            raise erro
        resp = MagicMock()
        resp.text = resposta_texto
        return resp

    cliente = MagicMock()
    cliente.aio = MagicMock()
    cliente.aio.models = MagicMock()
    cliente.aio.models.generate_content = AsyncMock(side_effect=generate_content)

    gen.gemini_client = cliente
    gen.use_gemini = True
    return gen, chamadas


def _com_openai(gen, resposta_texto=ARTIGO_JSON):
    """Instala um cliente OpenAI falso e devolve a lista de chamadas."""
    chamadas = []

    async def create(**kwargs):
        chamadas.append(kwargs)
        msg = MagicMock()
        msg.message.content = resposta_texto
        resp = MagicMock()
        resp.choices = [msg]
        return resp

    gen.openai_client = MagicMock()
    gen.openai_client.chat = MagicMock()
    gen.openai_client.chat.completions = MagicMock()
    gen.openai_client.chat.completions.create = AsyncMock(side_effect=create)
    return chamadas


@pytest.mark.asyncio
async def test_faz_uma_unica_chamada():
    """O ponto central da consolidação: 1 chamada, não 3."""
    gen, chamadas = _gerador_gemini()

    resultado = await gen._generate_article_json(
        "Bitcoin Hits High", "texto da fonte", "CoinDesk", "bitcoin", None
    )

    assert resultado is not None
    assert len(chamadas) == 1


@pytest.mark.asyncio
async def test_pede_json_nativo_ao_gemini():
    """response_mime_type é o reforço nativo do contrato que vive no prompt."""
    gen, chamadas = _gerador_gemini()

    await gen._generate_article_json("t", "d", "s", "bitcoin", None)

    config = chamadas[0]["config"]
    assert config.response_mime_type == "application/json"


@pytest.mark.asyncio
async def test_contrato_dos_quatro_campos_esta_no_prompt():
    gen, chamadas = _gerador_gemini()

    await gen._generate_article_json("t", "d", "s", "bitcoin", None)

    prompt = chamadas[0]["contents"]
    for campo in ("content_markdown", "title", "excerpt", "meta_description"):
        assert campo in prompt, f"campo {campo} ausente do contrato no prompt"


@pytest.mark.asyncio
async def test_correction_hint_entra_no_prompt():
    """
    Em retry pós-reprovação o hint precisa chegar ao modelo. Substitui o teste
    equivalente que apontava para _generate_content.
    """
    gen, chamadas = _gerador_gemini()

    await gen._generate_article_json(
        "t", "d", "s", "bitcoin", "word count abaixo do minimo"
    )

    assert "word count abaixo do minimo" in chamadas[0]["contents"]


@pytest.mark.asyncio
async def test_sem_hint_nao_injeta_bloco_de_correcao():
    gen, chamadas = _gerador_gemini()

    await gen._generate_article_json("t", "d", "s", "bitcoin", None)

    assert "<correcao_obrigatoria>" not in chamadas[0]["contents"]


@pytest.mark.asyncio
async def test_fallback_openai_quando_gemini_falha():
    """Mesmo contrato nos dois provedores — é por isso que ele vive no prompt."""
    gen, chamadas_gemini = _gerador_gemini(erro=RuntimeError("429 rate limit"))
    chamadas_openai = _com_openai(gen)

    resultado = await gen._generate_article_json("t", "d", "s", "bitcoin", None)

    assert resultado is not None
    assert resultado["title"].startswith("Bitcoin Atinge")
    assert len(chamadas_gemini) == 1
    assert len(chamadas_openai) == 1
    assert chamadas_openai[0]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_resposta_nao_json_retorna_none():
    gen, _ = _gerador_gemini(resposta_texto="desculpe, não posso ajudar")
    _com_openai(gen, resposta_texto="também não")

    assert await gen._generate_article_json("t", "d", "s", "bitcoin", None) is None
