"""
Testes da lógica de filtragem/ranking de URLs do WebResearcher.
"""
from app.services.airdrop.web_researcher import (
    WebResearcher,
    BLOCKED_DOMAINS,
    PREFERRED_DOMAINS,
)


def test_deduplicates_urls_by_domain_keeping_top():
    researcher = WebResearcher()
    candidates = [
        ("https://coindesk.com/post-a", 1),
        ("https://coindesk.com/post-b", 2),
        ("https://cointelegraph.com/post-c", 3),
    ]
    result = researcher._dedup_by_domain(candidates)
    # mantém só o primeiro (rank menor) de cada domínio
    domains = {r[0].split("/")[2] for r in result}
    assert "coindesk.com" in domains
    assert "cointelegraph.com" in domains
    assert len(result) == 2


def test_blocklist_drops_social_and_video_domains():
    researcher = WebResearcher()
    candidates = [
        ("https://reddit.com/r/crypto/post", 1),
        ("https://x.com/someone/status/1", 2),
        ("https://youtube.com/watch?v=x", 3),
        ("https://coindesk.com/article", 4),
    ]
    result = researcher._apply_blocklist(candidates)
    domains = {r[0].split("/")[2] for r in result}
    assert "reddit.com" not in domains
    assert "x.com" not in domains
    assert "youtube.com" not in domains
    assert "coindesk.com" in domains


def test_whitelist_boost_prefers_known_sources():
    researcher = WebResearcher()
    candidates = [
        ("https://random-blog.example/post", 1),
        ("https://coindesk.com/article", 5),
        ("https://obscure.io/post", 2),
        ("https://coingecko.com/coin/x", 6),
    ]
    result = researcher._apply_whitelist_boost(candidates)
    # ranks dos preferred devem diminuir (boost = subtraem N de rank)
    coindesk_rank = next(r for url, r in result if "coindesk.com" in url)
    blog_rank = next(r for url, r in result if "random-blog" in url)
    assert coindesk_rank < blog_rank, "Whitelisted domain should outrank random blog after boost"


def test_select_top_n_includes_official_url_always():
    researcher = WebResearcher()
    ranked = [
        ("https://coindesk.com/a", 1),
        ("https://cointelegraph.com/b", 2),
        ("https://decrypt.co/c", 3),
        ("https://theblock.co/d", 4),
        ("https://other.com/e", 5),
        ("https://other2.com/f", 6),
    ]
    selected = researcher._select_top(ranked, "https://layerzero.network", top_n=5)
    assert "https://layerzero.network" in selected
    assert len(selected) == 5


def test_select_top_n_does_not_duplicate_official_url():
    """Se a official_url já está no ranking, não duplica."""
    researcher = WebResearcher()
    ranked = [
        ("https://layerzero.network", 1),
        ("https://coindesk.com/a", 2),
        ("https://cointelegraph.com/b", 3),
    ]
    selected = researcher._select_top(ranked, "https://layerzero.network", top_n=5)
    assert selected.count("https://layerzero.network") == 1


def test_blocked_and_preferred_domains_sets_exist():
    assert "reddit.com" in BLOCKED_DOMAINS
    assert "x.com" in BLOCKED_DOMAINS
    assert "youtube.com" in BLOCKED_DOMAINS
    assert "coindesk.com" in PREFERRED_DOMAINS
    assert "coingecko.com" in PREFERRED_DOMAINS
