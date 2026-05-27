"""Unit tests for ContentGenerator._sanitize_content."""
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
