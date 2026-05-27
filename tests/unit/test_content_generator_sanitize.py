"""Unit tests for ContentGenerator: sanitizer and correction-hint retry."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.content_generator import ContentGenerator


@pytest.fixture
def generator() -> ContentGenerator:
    return ContentGenerator()


def test_sanitize_preserves_double_line_breaks(generator: ContentGenerator):
    """Regression: cleanup regex must NOT collapse \\n\\n.

    Bug: re.sub(r'\\s{2,}', ' ', ...) was collapsing paragraph breaks,
    causing quality_validator to reject articles with "0 quebra(s) dupla(s)".
    """
    content = (
        "## Manchete H2\n\n"
        "Primeiro parágrafo do lead jornalístico.\n\n"
        "## Contexto\n\n"
        "Segundo parágrafo com detalhes.\n\n"
        "## Impacto no Brasil\n\n"
        "Terceiro parágrafo."
    )

    result = generator._sanitize_content(content)

    assert result.count("\n\n") >= 2, (
        f"Sanitize collapsed paragraph breaks. Got {result.count(chr(10) * 2)} "
        f"double breaks. Output: {result[:200]!r}"
    )


def test_sanitize_collapses_inline_double_spaces(generator: ContentGenerator):
    """Inline double-spaces should still be collapsed to a single space."""
    content = "## Título\n\nPrimeiro  parágrafo   com   espaços.\n\nSegundo."

    result = generator._sanitize_content(content)

    assert "  " not in result
    assert result.count("\n\n") >= 2


def test_sanitize_removes_site_mention_and_keeps_breaks(generator: ContentGenerator):
    """Removing a banned outlet must not destroy paragraph structure."""
    content = (
        "## Manchete\n\n"
        "Segundo o CoinDesk, o Bitcoin atingiu novo recorde.\n\n"
        "## Contexto\n\n"
        "Segundo parágrafo aqui."
    )

    result = generator._sanitize_content(content)

    assert "CoinDesk" not in result
    assert result.count("\n\n") >= 2


@pytest.mark.asyncio
async def test_generate_content_injects_correction_hint_in_prompt(
    generator: ContentGenerator,
):
    """When correction_hint is passed, the LLM must receive a <correcao_obrigatoria>
    block. Otherwise the regenerate-once retry in news_pipeline can't push the
    LLM to fix the previous failure (e.g., word count below minimum).
    """
    fake_response = MagicMock()
    fake_response.text = "## Manchete\n\nCorpo gerado.\n\n## Mais\n\nFinal."

    generator.gemini_client = MagicMock()
    generator.gemini_client.aio.models.generate_content = AsyncMock(
        return_value=fake_response
    )
    generator.use_gemini = True

    await generator._generate_content(
        title="Bitcoin sobe",
        description="Detalhes da notícia.",
        source="example.com",
        category="bitcoin",
        correction_hint="Conteúdo muito curto (602 palavras, mínimo 700)",
    )

    sent_prompt = generator.gemini_client.aio.models.generate_content.await_args.kwargs[
        "contents"
    ]
    assert "<correcao_obrigatoria>" in sent_prompt
    assert "602 palavras" in sent_prompt
    assert "EXPANDA" in sent_prompt


@pytest.mark.asyncio
async def test_generate_content_omits_correction_block_when_no_hint(
    generator: ContentGenerator,
):
    """First-attempt generations should NOT carry the correction block."""
    fake_response = MagicMock()
    fake_response.text = "## Manchete\n\nCorpo.\n\n## Mais\n\nFinal."

    generator.gemini_client = MagicMock()
    generator.gemini_client.aio.models.generate_content = AsyncMock(
        return_value=fake_response
    )
    generator.use_gemini = True

    await generator._generate_content(
        title="Bitcoin sobe",
        description="Detalhes.",
        source="example.com",
        category="bitcoin",
    )

    sent_prompt = generator.gemini_client.aio.models.generate_content.await_args.kwargs[
        "contents"
    ]
    assert "<correcao_obrigatoria>" not in sent_prompt
