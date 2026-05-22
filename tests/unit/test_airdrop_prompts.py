"""
Testes do módulo de prompts de airdrop.
"""
from app.services.ai.prompts.airdrop_prompts import (
    AIRDROP_SYSTEM_PROMPT,
    build_airdrop_user_prompt,
)


def test_system_prompt_contains_critical_rules():
    p = AIRDROP_SYSTEM_PROMPT.lower()
    assert "neutro" in p
    assert "não constitui recomendação" in p or "nao constitui recomendacao" in p
    assert "fontes" in p


def test_system_prompt_forbids_investment_language():
    p = AIRDROP_SYSTEM_PROMPT.lower()
    # Frases proibidas devem aparecer como exemplos do que NÃO usar
    assert "lucro" in p or "garantia" in p or "investir" in p


def test_user_prompt_injects_all_variables():
    result = build_airdrop_user_prompt(
        project_name="LayerZero",
        official_url="https://layerzero.network",
        referral_url="https://ref.example/abc",
        sources_text="=== FONTES ===\n[FONTE 1] ...",
        current_date="2026-05-21",
    )
    assert "LayerZero" in result
    assert "https://layerzero.network" in result
    assert "https://ref.example/abc" in result
    assert "=== FONTES ===" in result
    assert "2026-05-21" in result


def test_user_prompt_specifies_word_range():
    result = build_airdrop_user_prompt(
        project_name="X",
        official_url="https://x.com",
        referral_url="https://x.com/r",
        sources_text="",
        current_date="2026-01-01",
    )
    assert "500" in result and "750" in result
