"""
Testes do corte por tamanho em _validate_and_optimize_prompt.

Regressão: o corte era feito no FIM do prompt (`result[:MAX].rsplit(', ', 1)`),
e os guardrails obrigatórios vivem exatamente lá — formato 16:9,
anti-watermark, anti-getty/shutterstock e anti-branding de veículos
concorrentes. Num prompt de 1841 chars, 345 chars de cauda eram descartados
em silêncio, levando as proteções embora.

O formato 16:9 tem backup (image_generator passa aspect_ratio na API Gemini),
mas as proteções de marca NÃO têm — perdê-las é perda real.
"""
import pytest

from app.services.ai.news_context_analyzer import NewsContextAnalyzer
from app.services.ai.smart_prompt_generator import SmartPromptGenerator
from app.services.ai.visual_elements_bank import EditorialVisualElementsBank

MAX_PROMPT_LENGTH = 1500

# Guardrails que NUNCA podem sumir do prompt, mesmo quando ele estoura o cap.
GUARDRAILS = [
    "16:9 aspect ratio",
    "no cropped elements",
    "no getty/shutterstock/istock marks",
    "no coindesk/cointelegraph/news site branding",
]


@pytest.fixture
def generator():
    return SmartPromptGenerator(NewsContextAnalyzer(), EditorialVisualElementsBank())


def test_prompt_longo_e_truncado_mas_preserva_guardrails(generator):
    """Caso real que expôs o bug: contexto genérico gera prompt de ~1841 chars."""
    result = generator.generate_prompt_with_metadata(
        "Altcoins: Mercado atinge novo recorde em janeiro",
        "Diversas criptomoedas alternativas valorizaram no início do ano.",
        None,
    )
    prompt = result["prompt"].lower()

    assert len(result["prompt"]) <= MAX_PROMPT_LENGTH
    for guardrail in GUARDRAILS:
        assert guardrail in prompt, f"guardrail perdido no truncamento: {guardrail}"


def test_corte_respeita_o_cap_de_tamanho(generator):
    """O cap continua valendo — a correção não é 'deixar passar de 1500'."""
    prompt = generator._validate_and_optimize_prompt(
        ", ".join(f"sentenca descritiva numero {i} com algum texto" for i in range(200))
        + ", "
        + generator.QUALITY_SUFFIX
        + ", "
        + generator.QUALITY_PROTECTION_SUFFIX
    )

    assert len(prompt) <= MAX_PROMPT_LENGTH


def test_corte_descarta_miolo_descritivo_nao_a_cauda(generator):
    """Sentenças descritivas do fim cedem lugar; os guardrails ficam."""
    descritivas = [f"sentenca descritiva numero {i} com algum texto" for i in range(200)]
    prompt = generator._validate_and_optimize_prompt(
        ", ".join(descritivas)
        + ", "
        + generator.QUALITY_SUFFIX
        + ", "
        + generator.QUALITY_PROTECTION_SUFFIX
    ).lower()

    for guardrail in GUARDRAILS:
        assert guardrail in prompt, f"guardrail perdido: {guardrail}"
    # As primeiras descritivas sobrevivem, as últimas não
    assert "sentenca descritiva numero 0 " in prompt
    assert "sentenca descritiva numero 199 " not in prompt


def test_prompt_curto_passa_intacto(generator):
    """Sem estouro de cap, nada é removido além da dedup de sentenças."""
    prompt = generator._validate_and_optimize_prompt(
        "cena jornalistica, setting: mesa de operacoes, colors: verde e ouro"
    )

    assert prompt == "cena jornalistica, setting: mesa de operacoes, colors: verde e ouro"
