"""
Testes da validação de word count integrada ao _post_validate.

Antes, _post_validate checava só URLs e disclosure. Word count era checado
só no endpoint (QualityValidator), que retornava 422 sem retry. Agora a
checagem entra no _post_validate pra disparar regenerate-once com hint.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator
from app.services.airdrop.web_researcher import ResearchResult


def _article(content_markdown: str) -> dict:
    return {
        "title": "LayerZero airdrop: o que e e como participar do programa em 2026",
        "slug": "layerzero-airdrop-2026",
        "excerpt": "Conheca o LayerZero e como participar do programa de airdrop pelo site oficial.",
        "content_markdown": content_markdown,
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "LayerZero abre cadastro para airdrop. Saiba o que e o protocolo e como "
            "participar pelo site oficial."
        ),
    }


def _well_formed_content(word_filler_count: int) -> str:
    """
    Gera content_markdown estruturalmente válido (URLs + disclosure) com
    contagem de palavras alvo via filler. Útil pra exercitar limite superior/inferior.
    """
    base = (
        "Intro.\n\n## Sobre\n\nTexto sobre crypto blockchain.\n\n"
        "## Como participar\n\nAcesse [aqui](https://ref.example/abc).\n\n"
        "## Informações importantes\n\n"
        "Site oficial: [https://layerzero.network](https://layerzero.network). "
        "Este conteudo nao constitui recomendacao de investimento."
    )
    filler = " palavra" * word_filler_count
    return base + filler


def test_post_validate_flags_content_above_max_words():
    """924 palavras (> 750) deveria gerar erro."""
    g = AirdropPostGenerator.__new__(AirdropPostGenerator)
    # base tem ~30 palavras, +800 filler → ~830 palavras (acima de 750)
    article = _article(_well_formed_content(word_filler_count=800))
    errors = g._post_validate(
        article,
        referral_url="https://ref.example/abc",
        official_url="https://layerzero.network",
    )
    assert any("750" in e or "muito longo" in e for e in errors), errors


def test_post_validate_flags_content_below_min_words():
    """~30 palavras (< 500) deveria gerar erro."""
    g = AirdropPostGenerator.__new__(AirdropPostGenerator)
    article = _article(_well_formed_content(word_filler_count=0))  # ~30 palavras
    errors = g._post_validate(
        article,
        referral_url="https://ref.example/abc",
        official_url="https://layerzero.network",
    )
    assert any("500" in e or "muito curto" in e for e in errors), errors


def test_post_validate_accepts_content_within_word_range():
    """620 palavras (entre 500 e 750) não deve gerar erro de word count."""
    g = AirdropPostGenerator.__new__(AirdropPostGenerator)
    # base ~30 + 590 filler → ~620 palavras
    article = _article(_well_formed_content(word_filler_count=590))
    errors = g._post_validate(
        article,
        referral_url="https://ref.example/abc",
        official_url="https://layerzero.network",
    )
    # se houver erro, NÃO pode ser de word count
    for e in errors:
        assert "palavras" not in e and "muito longo" not in e and "muito curto" not in e, (
            f"erro inesperado de word count: {e}"
        )


@pytest.mark.asyncio
async def test_generator_regenerates_once_when_word_count_too_high():
    """
    Cenário do bug real: LLM gera ~830 palavras. _post_validate dispara
    regenerate-once com hint, segunda geração fica dentro da faixa.
    """
    generator = AirdropPostGenerator()
    generator.claude_available = True
    generator.claude_client = MagicMock()

    too_long = _article(_well_formed_content(word_filler_count=800))   # ~830 palavras
    ok = _article(_well_formed_content(word_filler_count=590))         # ~620 palavras

    calls = {"n": 0}

    async def fake_with_claude(prompt: str):
        calls["n"] += 1
        return too_long if calls["n"] == 1 else ok

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
    assert calls["n"] == 2, "deveria regenerar exatamente uma vez por word count alto"
    assert 500 <= result["word_count"] <= 750
