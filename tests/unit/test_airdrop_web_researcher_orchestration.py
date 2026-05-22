"""
Testes de orquestração completa do WebResearcher.gather_context().
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.airdrop.web_researcher import (
    ResearchFailedError,
    WebResearcher,
)


@pytest.fixture
def mock_ddg_results():
    return [
        {"href": "https://coindesk.com/layerzero-airdrop", "title": "x", "body": "x"},
        {"href": "https://coingecko.com/layerzero", "title": "x", "body": "x"},
        {"href": "https://reddit.com/r/layerzero", "title": "x", "body": "x"},
        {"href": "https://random-blog.com/post", "title": "x", "body": "x"},
    ]


@pytest.fixture
def mock_html_response():
    return """
    <html><body><main>
      <p>LayerZero é um protocolo de interoperabilidade entre blockchains.</p>
      <p>Permite mensagens cross-chain de forma segura.</p>
    </main></body></html>
    """


@pytest.mark.asyncio
async def test_gather_context_returns_consolidated_text(
    mock_ddg_results, mock_html_response
):
    researcher = WebResearcher()

    # Mock DDGS to return results per query
    mock_ddgs_instance = MagicMock()
    mock_ddgs_instance.text = MagicMock(return_value=iter(mock_ddg_results))
    mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
    mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = mock_html_response

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.airdrop.web_researcher.DDGS", return_value=mock_ddgs_instance):
        with patch("app.services.airdrop.web_researcher.httpx.AsyncClient", return_value=mock_client):
            result = await researcher.gather_context(
                project_name="LayerZero",
                official_url="https://layerzero.network",
            )

    assert "LayerZero" in result.sources_text
    assert "[FONTE 1 - OFICIAL]" in result.sources_text
    assert "https://layerzero.network" in result.sources_used
    # reddit não deve aparecer (blocklist)
    assert "reddit.com" not in result.sources_text


@pytest.mark.asyncio
async def test_gather_context_raises_when_official_url_fails():
    """Se a página oficial falha e DDG não retorna nada, levanta erro."""
    researcher = WebResearcher()

    mock_ddgs_instance = MagicMock()
    mock_ddgs_instance.text = MagicMock(return_value=iter([]))
    mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
    mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("network down"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.airdrop.web_researcher.DDGS", return_value=mock_ddgs_instance):
        with patch("app.services.airdrop.web_researcher.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ResearchFailedError):
                await researcher.gather_context(
                    project_name="Bogus",
                    official_url="https://bogus.example",
                )


@pytest.mark.asyncio
async def test_gather_context_continues_when_secondary_url_fails(
    mock_ddg_results, mock_html_response
):
    """Se algumas URLs secundárias falham, processo continua."""
    researcher = WebResearcher()

    mock_ddgs_instance = MagicMock()
    mock_ddgs_instance.text = MagicMock(return_value=iter(mock_ddg_results))
    mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
    mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

    mock_success_response = MagicMock()
    mock_success_response.status_code = 200
    mock_success_response.headers = {"content-type": "text/html"}
    mock_success_response.text = mock_html_response

    call_count = {"n": 0}

    async def flaky_get(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise Exception("flake")
        return mock_success_response

    mock_client = MagicMock()
    mock_client.get = flaky_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.airdrop.web_researcher.DDGS", return_value=mock_ddgs_instance):
        with patch("app.services.airdrop.web_researcher.httpx.AsyncClient", return_value=mock_client):
            result = await researcher.gather_context(
                project_name="LayerZero",
                official_url="https://layerzero.network",
            )

    # Pelo menos a oficial entrou
    assert "[FONTE 1 - OFICIAL]" in result.sources_text
    assert len(result.sources_used) >= 1
