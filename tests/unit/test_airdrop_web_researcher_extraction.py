"""
Testes de extração de HTML do WebResearcher.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.airdrop.web_researcher import (
    SOURCE_TRUNCATE_CHARS,
    WebResearcher,
)


@pytest.fixture
def html_with_noise():
    return """
    <html>
      <head><title>LayerZero</title></head>
      <body>
        <nav>Menu home about</nav>
        <script>console.log('x')</script>
        <style>.x{color:red}</style>
        <main>
          <h1>LayerZero</h1>
          <p>O LayerZero é um protocolo de mensagens entre blockchains.</p>
          <p>Possui um token chamado ZRO.</p>
        </main>
        <footer>Footer text</footer>
      </body>
    </html>
    """


def test_extract_text_strips_scripts_styles_nav_footer(html_with_noise):
    researcher = WebResearcher()
    text = researcher._extract_text(html_with_noise)
    assert "console.log" not in text
    assert ".x{color:red}" not in text
    assert "Menu home about" not in text
    assert "Footer text" not in text
    assert "protocolo de mensagens" in text
    assert "ZRO" in text


def test_extract_text_truncates_to_max_chars():
    researcher = WebResearcher()
    long_html = "<html><body><p>" + ("palavra " * 5000) + "</p></body></html>"
    text = researcher._extract_text(long_html)
    assert len(text) <= SOURCE_TRUNCATE_CHARS


@pytest.mark.asyncio
async def test_fetch_url_returns_text_on_200(html_with_noise):
    researcher = WebResearcher()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mock_response.text = html_with_noise

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    text = await researcher._fetch_url(mock_client, "https://example.com")
    assert text is not None
    assert "protocolo de mensagens" in text


@pytest.mark.asyncio
async def test_fetch_url_returns_none_on_non_html_content_type():
    researcher = WebResearcher()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/pdf"}
    mock_response.text = "%PDF-1.4..."

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    text = await researcher._fetch_url(mock_client, "https://example.com/doc.pdf")
    assert text is None


@pytest.mark.asyncio
async def test_fetch_url_returns_none_on_http_error():
    researcher = WebResearcher()
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
    text = await researcher._fetch_url(mock_client, "https://example.com")
    assert text is None
