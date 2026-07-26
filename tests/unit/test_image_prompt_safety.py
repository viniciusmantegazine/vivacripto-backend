"""
Testes de segurança do vocabulário dos prompts de imagem.

Regressão: `ACTION_VISUAL_ELEMENTS` continha "under attack with warning
indicators". Como essa opção é sorteada por random.choice, a palavra
bloqueada "attack" vazava para o prompt em ~27% das gerações de notícias
de segurança (110 de 400 medidas) — e era isso que fazia
test_full_pipeline_security_warning falhar de forma intermitente.

Causa dupla:
1. O banco de elementos visuais (escrito em INGLÊS) usava vocabulário que a
   sanitização pretendia bloquear.
2. SAFE_REPLACEMENTS mapeava só os termos em PORTUGUÊS ('ataque', 'roubo',
   'hackeado') — os equivalentes ingleses não tinham cobertura.

Estes testes varrem a lista INTEIRA em vez de amostrar, então não dependem
de sorteio.
"""
import re

import pytest

from app.services.ai.news_context_analyzer import NewsContextAnalyzer
from app.services.ai.smart_prompt_generator import SmartPromptGenerator
from app.services.ai.visual_elements_bank import EditorialVisualElementsBank

# Vocabulário que nunca deve chegar a uma API de geração de imagem: causa
# recusa ou flag de conteúdo violento.
VOCABULARIO_INSEGURO = [
    "attack", "attacked", "stolen", "steal", "stealing", "theft",
    "hack", "hacked", "hacker", "kill", "murder", "blood", "weapon",
    "gun", "assault", "violent",
]


def _todas_as_strings(valor):
    """Achata qualquer constante do banco (str/list/dict aninhados) em strings."""
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for v in valor.values():
            yield from _todas_as_strings(v)
    elif isinstance(valor, (list, tuple)):
        for v in valor:
            yield from _todas_as_strings(v)


def test_banco_de_elementos_visuais_nao_usa_vocabulario_inseguro():
    """
    O banco deve nascer seguro. Depender da sanitização a jusante é frágil:
    o texto vira prompt por caminhos que podem não passar pelo sanitizador.
    """
    infracoes = []
    for nome in dir(EditorialVisualElementsBank):
        if nome.startswith("_") or not nome.isupper():
            continue
        for texto in _todas_as_strings(getattr(EditorialVisualElementsBank, nome)):
            for palavra in VOCABULARIO_INSEGURO:
                if re.search(rf"\b{palavra}\b", texto, re.IGNORECASE):
                    infracoes.append(f"{nome}: '{palavra}' em \"{texto}\"")

    assert not infracoes, "vocabulário inseguro no banco:\n" + "\n".join(infracoes)


@pytest.mark.parametrize(
    "termo_ingles",
    ["attack", "attacked", "stolen", "steal", "stealing", "theft", "hacked"],
)
def test_safe_replacements_cobre_termos_ingleses(termo_ingles):
    """
    O mapa cobria só o português. Como o banco e os prompts são em inglês,
    os equivalentes ingleses precisam da mesma cobertura.
    """
    analyzer = NewsContextAnalyzer()
    resultado = analyzer.apply_safe_replacements(f"exchange {termo_ingles} today")

    assert not re.search(rf"\b{termo_ingles}\b", resultado, re.IGNORECASE), (
        f"'{termo_ingles}' sobreviveu à sanitização: {resultado}"
    )


def test_todas_as_acoes_de_seguranca_geram_prompt_limpo():
    """
    Varre TODAS as opções de ação de segurança (em vez de sortear uma),
    garantindo que nenhuma delas vaza palavra bloqueada para o prompt.
    """
    generator = SmartPromptGenerator()
    acoes = EditorialVisualElementsBank.ACTION_VISUAL_ELEMENTS

    for acao, opcoes in acoes.items():
        for opcao in opcoes:
            for palavra in ("hack", "attack", "stolen"):
                assert not re.search(rf"\b{palavra}\b", opcao, re.IGNORECASE), (
                    f"ação '{acao}' tem opção com '{palavra}': \"{opcao}\""
                )

    # E o pipeline completo de notícia de segurança segue limpo
    resultado = generator.generate_prompt_with_metadata(
        "Exchange sofre ataque hacker de US$ 50 milhões",
        "Uma exchange centralizada foi alvo de hackers que exploraram "
        "vulnerabilidade no sistema. Fundos dos usuários foram roubados.",
        "altcoins",
    )
    prompt = resultado["prompt"].lower()
    for palavra in ("hack", "attack", "stolen"):
        assert palavra not in prompt, f"'{palavra}' vazou no prompt: {prompt[:200]}"
