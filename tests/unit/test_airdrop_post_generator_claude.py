"""
Testa o caminho feliz do AirdropPostGenerator usando Claude.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator
from app.services.airdrop.web_researcher import ResearchResult


def _fake_claude_response(payload: dict):
    """Simula a estrutura de retorno do anthropic SDK."""
    response = MagicMock()
    block = MagicMock()
    block.text = json.dumps(payload)
    response.content = [block]
    return response


@pytest.mark.asyncio
async def test_generate_returns_article_dict_on_success():
    generator = AirdropPostGenerator()
    # força Claude disponível com client mockado
    generator.claude_available = True
    generator.claude_client = MagicMock()

    # Padding pra atingir faixa 500-750 palavras exigida por _post_validate.
    _filler = (" palavra" * 600).strip()
    article_payload = {
        "title": "LayerZero: o protocolo cross-chain e seu programa de airdrop",
        "slug": "layerzero-protocolo-cross-chain-airdrop",
        "excerpt": "Conheca o LayerZero, protocolo de interoperabilidade entre blockchains.",
        "content_markdown": (
            "Introducao curta sobre o projeto.\n\n"
            f"## Sobre o projeto LayerZero\n\nTexto. {_filler}\n\n"
            "## O programa de airdrop\n\nTexto.\n\n"
            "## Como participar\n\nAcesse [aqui](https://ref.example/abc) para se cadastrar.\n\n"
            "## Informações importantes\n\nSite oficial: [https://layerzero.network](https://layerzero.network). "
            "Este conteudo nao constitui recomendacao de investimento."
        ),
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "LayerZero e um protocolo de interoperabilidade. Saiba como participar "
            "do airdrop pelo site oficial."
        ),
    }

    generator.claude_client.messages = MagicMock()
    generator.claude_client.messages.create = AsyncMock(
        return_value=_fake_claude_response(article_payload)
    )

    research = ResearchResult(
        sources_text="=== FONTES ===\n[FONTE 1] x",
        sources_used=["https://layerzero.network"],
    )
    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_image", AsyncMock(return_value="https://img/x.jpg")):
            result = await generator.generate(
                project_name="LayerZero",
                official_url="https://layerzero.network",
                referral_url="https://ref.example/abc",
            )

    assert result is not None
    assert result["title"].startswith("LayerZero")
    assert "https://ref.example/abc" in result["content_markdown"]
    assert result["image_url"] == "https://img/x.jpg"
    assert result["sources_used"] == ["https://layerzero.network"]
    assert result["word_count"] >= 1


@pytest.mark.asyncio
async def test_generate_returns_none_when_claude_returns_invalid_json():
    generator = AirdropPostGenerator()
    generator.claude_available = True
    generator.claude_client = MagicMock()

    bad_response = MagicMock()
    block = MagicMock()
    block.text = "this is not json"
    bad_response.content = [block]

    generator.claude_client.messages = MagicMock()
    generator.claude_client.messages.create = AsyncMock(return_value=bad_response)
    # também desativa fallback Gemini pra isolar este teste
    generator.content_generator = None

    research = ResearchResult(sources_text="x", sources_used=["https://x.com"])
    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        result = await generator.generate(
            project_name="X",
            official_url="https://x.com",
            referral_url="https://x.com/r",
        )
    assert result is None
