"""
Testes do _fetch_feed do RSSCollector: tratamento de HTTP status.

Regressão: The Block retornava 403 e caía no `except Exception` genérico,
sumindo silenciosamente da coleta. 4xx não deve ter retry (bloqueio/feed
removido); 5xx deve ser retentado.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.sources.rss_collector import RSSCollector


def _resp_with_status(status: int):
    """Response mock cujo raise_for_status levanta HTTPStatusError."""
    resp = MagicMock()
    resp.status_code = status
    err = httpx.HTTPStatusError(
        f"HTTP {status}", request=MagicMock(), response=resp
    )
    resp.raise_for_status = MagicMock(side_effect=err)
    return resp


def _client_ctx(response):
    """Context manager async fake para httpx.AsyncClient."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, client


@pytest.mark.asyncio
async def test_4xx_nao_tem_retry_e_retorna_none():
    collector = RSSCollector()
    ctx, client = _client_ctx(_resp_with_status(403))

    with patch(
        "app.services.sources.rss_collector.httpx.AsyncClient",
        return_value=ctx,
    ):
        result = await collector._fetch_feed("https://exemplo.com/rss")

    assert result is None
    assert client.get.await_count == 1  # sem retry para 4xx


@pytest.mark.asyncio
async def test_5xx_tem_retry():
    collector = RSSCollector()
    ctx, client = _client_ctx(_resp_with_status(500))

    with patch(
        "app.services.sources.rss_collector.httpx.AsyncClient",
        return_value=ctx,
    ):
        result = await collector._fetch_feed("https://exemplo.com/rss")

    assert result is None
    assert client.get.await_count == 2  # max_retries = 2


def test_the_block_removido_bitcoin_magazine_presente():
    """The Block responde 403 permanente (bloqueio anti-bot); substituído."""
    names = [f["name"] for f in RSSCollector.RSS_FEEDS]
    assert "The Block" not in names
    assert "Bitcoin Magazine" in names
