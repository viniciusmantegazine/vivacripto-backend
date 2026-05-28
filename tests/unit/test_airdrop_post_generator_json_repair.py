"""
Testes do reparo de JSON em _parse_json.

LLMs (Claude e Gemini) frequentemente retornam JSON com aspas/quebras
não-escapadas dentro de content_markdown longo. Sem reparo, json.loads
quebra com "Expecting ',' delimiter" e o artigo é perdido.
"""
from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator


def _make_generator() -> AirdropPostGenerator:
    """Generator sem inicializar Claude (não precisamos pra testar _parse_json)."""
    g = AirdropPostGenerator.__new__(AirdropPostGenerator)
    return g


def test_parse_json_recovers_from_unescaped_double_quotes_in_content():
    """
    Cenário real: LLM coloca uma citação com aspas dentro do content_markdown
    sem escapar. Sem reparo, json.loads quebra com "Expecting ',' delimiter".
    """
    g = _make_generator()
    broken = (
        '{\n'
        '  "title": "Polymarket: o projeto e o airdrop",\n'
        '  "slug": "polymarket-airdrop",\n'
        '  "excerpt": "Saiba como participar do programa de pontos.",\n'
        '  "content_markdown": "Polymarket é uma plataforma. O CEO disse "vamos crescer" em entrevista.\\n\\n## Sobre\\n\\nTexto.",\n'
        '  "meta_title": "Polymarket",\n'
        '  "meta_description": "Polymarket plataforma de previsão crypto airdrop programa pontos."\n'
        '}'
    )
    result = g._parse_json(broken)
    assert result is not None, "parser deveria recuperar JSON com aspas internas"
    assert result["title"].startswith("Polymarket")
    assert "Polymarket é uma plataforma" in result["content_markdown"]


def test_parse_json_recovers_from_literal_newlines_in_string():
    """
    LLM às vezes emite quebras de linha literais (não \\n) dentro de string.
    """
    g = _make_generator()
    broken = (
        '{\n'
        '  "title": "X airdrop programa de pontos cripto",\n'
        '  "content_markdown": "Linha 1\nLinha 2\n\nParágrafo 2."\n'
        '}'
    )
    result = g._parse_json(broken)
    assert result is not None
    assert "Linha 1" in result["content_markdown"]
    assert "Parágrafo 2" in result["content_markdown"]


def test_parse_json_still_strips_markdown_fences():
    """Comportamento existente preservado: cercas ```json ... ``` removidas."""
    g = _make_generator()
    fenced = (
        '```json\n'
        '{"title": "X programa airdrop cripto", "content_markdown": "y"}\n'
        '```'
    )
    result = g._parse_json(fenced)
    assert result is not None
    assert result["title"].startswith("X")


def test_parse_json_returns_none_for_completely_garbage_input():
    """Reparo não deve transformar lixo em artigo válido."""
    g = _make_generator()
    garbage = "isto não é json de jeito nenhum, só texto solto"
    result = g._parse_json(garbage)
    assert result is None


def test_parse_json_returns_none_when_required_fields_missing_even_after_repair():
    """Mesmo após reparo, se faltar title/content_markdown retorna None."""
    g = _make_generator()
    no_required = '{"slug": "x", "excerpt": "y"}'
    result = g._parse_json(no_required)
    assert result is None
