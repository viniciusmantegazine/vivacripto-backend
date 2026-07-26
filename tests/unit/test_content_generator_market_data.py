"""
Testes da injeção de dados de mercado no prompt.

O SYSTEM_PROMPT proíbe o modelo de citar número fora da fonte — regra que
existe para impedir alucinação de preço, e que continua valendo. O efeito
colateral é linguagem vaga ("registrou alta") por falta de dado.

Com <dados_de_mercado> o modelo passa a ter número verificado. Mas o guardrail
precisa dizer explicitamente que a seção é fonte válida: sem isso o modelo
trata os dados como "não sendo a fonte fornecida" e os ignora — e a falha seria
silenciosa, só visível na leitura de artigos publicados.
"""
import pytest

from app.services.ai.content_generator import ContentGenerator

SNAPSHOT = (
    "=== DADOS DE MERCADO COLETADOS EM 26/07/2026 17:51 UTC ===\n\n"
    "PREÇOS CRIPTO (fonte: CoinGecko, tempo real):\n"
    "  Bitcoin (BTC):\n    Preço: US$ 64,640.00\n    Variação: 24h +0.80%"
)


@pytest.fixture
def generator() -> ContentGenerator:
    return ContentGenerator()


def test_secao_entra_no_prompt_quando_ha_dado(generator: ContentGenerator):
    prompt = generator._build_article_prompt(
        "Bitcoin sobe", "corpo da noticia", "CoinDesk", "bitcoin",
        "Bitcoin", None, market_data=SNAPSHOT,
    )

    assert "<dados_de_mercado>" in prompt
    assert "</dados_de_mercado>" in prompt
    assert "US$ 64,640.00" in prompt


def test_secao_nao_entra_quando_nao_ha_dado(generator: ContentGenerator):
    """Sem dado, nada de seção vazia ou placeholder confundindo o modelo."""
    prompt = generator._build_article_prompt(
        "Bitcoin sobe", "corpo da noticia", "CoinDesk", "bitcoin",
        "Bitcoin", None, market_data=None,
    )

    assert "<dados_de_mercado>" not in prompt


def test_market_data_e_opcional(generator: ContentGenerator):
    """Chamada sem o argumento continua válida — o default é None."""
    prompt = generator._build_article_prompt(
        "Bitcoin sobe", "corpo", "CoinDesk", "bitcoin", "Bitcoin", None,
    )

    assert "<dados_de_mercado>" not in prompt
    assert "<dados_da_fonte>" in prompt


def test_secao_vem_logo_apos_dados_da_fonte(generator: ContentGenerator):
    """
    Posição importa: é material de fonte, então fica junto do resto do
    material de fonte e ANTES das instruções de tarefa.
    """
    prompt = generator._build_article_prompt(
        "t", "d", "s", "bitcoin", "Bitcoin", None, market_data=SNAPSHOT,
    )

    fim_fonte = prompt.index("</dados_da_fonte>")
    ini_mercado = prompt.index("<dados_de_mercado>")
    ini_tarefa = prompt.index("<tarefa>")

    assert fim_fonte < ini_mercado < ini_tarefa


def test_secao_instrui_uso_condicional(generator: ContentGenerator):
    """
    O dado entra em todo artigo, mas preço é irrelevante para uma notícia de
    regulação. A instrução evita que o modelo enfie número onde não cabe.
    """
    prompt = generator._build_article_prompt(
        "t", "d", "s", "bitcoin", "Bitcoin", None, market_data=SNAPSHOT,
    )

    ini = prompt.index("<dados_de_mercado>")
    fim = prompt.index("</dados_de_mercado>")
    bloco = prompt[ini:fim].lower()

    assert "pertinente" in bloco or "relevante" in bloco


def test_guardrail_abencoa_a_secao_de_dados_de_mercado():
    """
    O teste que protege contra a falha silenciosa: sem esta menção, o modelo
    recebe os dados e não os usa, e nada no sistema acusa.
    """
    guardrail = ContentGenerator.SYSTEM_PROMPT

    assert "<dados_de_mercado>" in guardrail, (
        "o guardrail de dados inventados precisa citar a seção como fonte "
        "válida, senão o modelo ignora os números"
    )


def test_guardrail_mantem_a_proibicao_de_inventar():
    """Abençoar a seção não pode virar licença geral para inventar número."""
    guardrail = ContentGenerator.SYSTEM_PROMPT

    assert "NUNCA invente preços" in guardrail
    assert "registrou alta" in guardrail
