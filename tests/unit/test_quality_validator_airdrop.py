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


def _article_intro_then_h2(words: int = 600) -> dict:
    """
    Artigo no formato airdrop: parágrafo de intro ANTES do primeiro H2,
    seguido pelas seções H2. Estrutura espelha o que o prompt de airdrop
    instrui o LLM a produzir.
    """
    intro = (
        "O projeto bitcoin-x é uma rede blockchain voltada a aplicações cripto "
        "educacionais. Este artigo descreve seu programa de airdrop de token de forma neutra."
    )
    body_words = max(words - len(intro.split()) - 4, 0)  # 4 = palavras dos H2s
    half = max(body_words // 2, 1)
    remainder = max(body_words - half, 0)
    content = (
        intro
        + "\n\n## Sobre o projeto\n\n"
        + "palavra " * half
        + "\n\n## Como participar\n\n"
        + "palavra " * remainder
    )
    return {
        "title": "Bitcoin-X airdrop: o que e o projeto e como participar agora",
        "slug": "bitcoin-x-airdrop",
        "excerpt": (
            "Conheca o projeto bitcoin-x, sua proposta de blockchain educacional "
            "e veja como participar do airdrop de token disponivel agora."
        ),
        "meta_title": "Bitcoin-X airdrop: guia rapido",
        "meta_description": (
            "Bitcoin-X e um projeto blockchain educacional. Veja como participar "
            "do airdrop pelo site oficial e cadastre-se com seguranca em poucos passos."
        ),
        "content_markdown": content,
    }


def test_accepts_intro_paragraph_when_h2_first_disabled():
    """
    Com require_h2_first=False, conteúdo pode começar com parágrafo de
    introdução antes do primeiro H2 (formato do airdrop).
    """
    validator = QualityValidator(
        min_words=500, max_words=750, require_h2_first=False
    )
    article = _article_intro_then_h2(600)
    is_valid, errors = validator.validate_article(article)
    assert is_valid, f"Expected valid, got errors: {errors}"


def test_rejects_intro_paragraph_by_default():
    """
    Comportamento default (require_h2_first=True) continua rejeitando
    conteúdo que não começa com H2 — protege o pipeline de notícias.
    """
    validator = QualityValidator(min_words=500, max_words=750)
    article = _article_intro_then_h2(600)
    is_valid, errors = validator.validate_article(article)
    assert not is_valid
    assert any("manchete interna" in e.lower() or "H2" in e for e in errors)


def test_h2_disabled_still_requires_at_least_one_h2_in_paragraph_check():
    """
    Mesmo com require_h2_first=False, conteúdo sem nenhum bloco precisa
    falhar nas outras checagens estruturais (paragrafos / quebras duplas).
    Garante que a flag só afrouxa o início, não toda a estrutura.
    """
    validator = QualityValidator(
        min_words=10, max_words=5000, require_h2_first=False
    )
    article = _article_intro_then_h2(600)
    article["content_markdown"] = "linha unica sem quebras duplas nem heading"
    is_valid, errors = validator.validate_article(article)
    assert not is_valid
    assert any("quebra" in e.lower() or "parágrafo" in e.lower() for e in errors)
