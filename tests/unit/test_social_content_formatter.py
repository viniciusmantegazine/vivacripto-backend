"""
Testes do SocialContentFormatter.

O módulo social tinha 593 linhas sem nenhum teste, e é o único código do
projeto que age FORA do sistema: publica na conta pública do Twitter. Erro ali
não estraga um artigo, estraga a conta.

O teste que mais importa é o de limite de caracteres: o Twitter rejeita acima
de 280, e a aritmética de espaço reservado estava errada por 2 caracteres —
contava 2 separadores quando o texto usa dois "\\n\\n", que são 4.
"""
import pytest

from app.services.social.content_formatter import SocialContentFormatter

TWITTER_LIMIT = 280
TWITTER_URL_LENGTH = 23


@pytest.fixture
def formatter() -> SocialContentFormatter:
    return SocialContentFormatter()


def _comprimento_efetivo(resultado) -> int:
    """
    Comprimento como o Twitter conta: a URL vale 23 chars fixos,
    independentemente do tamanho real.
    """
    return len(resultado.text) - len(resultado.url) + TWITTER_URL_LENGTH


# --- limite de caracteres ------------------------------------------------

@pytest.mark.parametrize(
    "titulo",
    [
        "Bitcoin Atinge Maxima Historica Apos Aprovacao de ETF nos EUA",
        "B" * 400,                      # uma palavra longa: sem espaço para recuar
        ("B" * 90 + " ") * 5,           # espaços raros
        "Bitcoin " * 60,                # muitos espaços
        "T" * 100,                      # limite do validador de título
    ],
)
def test_tweet_nunca_passa_de_280(formatter: SocialContentFormatter, titulo: str):
    """
    Regressão: o espaço reservado contava 2 caracteres de separador, mas o
    texto usa dois "\\n\\n" — 4 caracteres. Um título sem espaços perto do
    corte não tem recuo de truncamento para absorver a diferença, e o tweet
    chegava a 282.
    """
    resultado = formatter.format_for_twitter(titulo, "slug-de-teste", "bitcoin")

    efetivo = _comprimento_efetivo(resultado)
    assert efetivo <= TWITTER_LIMIT, (
        f"tweet com {efetivo} chars efetivos (limite {TWITTER_LIMIT})"
    )


def test_titulo_curto_nao_e_truncado(formatter: SocialContentFormatter):
    """Título dentro do limite do validador não deve perder texto."""
    titulo = "Bitcoin Atinge Maxima Historica Apos Aprovacao de ETF nos EUA"

    resultado = formatter.format_for_twitter(titulo, "slug", "bitcoin")

    assert "..." not in resultado.text.split("\n\n")[0]


def test_titulo_longo_recebe_elipse(formatter: SocialContentFormatter):
    resultado = formatter.format_for_twitter("Bitcoin " * 60, "slug", "bitcoin")

    primeira_parte = resultado.text.split("\n\n")[0]
    assert primeira_parte.endswith("...")


# --- estrutura do tweet --------------------------------------------------

def test_tweet_tem_titulo_hashtags_e_url(formatter: SocialContentFormatter):
    resultado = formatter.format_for_twitter("Bitcoin sobe forte", "meu-slug", "bitcoin")

    partes = resultado.text.split("\n\n")
    assert len(partes) == 3
    assert "#" in partes[1]
    assert partes[2] == resultado.url


def test_url_usa_o_slug_e_carrega_utm(formatter: SocialContentFormatter):
    """Os parâmetros UTM são o que permite medir tráfego vindo do social."""
    resultado = formatter.format_for_twitter("Titulo", "bitcoin-atinge-maxima", "bitcoin")

    assert "/posts/bitcoin-atinge-maxima" in resultado.url
    assert "utm_source=twitter" in resultado.url
    assert "utm_medium=social" in resultado.url


# --- hashtags ------------------------------------------------------------

def test_hashtags_da_categoria_entram(formatter: SocialContentFormatter):
    resultado = formatter.format_for_twitter("Titulo", "slug", "ethereum")

    assert any("Ethereum" in h for h in resultado.hashtags)


def test_categoria_desconhecida_usa_hashtags_base(formatter: SocialContentFormatter):
    """Categoria fora do mapa não pode gerar tweet sem hashtag nenhuma."""
    resultado = formatter.format_for_twitter("Titulo", "slug", "categoria-inexistente")

    assert resultado.hashtags


def test_sem_categoria_usa_hashtags_base(formatter: SocialContentFormatter):
    resultado = formatter.format_for_twitter("Titulo", "slug", None)

    assert resultado.hashtags


def test_hashtags_do_twitter_limitadas_a_tres(formatter: SocialContentFormatter):
    """Mais hashtags comem o espaço do título e cheiram a spam."""
    resultado = formatter.format_for_twitter("Titulo", "slug", "ethereum")

    assert len(resultado.hashtags) <= 3


def test_hashtags_nao_tem_espaco_interno(formatter: SocialContentFormatter):
    """
    Hashtag com espaço quebra em duas no Twitter. O mapa tem entradas como
    "FinançasDescentralizadas" justamente por isso.
    """
    resultado = formatter.format_for_twitter("Titulo", "slug", "defi")

    for tag in resultado.hashtags:
        assert " " not in tag, f"hashtag com espaço: {tag!r}"


# --- Instagram -----------------------------------------------------------

def test_instagram_respeita_o_limite(formatter: SocialContentFormatter):
    resultado = formatter.format_for_instagram(
        "Bitcoin " * 200, "slug", "bitcoin",
    )

    assert len(resultado.text) <= SocialContentFormatter.INSTAGRAM_MAX_LENGTH
