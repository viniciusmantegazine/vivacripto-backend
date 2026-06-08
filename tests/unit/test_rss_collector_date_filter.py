"""
Testes do filtro de recência do RSSCollector.

Regressão: entradas de feed SEM data parseável vazavam pelo filtro de janela
(hours_back) e podiam ser publicadas como notícia, mesmo sendo antigas.
"""
from datetime import datetime, timedelta, timezone

import feedparser
import pytest

from app.services.sources.rss_collector import RSSCollector


def _entry(title: str, *, published_struct=None):
    """Cria uma entrada estilo feedparser. Sem published_struct => sem data."""
    entry = feedparser.FeedParserDict()
    entry["title"] = title
    entry["link"] = f"https://example.com/{title.replace(' ', '-')}"
    entry["summary"] = f"resumo de {title}"
    if published_struct is not None:
        entry["published_parsed"] = published_struct
    return entry


def _feed(entries):
    feed = feedparser.FeedParserDict()
    feed["entries"] = entries
    return feed


@pytest.mark.asyncio
async def test_descarta_entrada_sem_data(monkeypatch):
    """Entrada sem data parseável NÃO deve passar pelo filtro de recência."""
    collector = RSSCollector()

    recent_struct = (datetime.now(timezone.utc) - timedelta(hours=1)).timetuple()
    feed = _feed([
        _entry("Noticia recente", published_struct=recent_struct),
        _entry("Noticia sem data"),  # sem published_parsed => _parse_date == None
    ])

    async def fake_fetch(url):
        return feed

    monkeypatch.setattr(collector, "_fetch_feed", fake_fetch)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    items = await collector._collect_from_feed(
        {"name": "Test", "url": "x", "language": "en"}, cutoff
    )

    titles = [i["title"] for i in items]
    assert "Noticia recente" in titles
    assert "Noticia sem data" not in titles
