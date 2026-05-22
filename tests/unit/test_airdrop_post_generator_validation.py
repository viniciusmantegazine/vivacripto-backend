"""
Testes da validação pós-geração (link de referência + link oficial + disclosure).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator
from app.services.airdrop.web_researcher import ResearchResult


def _article(content: str) -> dict:
    return {
        "title": "LayerZero airdrop: o que e e como participar do programa em 2026",
        "slug": "layerzero-airdrop-2026",
        "excerpt": "Conheca o LayerZero e como participar do programa de airdrop pelo site oficial.",
        "content_markdown": content,
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "LayerZero abre cadastro para airdrop. Saiba o que e o protocolo e como "
            "participar pelo site oficial."
        ),
    }


@pytest.mark.asyncio
async def test_regenerates_when_referral_url_missing():
    generator = AirdropPostGenerator()
    generator.claude_available = True
    generator.claude_client = MagicMock()

    bad = _article(
        "Intro.\n\n## Sobre\n\nTexto.\n\n"
        "## Como participar\n\nAcesse o site oficial.\n\n"
        "## Informações importantes\n\n[https://layerzero.network](https://layerzero.network). "
        "Nao constitui recomendacao."
    )
    good = _article(
        "Intro.\n\n## Sobre\n\nTexto.\n\n"
        "## Como participar\n\nAcesse [aqui](https://ref.example/abc).\n\n"
        "## Informações importantes\n\n[https://layerzero.network](https://layerzero.network). "
        "Nao constitui recomendacao."
    )

    call_count = {"n": 0}

    async def fake_with_claude(prompt: str):
        call_count["n"] += 1
        return bad if call_count["n"] == 1 else good

    research = ResearchResult(sources_text="x", sources_used=["https://layerzero.network"])

    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_with_claude", side_effect=fake_with_claude):
            with patch.object(generator, "_generate_image", AsyncMock(return_value=None)):
                result = await generator.generate(
                    project_name="LayerZero",
                    official_url="https://layerzero.network",
                    referral_url="https://ref.example/abc",
                )

    assert result is not None
    assert "https://ref.example/abc" in result["content_markdown"]
    assert call_count["n"] == 2, "Should regenerate exactly once when referral missing"


@pytest.mark.asyncio
async def test_returns_none_when_validation_fails_twice():
    generator = AirdropPostGenerator()
    generator.claude_available = True
    generator.claude_client = MagicMock()

    bad = _article(
        "Intro.\n\n## Como participar\n\nVeja o site.\n\n## Informações importantes\n\nx"
    )

    research = ResearchResult(sources_text="x", sources_used=["https://x.com"])

    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_with_claude", AsyncMock(return_value=bad)):
            with patch.object(generator, "_generate_with_gemini", AsyncMock(return_value=bad)):
                with patch.object(generator, "_generate_image", AsyncMock(return_value=None)):
                    result = await generator.generate(
                        project_name="X",
                        official_url="https://x.com",
                        referral_url="https://x.com/r",
                    )
    assert result is None


@pytest.mark.asyncio
async def test_accepts_article_with_referral_official_and_disclosure_string():
    generator = AirdropPostGenerator()
    generator.claude_available = True
    generator.claude_client = MagicMock()

    good = _article(
        "Intro.\n\n## Sobre\n\nTexto.\n\n## O programa de airdrop\n\nTexto.\n\n"
        "## Como participar\n\nAcesse [aqui](https://ref.example/abc).\n\n"
        "## Informações importantes\n\nSite oficial: [https://x.com](https://x.com). "
        "Este conteudo não constitui recomendação de investimento."
    )

    research = ResearchResult(sources_text="x", sources_used=["https://x.com"])
    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_with_claude", AsyncMock(return_value=good)):
            with patch.object(generator, "_generate_image", AsyncMock(return_value=None)):
                result = await generator.generate(
                    project_name="X",
                    official_url="https://x.com",
                    referral_url="https://ref.example/abc",
                )
    assert result is not None
