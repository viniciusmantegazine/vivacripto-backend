"""
Testes do fallback Gemini quando Claude falha.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator
from app.services.airdrop.web_researcher import ResearchResult


@pytest.mark.asyncio
async def test_falls_back_to_gemini_when_claude_unavailable():
    generator = AirdropPostGenerator()
    # simula Claude indisponível
    generator.claude_available = False
    generator.claude_client = None

    # Padding pra atingir faixa 500-750 palavras exigida por _post_validate.
    _filler = (" palavra" * 600).strip()
    article_payload = {
        "title": "LayerZero airdrop: como participar pelo site oficial em 2026",
        "slug": "layerzero-airdrop-como-participar",
        "excerpt": "Conheca o LayerZero, protocolo de interoperabilidade entre blockchains, e como participar.",
        "content_markdown": (
            "Introducao.\n\n"
            f"## Sobre\n\nTexto sobre crypto e blockchain. {_filler}\n\n"
            "## O programa de airdrop\n\nTexto.\n\n"
            "## Como participar\n\nAcesse [aqui](https://ref.example/abc).\n\n"
            "## Informacoes importantes\n\n[https://layerzero.network](https://layerzero.network). "
            "Nao constitui recomendacao."
        ),
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "LayerZero, protocolo de interoperabilidade entre blockchains, abre cadastro "
            "antecipado para airdrop pelo site oficial."
        ),
    }

    # mock do método de fallback que vamos chamar
    mock_gemini = AsyncMock(return_value=article_payload)

    research = ResearchResult(sources_text="x", sources_used=["https://layerzero.network"])
    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_with_gemini", mock_gemini):
            with patch.object(generator, "_generate_image", AsyncMock(return_value=None)):
                result = await generator.generate(
                    project_name="LayerZero",
                    official_url="https://layerzero.network",
                    referral_url="https://ref.example/abc",
                )

    assert result is not None
    assert result["title"].startswith("LayerZero")
    mock_gemini.assert_called_once()


@pytest.mark.asyncio
async def test_returns_none_when_both_models_fail():
    generator = AirdropPostGenerator()
    generator.claude_available = False
    generator.claude_client = None

    research = ResearchResult(sources_text="x", sources_used=["https://x.com"])
    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_with_gemini", AsyncMock(return_value=None)):
            result = await generator.generate(
                project_name="X",
                official_url="https://x.com",
                referral_url="https://x.com/r",
            )
    assert result is None
