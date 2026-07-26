"""
Testes do RelevanceFilter.

A fixture usa titulo e resumo REAIS, capturados dos feeds em 2026-07-26. O
resumo importa principalmente na direcao negativa: e ele que o veto de cripto
le, e uma implementacao que ignorasse `description` por completo passaria
despercebida nos testes de descarte (os 7 itens descartam pelo titulo
sozinho) se nao fosse por `test_le_o_resumo_e_nao_so_o_titulo`, que existe
so para fechar esse buraco.
"""
import pytest

from app.services.sources.relevance_filter import RelevanceFilter


@pytest.fixture
def filtro() -> RelevanceFilter:
    return RelevanceFilter()


# Itens reais de IA pura, sem nenhum angulo de cripto. Todos do Decrypt,
# que e tanto publicacao de IA quanto de cripto.
FORA_DE_TEMA = [
    (
        "Mira Murati’s Inkling AI Model Review: Best Open-Source Model in the West",
        "After two years of silence from Thinking Machines Lab, Murati's debut "
        "model is out and on OpenRouter. The MCP score is genuinely impressive. "
        "The price-to-performance math is more complicated.",
        "AI Model",
    ),
    (
        "What Is an AI Kill Switch and Why Do US Lawmakers Want One?",
        "The AI Kill Switch Act would let Homeland Security order frontier AI "
        "throttled or shut down, with fines up to $20 million a day for defying it.",
        "AI Kill Switch",
    ),
    (
        "Claude Opus 5 Outscores Fable 5 on Most Benchmarks—At Half the Price",
        "Anthropic's new everyday model undercuts its own frontier product on "
        "cost and beats it almost everywhere that counts.",
        "Claude",
    ),
    (
        "Black Forest Labs Unveils FLUX 3 AI: Ditches Stills for Video—And Robot Hands",
        "FLUX 3 is the German AI lab’s first video model, and the same system is "
        "already teaching robots to work an Audi assembly line.",
        "Black Forest Labs",
    ),
    (
        "Alibaba's New Qwen Image 3 AI Wants to Be Useful, Not Just Pretty",
        "Qwen Image 3.0 generates dense newspapers and infographic grids in one "
        "shot and renders text down to 10 pixels. The catch: no benchmarks, no "
        "open weights.",
        "Qwen",
    ),
    # Este passou na primeira versao do vocabulario porque 'hack', no RESUMO,
    # estava no veto de cripto e anulou 'Nvidia' + 'Open-Source AI'.
    (
        "Nvidia, Meta, and Microsoft Tell Washington: Don't Kill Open-Source AI",
        "Twenty-five companies signed a letter defending open-weight models days "
        "after a Chinese AI helped Hugging Face survive a hack triggered by "
        "OpenAI's own systems.",
        "Nvidia",
    ),
    # Este passou porque a OFF_BEAT nao tinha nome proprio de laboratorio:
    # "Chinese AI" e "Chinese model GLM 5.2" nao casavam com padrao nenhum.
    (
        "Hugging Face CEO Thanks Chinese AI for Saving the Day After OpenAI Hack",
        "When American commercial AI refused to help investigate the breach, "
        "Hugging Face ran Chinese model GLM 5.2 locally. Its CEO now says "
        "there's an important lesson in this.",
        "Hugging Face",
    ),
]


@pytest.mark.parametrize("titulo,resumo,esperado", FORA_DE_TEMA)
def test_descarta_noticia_de_outra_editoria(filtro, titulo, resumo, esperado):
    termo = filtro.rejection_reason({"title": titulo, "description": resumo})

    assert termo is not None, f"deveria descartar: {titulo}"


@pytest.mark.parametrize("titulo,resumo,esperado", FORA_DE_TEMA)
def test_devolve_o_termo_que_causou_o_descarte(filtro, titulo, resumo, esperado):
    """
    Igualdade e nao 'e substring': o valor devolvido vai para o log de
    descarte, e documentar QUAL sinal disparou em cada item pega o
    descarte-pelo-motivo-errado, que a versao com substring nao ve.
    """
    assert filtro.rejection_reason({"title": titulo, "description": resumo}) == esperado


def test_le_o_resumo_e_nao_so_o_titulo(filtro):
    """
    Sem isto, uma implementacao que ignorasse `description` por completo
    passaria em todos os outros testes: os 7 fixtures descartam pelo
    titulo sozinho.
    """
    _, resumo, _ = FORA_DE_TEMA[0]

    assert filtro.rejection_reason({"title": "", "description": resumo}) is not None


@pytest.mark.parametrize(
    "vocabulario",
    [RelevanceFilter.OFF_BEAT_PATTERNS, RelevanceFilter.CRYPTO_SIGNAL_PATTERNS],
)
def test_nenhuma_virgula_esquecida_no_vocabulario(vocabulario):
    """
    Virgula esquecida faz o Python concatenar duas entradas vizinhas em
    algo como r"\\bnvidia\\b\\bgpus?\\b" — casa com nada, compila sem erro e
    nenhum outro teste percebe.
    """
    for padrao in vocabulario:
        assert "\\b\\b" not in padrao, f"virgula esquecida perto de: {padrao}"
