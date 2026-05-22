"""
Testes para parametrização do QualityValidator com word range customizado
"""
import pytest

from app.services.automation.quality_validator import QualityValidator


def _article_with_word_count(words: int) -> dict:
    """Cria um artigo de teste com a contagem de palavras desejada.

    O header '## Manchete' conta como 2 palavras; subtrai-se 2 do total
    para que o validator veja exatamente `words` palavras no split().
    Garante >= 2 quebras duplas (estrutura válida: H2 + 2 parágrafos).
    """
    body_words = max(words - 2, 0)
    half = max(body_words // 2, 1)
    remainder = max(body_words - half, 0)
    content = "## Manchete\n\n" + "palavra " * half + "\n\n" + "palavra " * remainder
    return {
        "title": "Bitcoin e o futuro do mercado cripto em 2026 aqui",
        "slug": "bitcoin-futuro-mercado-cripto-2026",
        "excerpt": "Um excerpt de teste sobre bitcoin que tem mais de oitenta caracteres aqui ok mesmo.",
        "meta_title": "Bitcoin e o futuro do mercado em 2026",
        "meta_description": (
            "Bitcoin segue como o principal ativo cripto e segue gerando "
            "discussoes aprofundadas sobre o futuro do mercado digital em 2026 para todos."
        ),
        "content_markdown": content,
    }


def test_accepts_custom_word_range_within_bounds():
    validator = QualityValidator(min_words=500, max_words=750)
    article = _article_with_word_count(600)
    is_valid, errors = validator.validate_article(article)
    assert is_valid, f"Expected valid, got errors: {errors}"


def test_rejects_below_custom_min_words():
    validator = QualityValidator(min_words=500, max_words=750)
    article = _article_with_word_count(400)
    is_valid, errors = validator.validate_article(article)
    assert not is_valid
    assert any("400 palavras" in e and "mínimo 500" in e for e in errors)


def test_rejects_above_custom_max_words():
    validator = QualityValidator(min_words=500, max_words=750)
    article = _article_with_word_count(800)
    is_valid, errors = validator.validate_article(article)
    assert not is_valid
    assert any("800 palavras" in e and "máximo 750" in e for e in errors)


def test_default_constructor_preserves_original_behavior():
    """Sem argumentos, validator deve manter 250-500 (compatibilidade)"""
    validator = QualityValidator()
    article = _article_with_word_count(400)
    is_valid, _ = validator.validate_article(article)
    assert is_valid

    article_too_long = _article_with_word_count(600)
    is_valid, errors = validator.validate_article(article_too_long)
    assert not is_valid
    assert any("máximo 500" in e for e in errors)
