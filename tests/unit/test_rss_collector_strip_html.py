"""
Testes do _strip_html: `entry.summary` de vários feeds vem com HTML,
que contaminava o prompt do LLM, o TF-IDF de dedup e o critério de
"descrição mais completa" (tags inflam o tamanho).
"""
from app.services.sources.rss_collector import _strip_html


def test_remove_tags():
    assert _strip_html("<p>Bitcoin <b>sobe</b> hoje</p>") == "Bitcoin sobe hoje"


def test_unescape_entidades():
    assert _strip_html("Fear &amp; Greed em alta") == "Fear & Greed em alta"


def test_colapsa_espacos_e_quebras():
    assert _strip_html("Bitcoin\n\n  sobe   hoje") == "Bitcoin sobe hoje"


def test_vazio_e_none():
    assert _strip_html("") == ""
    assert _strip_html(None) == ""
