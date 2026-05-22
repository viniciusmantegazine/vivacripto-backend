"""
Testes de integração do endpoint /api/v1/airdrops/generate-post — modo preview.

Usa um httpx.AsyncClient direto contra o app, com get_db override mockado,
pra contornar a incompatibilidade UUID/SQLite pré-existente no projeto.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.airdrops import get_generator
from app.core.config import settings
from app.db.base import get_db
from app.main import app


@pytest_asyncio.fixture
async def airdrop_api_client():
    """
    Cliente HTTP que mocka get_db (sem DB real) e expõe um MagicMock
    como generator via dependency override.
    """

    async def fake_get_db():
        yield MagicMock()

    mock_generator = MagicMock()

    def fake_get_generator():
        return mock_generator

    app.dependency_overrides[get_db] = fake_get_db
    app.dependency_overrides[get_generator] = fake_get_generator
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # disponibiliza o mock via atributo pro teste customizar
        client.mock_generator = mock_generator
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_endpoint_requires_auth(airdrop_api_client):
    response = await airdrop_api_client.post(
        "/api/v1/airdrops/generate-post",
        json={
            "project_name": "LayerZero",
            "official_url": "https://layerzero.network",
            "referral_url": "https://ref.example/abc",
            "publish": False,
        },
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_preview_returns_markdown_without_publishing(airdrop_api_client):
    # Bloco de texto reutilizável para padding — ~50 palavras cada repetição
    _pad = (
        "O LayerZero conecta redes blockchain distintas permitindo a comunicação segura "
        "entre Ethereum Arbitrum Optimism Polygon BNB Chain Avalanche e outras redes. "
        "Isso viabiliza transferências de tokens e dados sem intermediários centrais. "
    )  # ~32 palavras
    # content_markdown deve: começar com ##, ter 500–750 palavras, >=2 quebras duplas,
    # >=2 parágrafos (sem contar H2s). excerpt: 80–200 chars. meta_description: 120–180 chars.
    article = {
        "title": "LayerZero airdrop: o que e o protocolo e como participar em 2026",
        "slug": "layerzero-protocolo-airdrop-2026",
        "excerpt": (
            "Conheca o LayerZero, protocolo de interoperabilidade entre blockchains. "
            "Veja como participar do programa de airdrop pelo site oficial em 2026."
        ),
        "content_markdown": (
            "## Sobre o LayerZero\n\n"
            + "O LayerZero é um protocolo de interoperabilidade entre blockchains que permite "
            "transferências de tokens e mensagens entre diferentes redes de forma segura e "
            "descentralizada. A tecnologia usa endpoints ultra-leves para comunicação cross-chain "
            "sem depender de redes intermediárias centralizadas. O protocolo suporta mais de vinte "
            "blockchains diferentes, incluindo Ethereum, Arbitrum, Optimism, BNB Chain e Polygon. "
            + _pad * 4
            + "\n\n## O programa de airdrop\n\n"
            "O airdrop do LayerZero distribui tokens ZRO para usuários que interagiram com o "
            "protocolo antes do snapshot. Para ser elegível, era necessário ter realizado "
            "transações cross-chain usando a infraestrutura do LayerZero. O token ZRO representa "
            "governança e utilidade dentro do ecossistema crypto do protocolo. Usuários de DeFi "
            "e blockchain que usaram bridges compatíveis podem verificar sua elegibilidade. "
            + _pad * 3
            + "\n\n## Como participar\n\n"
            "Para participar do airdrop, acesse o site oficial em "
            "[https://layerzero.network](https://layerzero.network) "
            "e verifique sua elegibilidade conectando sua carteira. Use o link de referência "
            "[aqui](https://ref.example/abc) para se cadastrar e acompanhar seu progresso. "
            "Siga as instruções na plataforma para reivindicar seus tokens ZRO com segurança. "
            + _pad * 2
            + "\n\n## Informações importantes\n\n"
            "Este conteudo não constitui recomendação de investimento. "
            "Sempre faça sua própria pesquisa antes de participar de qualquer airdrop de crypto "
            "ou blockchain. Os tokens ZRO podem ter valor variável e participar envolve riscos. "
            "Consulte fontes confiáveis e o site oficial do projeto antes de tomar decisões. "
            "A comunidade de crypto e blockchain acompanha de perto o desenvolvimento do LayerZero. "
        ),
        "meta_title": "LayerZero airdrop 2026",
        "meta_description": (
            "LayerZero, protocolo de interoperabilidade entre blockchains. Veja como participar do "
            "programa de airdrop pelo site oficial e cadastre-se agora."
        ),
        "image_url": "https://img/x.jpg",
        "sources_used": ["https://layerzero.network", "https://coindesk.com/x"],
        "word_count": 600,
    }

    airdrop_api_client.mock_generator.generate = AsyncMock(return_value=article)

    response = await airdrop_api_client.post(
        "/api/v1/airdrops/generate-post",
        json={
            "project_name": "LayerZero",
            "official_url": "https://layerzero.network",
            "referral_url": "https://ref.example/abc",
            "publish": False,
        },
        headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True
    assert data["post_id"] is None
    assert "preview_content" in data and data["preview_content"]
    assert data["sources_used"] == [
        "https://layerzero.network",
        "https://coindesk.com/x",
    ]
    # Preview NÃO deve pedir imagem (skip pra economizar custo).
    call_kwargs = airdrop_api_client.mock_generator.generate.call_args.kwargs
    assert call_kwargs.get("generate_image") is False


@pytest.mark.asyncio
async def test_preview_accepts_intro_paragraph_before_first_h2(airdrop_api_client):
    """
    Regressão: o prompt do airdrop instrui o LLM a colocar uma introdução
    antes do primeiro H2. O endpoint precisa aceitar esse formato (e não
    aplicar a regra H2-first do pipeline RSS).
    """
    _pad = (
        "O projeto bitcoin-x conecta redes blockchain distintas permitindo a comunicacao "
        "entre Ethereum Arbitrum Optimism Polygon BNB Chain Avalanche e outras redes. "
        "Isso viabiliza transferencias de tokens e dados sem intermediarios centrais. "
    )
    article = {
        "title": "Bitcoin-X airdrop: o que e o projeto e como participar agora",
        "slug": "bitcoin-x-airdrop",
        "excerpt": (
            "Conheca o projeto bitcoin-x, sua proposta de blockchain educacional "
            "e veja como participar do airdrop de token disponivel agora."
        ),
        "content_markdown": (
            # Parágrafo de introdução ANTES de qualquer heading — formato airdrop
            "O bitcoin-x e um projeto de blockchain voltado a interoperabilidade entre "
            "redes cripto distintas. Este artigo descreve seu programa de airdrop de "
            "forma neutra, educacional e baseada em fontes publicas disponiveis.\n\n"
            "## Sobre o projeto bitcoin-x\n\n"
            + _pad * 7
            + "\n\n## O programa de airdrop\n\n"
            + _pad * 6
            + "\n\n## Como participar\n\n"
            "Para participar acesse [aqui](https://ref.example/abc) e siga o cadastro. "
            + _pad * 4
            + "\n\n## Informações importantes\n\n"
            "Este conteudo nao constitui recomendacao de investimento. "
            "Sempre faca sua propria pesquisa antes de participar de qualquer airdrop de crypto. "
            "Acesse o site oficial em [https://bitcoinx.example](https://bitcoinx.example). "
        ),
        "meta_title": "Bitcoin-X airdrop: guia rapido",
        "meta_description": (
            "Bitcoin-X e um projeto blockchain educacional. Veja como participar "
            "do airdrop pelo site oficial e cadastre-se com seguranca em poucos passos."
        ),
        "image_url": None,
        "sources_used": ["https://bitcoinx.example"],
        "word_count": 600,
    }

    airdrop_api_client.mock_generator.generate = AsyncMock(return_value=article)

    response = await airdrop_api_client.post(
        "/api/v1/airdrops/generate-post",
        json={
            "project_name": "bitcoin-x",
            "official_url": "https://bitcoinx.example",
            "referral_url": "https://ref.example/abc",
            "publish": False,
        },
        headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    # Conteúdo retornado começa com parágrafo de intro, não com H2
    assert body["preview_content"].lstrip().startswith("O bitcoin-x")


@pytest.mark.asyncio
async def test_research_failure_returns_502(airdrop_api_client):
    from app.services.airdrop.web_researcher import ResearchFailedError

    airdrop_api_client.mock_generator.generate = AsyncMock(
        side_effect=ResearchFailedError("no sources")
    )

    response = await airdrop_api_client.post(
        "/api/v1/airdrops/generate-post",
        json={
            "project_name": "Bogus",
            "official_url": "https://bogus.example",
            "referral_url": "https://ref.example/abc",
            "publish": False,
        },
        headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
    )

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_generator_returns_none_returns_422(airdrop_api_client):
    airdrop_api_client.mock_generator.generate = AsyncMock(return_value=None)

    response = await airdrop_api_client.post(
        "/api/v1/airdrops/generate-post",
        json={
            "project_name": "X",
            "official_url": "https://x.com",
            "referral_url": "https://x.com/ref",
            "publish": False,
        },
        headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
    )
    assert response.status_code == 422
