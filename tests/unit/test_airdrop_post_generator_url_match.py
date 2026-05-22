"""
Testes do match tolerante de URL e normalização Unicode do
AirdropPostGenerator._post_validate.
"""
from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator


def test_url_match_handles_markdown_link_with_same_url_as_text():
    """[url](url) — formato comum no disclosure."""
    content = "Site oficial: [https://layerzero.network](https://layerzero.network)."
    assert AirdropPostGenerator._url_appears_in_markdown(
        "https://layerzero.network", content
    )


def test_url_match_tolerates_trailing_slash_divergence():
    content = "Acesse [aqui](https://ref.example/abc/) agora."
    assert AirdropPostGenerator._url_appears_in_markdown(
        "https://ref.example/abc", content
    )


def test_url_match_tolerates_added_utm_params():
    content = "Acesse [aqui](https://ref.example/abc?utm=organic) agora."
    assert AirdropPostGenerator._url_appears_in_markdown(
        "https://ref.example/abc", content
    )


def test_url_match_tolerates_added_fragment():
    content = "Mais info em [docs](https://layerzero.network#getting-started)."
    assert AirdropPostGenerator._url_appears_in_markdown(
        "https://layerzero.network", content
    )


def test_url_match_handles_autolink_brackets():
    content = "Veja <https://layerzero.network> ou siga."
    assert AirdropPostGenerator._url_appears_in_markdown(
        "https://layerzero.network", content
    )


def test_url_match_returns_false_when_truly_absent():
    content = "Vai no site oficial mas sem link."
    assert not AirdropPostGenerator._url_appears_in_markdown(
        "https://layerzero.network", content
    )


def test_url_match_does_not_false_positive_on_substring_path():
    """`/abc` não deve match `/abcdef`."""
    content = "Veja [outro](https://ref.example/abcdef)."
    assert not AirdropPostGenerator._url_appears_in_markdown(
        "https://ref.example/abc", content
    )


def test_strip_accents_handles_full_disclosure_phrase():
    raw = "Este conteúdo é meramente informativo e não constitui recomendação."
    assert "nao constitui recomendacao" in AirdropPostGenerator._strip_accents(raw)


def test_strip_accents_handles_combining_chars_nfd():
    import unicodedata

    nfd = unicodedata.normalize("NFD", "não constitui recomendação")
    assert "nao constitui recomendacao" in AirdropPostGenerator._strip_accents(nfd)
