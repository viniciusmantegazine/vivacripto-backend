"""
Testes do _parse_article_json.

O LLM devolve o artigo inteiro num objeto JSON. O campo content_markdown é
longo e cheio de newlines e aspas, que é justamente onde modelos erram o
escape — por isso o parse tem json_repair como rede, e não só json.loads.

Obrigatórios são content_markdown e title: sem texto não há artigo, e sem
título PT-BR não publicamos (o fallback seria o título em inglês da fonte).
excerpt e meta_description são recuperáveis e NÃO invalidam o parse.
"""
import json

import pytest

from app.services.ai.content_generator import ContentGenerator


@pytest.fixture
def generator() -> ContentGenerator:
    return ContentGenerator()


def _json_valido(**overrides) -> str:
    dados = {
        "content_markdown": "## Manchete\n\nCorpo do artigo.",
        "title": "Bitcoin Atinge Máxima Histórica Após Aprovação de ETF",
        "excerpt": "Bitcoin renova máxima em meio a forte demanda institucional por ETFs.",
        "meta_description": "Entenda o que a nova máxima do Bitcoin significa para o investidor brasileiro e o que observar adiante.",
    }
    dados.update(overrides)
    return json.dumps(dados)


def test_json_limpo_e_parseado(generator: ContentGenerator):
    resultado = generator._parse_article_json(_json_valido())

    assert resultado["title"].startswith("Bitcoin Atinge")
    assert resultado["content_markdown"].startswith("## Manchete")


def test_remove_cercas_de_codigo(generator: ContentGenerator):
    """Modelos frequentemente embrulham JSON em cercas apesar do pedido."""
    resultado = generator._parse_article_json("```json\n" + _json_valido() + "\n```")

    assert resultado is not None
    assert resultado["title"].startswith("Bitcoin Atinge")


def test_json_repair_salva_aspas_nao_escapadas(generator: ContentGenerator):
    """
    Modo de falha conhecido: aspas cruas dentro do content_markdown longo.
    json.loads quebra; json_repair conserta sem desfigurar o conteúdo.
    """
    quebrado = (
        '{"content_markdown": "## Manchete\\n\\nO CEO disse "vamos crescer" ontem.",'
        ' "title": "Bitcoin Atinge Máxima Histórica Após Aprovação de ETF",'
        ' "excerpt": "Bitcoin renova máxima em meio a forte demanda institucional.",'
        ' "meta_description": "Entenda o que a máxima do Bitcoin significa para o investidor brasileiro hoje."}'
    )

    resultado = generator._parse_article_json(quebrado)

    assert resultado is not None
    assert "Manchete" in resultado["content_markdown"]


def test_texto_nao_json_retorna_none(generator: ContentGenerator):
    assert generator._parse_article_json("desculpe, não consigo ajudar com isso") is None


def test_vazio_retorna_none(generator: ContentGenerator):
    assert generator._parse_article_json("") is None
    assert generator._parse_article_json(None) is None


@pytest.mark.parametrize("campo", ["content_markdown", "title"])
def test_campo_obrigatorio_ausente_retorna_none(generator: ContentGenerator, campo: str):
    """Sem conteúdo ou sem título não há artigo publicável."""
    dados = json.loads(_json_valido())
    del dados[campo]

    assert generator._parse_article_json(json.dumps(dados)) is None


@pytest.mark.parametrize("campo", ["content_markdown", "title"])
def test_campo_obrigatorio_vazio_retorna_none(generator: ContentGenerator, campo: str):
    """String vazia ou só espaço é o mesmo que ausente."""
    assert generator._parse_article_json(_json_valido(**{campo: "   "})) is None


@pytest.mark.parametrize("campo", ["excerpt", "meta_description"])
def test_campo_recuperavel_ausente_nao_invalida(generator: ContentGenerator, campo: str):
    """
    excerpt tem fallback mecânico e meta_description é reparada pelo retry do
    pipeline. Descartar o artigo por causa deles repetiria justamente o defeito
    que esta consolidação existe para corrigir.
    """
    dados = json.loads(_json_valido())
    del dados[campo]

    resultado = generator._parse_article_json(json.dumps(dados))

    assert resultado is not None
    assert resultado.get(campo) is None
