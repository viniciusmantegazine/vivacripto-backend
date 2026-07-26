"""
Testes do SocialPublisher e do TwitterAdapter.

Este é o único código do projeto que age FORA do sistema: publica na conta
pública do Twitter. Os testes aqui cobrem as duas coisas que mais importam
nesse contexto — quando ele NÃO deve publicar, e que falha dele não pode
derrubar a publicação do artigo.

Nenhum teste toca a rede: o adapter é sempre substituído por mock.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.crud.crud_social_post import crud_social_post
from app.services.social.social_publisher import SocialPublisher
from app.services.social.twitter_adapter import TwitterAdapter, TwitterPublishResult


def _post():
    """Post mínimo como o publisher espera."""
    post = MagicMock()
    post.id = "post-uuid-1"
    post.title = "Bitcoin Atinge Maxima Historica"
    post.slug = "bitcoin-atinge-maxima"
    post.featured_image_url = "https://res.cloudinary.com/x/img.jpg"
    post.category = MagicMock()
    post.category.slug = "bitcoin"
    return post


# --- quando NÃO deve publicar --------------------------------------------

@pytest.mark.asyncio
async def test_nao_publica_quando_social_esta_desabilitado(monkeypatch):
    """A chave mestra tem que valer: nada sai com ela desligada."""
    monkeypatch.setattr(
        "app.services.social.social_publisher.settings.SOCIAL_PUBLISHING_ENABLED", False
    )
    publisher = SocialPublisher()
    publisher.twitter = MagicMock()
    publisher.twitter.publish = AsyncMock()

    resultado = await publisher.publish(_post(), MagicMock())

    publisher.twitter.publish.assert_not_called()
    assert resultado.twitter is None


@pytest.mark.asyncio
async def test_nao_publica_no_twitter_quando_a_plataforma_esta_desabilitada(monkeypatch):
    monkeypatch.setattr(
        "app.services.social.social_publisher.settings.SOCIAL_PUBLISHING_ENABLED", True
    )
    monkeypatch.setattr(
        "app.services.social.social_publisher.settings.TWITTER_ENABLED", False
    )
    publisher = SocialPublisher()
    publisher.twitter = MagicMock()
    publisher.twitter.publish = AsyncMock()

    await publisher.publish(_post(), MagicMock())

    publisher.twitter.publish.assert_not_called()


def test_adapter_nao_e_construido_com_twitter_desabilitado(monkeypatch):
    monkeypatch.setattr(
        "app.services.social.social_publisher.settings.TWITTER_ENABLED", False
    )

    assert SocialPublisher().twitter is None


# --- guarda de credencial ------------------------------------------------

def test_is_configured_exige_as_quatro_credenciais(monkeypatch):
    adapter = TwitterAdapter()

    for faltante in (
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_SECRET",
    ):
        for chave in (
            "TWITTER_API_KEY",
            "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_SECRET",
        ):
            monkeypatch.setattr(
                f"app.services.social.twitter_adapter.settings.{chave}", "valor"
            )
        monkeypatch.setattr(
            f"app.services.social.twitter_adapter.settings.{faltante}", ""
        )

        assert adapter.is_configured() is False, f"faltando {faltante}"


def test_is_configured_verdadeiro_com_tudo_preenchido(monkeypatch):
    for chave in (
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_SECRET",
    ):
        monkeypatch.setattr(
            f"app.services.social.twitter_adapter.settings.{chave}", "valor"
        )

    assert TwitterAdapter().is_configured() is True


@pytest.mark.asyncio
async def test_publish_sem_credencial_falha_sem_levantar():
    """
    `is_configured` existe mas NÃO é chamado em nenhum ponto do projeto — é
    guarda morta. Sem credencial, o fluxo vai direto ao _get_client.

    Não é catastrófico porque o try/except interno converte em
    success=False em vez de propagar exceção. Este teste trava esse
    comportamento: se alguém remover o try/except, uma credencial ausente
    passaria a estourar dentro do fluxo de publicação de artigo.
    """
    adapter = TwitterAdapter()

    resultado = await adapter.publish("texto do tweet")

    assert resultado.success is False
    assert isinstance(resultado, TwitterPublishResult)


# --- isolamento de falha -------------------------------------------------

@pytest.mark.asyncio
async def test_falha_do_twitter_nao_propaga_do_publisher(monkeypatch):
    """
    Erro no Twitter tem que virar resultado, não exceção: quem chama é o
    fluxo de publicação do artigo.
    """
    monkeypatch.setattr(
        "app.services.social.social_publisher.settings.SOCIAL_PUBLISHING_ENABLED", True
    )
    monkeypatch.setattr(
        "app.services.social.social_publisher.settings.TWITTER_ENABLED", True
    )
    publisher = SocialPublisher()
    publisher.twitter = MagicMock()
    publisher.twitter.publish = AsyncMock(side_effect=RuntimeError("API do Twitter fora"))

    resultado = await publisher.publish(_post(), MagicMock())

    assert resultado.has_any_success is False


@pytest.mark.asyncio
async def test_falha_social_nao_impede_publicacao_do_artigo():
    """
    A garantia mais importante deste módulo: o artigo é o produto, o tweet é
    acessório. `_publish_to_social_media` promete no docstring que não bloqueia
    a publicação principal — este teste trava a promessa.
    """
    from app.services.automation.article_publisher import ArticlePublisher

    with patch(
        "app.services.social.SocialPublisher"
    ) as social_cls, patch(
        "app.services.automation.article_publisher.settings.SOCIAL_PUBLISHING_ENABLED",
        True,
    ):
        social_cls.side_effect = RuntimeError("modulo social explodiu")

        publisher = ArticlePublisher(MagicMock())

        # Não deve levantar
        await publisher._publish_to_social_media(_post(), MagicMock())


@pytest.mark.asyncio
async def test_has_any_success_reflete_o_resultado_do_twitter(monkeypatch):
    monkeypatch.setattr(
        "app.services.social.social_publisher.settings.SOCIAL_PUBLISHING_ENABLED", True
    )
    monkeypatch.setattr(
        "app.services.social.social_publisher.settings.TWITTER_ENABLED", True
    )
    publisher = SocialPublisher()
    publisher.twitter = MagicMock()
    publisher.twitter.publish = AsyncMock(
        return_value=TwitterPublishResult(
            success=True, tweet_id="123", tweet_url="https://x.com/i/status/123"
        )
    )

    # A persistência é via crud_social_post.create; sem mock, o db falso
    # levantaria e o resultado viraria failed pelo except de _publish_to_twitter.
    # patch.object no singleton: o pacote app.crud reexporta o nome, então
    # patch("app.crud.crud_social_post.crud_social_post") resolve para o objeto
    # e não para o módulo.
    with patch.object(crud_social_post, "create", new=AsyncMock()) as create:
        resultado = await publisher.publish(_post(), MagicMock())

    assert resultado.has_any_success is True
    assert resultado.twitter.tweet_url == "https://x.com/i/status/123"
    # O registro em banco marca sucesso — é o que permite auditar o que saiu
    assert create.await_args.kwargs["status"] == "success"


@pytest.mark.asyncio
async def test_falha_do_twitter_e_registrada_em_banco(monkeypatch):
    """
    Tweet que falha precisa deixar rastro: sem o registro, ninguém sabe que a
    conta parou de publicar.
    """
    monkeypatch.setattr(
        "app.services.social.social_publisher.settings.SOCIAL_PUBLISHING_ENABLED", True
    )
    monkeypatch.setattr(
        "app.services.social.social_publisher.settings.TWITTER_ENABLED", True
    )
    publisher = SocialPublisher()
    publisher.twitter = MagicMock()
    publisher.twitter.publish = AsyncMock(side_effect=RuntimeError("API fora"))

    # patch.object no singleton: o pacote app.crud reexporta o nome, então
    # patch("app.crud.crud_social_post.crud_social_post") resolve para o objeto
    # e não para o módulo.
    with patch.object(crud_social_post, "create", new=AsyncMock()) as create:
        resultado = await publisher.publish(_post(), MagicMock())

    assert resultado.has_any_success is False
    assert create.await_args.kwargs["status"] == "failed"
    assert "API fora" in create.await_args.kwargs["error_message"]
