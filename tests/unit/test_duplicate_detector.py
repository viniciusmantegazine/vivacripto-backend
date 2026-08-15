"""
Testes do DuplicateDetector — a segunda camada de deduplicação, que compara
um artigo recém-gerado contra posts publicados nas últimas 24h.

Contexto de por que este arquivo existe: o módulo tem 555 linhas e estava sem
nenhum teste, e o comentário do SOURCE_DEDUP_THRESHOLD em news_aggregator.py
apoiava a escolha daquele valor na premissa de que esta camada absorveria
falsos negativos. A premissa era falsa — ver
test_threshold_de_080_nao_dispara_em_duplicata_real.

Os testes aqui são de CARACTERIZAÇÃO: documentam o comportamento atual, mesmo
onde ele é questionável, para que qualquer mudança futura seja deliberada. Onde
o comportamento documentado é problemático, o docstring diz por quê.

Só cobrem a superfície viva do módulo. `PipelineOrchestrator` e
`process_assignment` não têm nenhum consumidor no projeto (~150 linhas mortas)
e ficam de fora de propósito.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.deduplication.duplicate_detector import (
    ActionType,
    DuplicateDetector,
    NewsAssignment,
    PublishedPost,
)


def _assignment(titulo="Sberbank Anuncia Infraestrutura de Negociacao Cripto",
                resumo="O maior banco da Russia vai lancar negociacao de criptomoedas.",
                conteudo="## Sberbank entra no mercado cripto\n\nO Sberbank anunciou planos.",
                fonte="CoinDesk") -> NewsAssignment:
    return NewsAssignment(
        titulo=titulo,
        resumo=resumo,
        conteudo=conteudo,
        fonte=fonte,
        timestamp="2026-07-26T12:00:00",
    )


def _post(post_id="post-1", titulo="Titulo do post publicado",
          resumo="Resumo do post.", conteudo="Conteudo do post publicado.") -> PublishedPost:
    return PublishedPost(
        id=post_id,
        titulo=titulo,
        resumo=resumo,
        conteudo=conteudo,
        data_criacao="2026-07-26T10:00:00",
        data_atualizacao="2026-07-26T10:00:00",
        fonte="Cointelegraph",
    )


@pytest.fixture(autouse=True)
def sem_engine_real():
    """
    Impede que __init__ construa o engine de similaridade de verdade.

    O default de engine_type é "hybrid", que carrega modelo de embeddings — e
    cada teste aqui substitui o engine logo depois de construir o detector, de
    modo que carregar o real é desperdício puro. Sem este patch a suíte deste
    arquivo levava 272 segundos.
    """
    with patch(
        "app.services.deduplication.duplicate_detector.SimilarityFactory.create",
        return_value=MagicMock(),
    ) as factory:
        yield factory


def _detector(posts, score=0.0, threshold=0.80, erro=None):
    """
    Detector com repositório e engine de similaridade controlados.

    `score` é o valor que o engine devolve para qualquer par; `erro`, se dado,
    é levantado pelo engine.
    """
    repo = MagicMock()
    repo.get_posts_last_24h = AsyncMock(return_value=posts)

    detector = DuplicateDetector(repository=repo, similarity_threshold=threshold)

    engine = MagicMock()
    if erro is not None:
        engine.calculate = MagicMock(side_effect=erro)
    else:
        resultado = MagicMock()
        resultado.score = score
        engine.calculate = MagicMock(return_value=resultado)
    detector.similarity_engine = engine

    return detector, repo, engine


# --- NewsAssignment ------------------------------------------------------

def test_assignment_gera_id_automatico():
    a = _assignment()
    b = _assignment()

    assert a.id and b.id
    assert a.id != b.id


def test_assignment_respeita_id_informado():
    a = NewsAssignment(
        titulo="t", resumo="r", conteudo="c", fonte="f",
        timestamp="2026-07-26T12:00:00", id="fixo-123",
    )

    assert a.id == "fixo-123"


def test_combined_text_inclui_conteudo_por_padrao():
    a = _assignment(titulo="TITULO", resumo="RESUMO", conteudo="CONTEUDO")

    texto = a.get_combined_text()

    assert "TITULO" in texto and "RESUMO" in texto and "CONTEUDO" in texto


def test_combined_text_pode_excluir_conteudo():
    a = _assignment(titulo="TITULO", resumo="RESUMO", conteudo="CONTEUDO")

    texto = a.get_combined_text(include_content=False)

    assert "TITULO" in texto and "RESUMO" in texto
    assert "CONTEUDO" not in texto


def test_combined_text_trunca_conteudo_em_500_chars():
    """
    O corte em 500 é o que o detector compara. Importa porque duas notícias
    sobre o mesmo fato divergem mais no fim do texto que no lead.
    """
    a = _assignment(conteudo="x" * 900)

    texto = a.get_combined_text()

    assert texto.count("x") == 500


# --- check_duplicate: caminhos de decisão --------------------------------

@pytest.mark.asyncio
async def test_sem_posts_recentes_cria_novo():
    detector, _, engine = _detector(posts=[])

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.CREATE_NEW
    assert "24 horas" in resultado.motivo
    engine.calculate.assert_not_called()


@pytest.mark.asyncio
async def test_similaridade_acima_do_threshold_atualiza():
    detector, _, _ = _detector(posts=[_post("post-42")], score=0.91)

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.UPDATE_EXISTING
    assert resultado.post_existente_id == "post-42"
    assert resultado.similaridade_maxima == 0.91


@pytest.mark.asyncio
async def test_similaridade_abaixo_do_threshold_cria_novo():
    detector, _, _ = _detector(posts=[_post()], score=0.42)

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.CREATE_NEW
    assert resultado.similaridade_maxima == 0.42


@pytest.mark.asyncio
async def test_threshold_e_inclusivo():
    """Score exatamente igual ao threshold conta como duplicata (>=)."""
    detector, _, _ = _detector(posts=[_post()], score=0.80, threshold=0.80)

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.UPDATE_EXISTING


@pytest.mark.asyncio
async def test_escolhe_o_post_mais_similar_entre_varios():
    """Com vários candidatos, o update vai para o de maior similaridade."""
    posts = [_post("post-a"), _post("post-b"), _post("post-c")]
    detector, _, engine = _detector(posts=posts)

    def scores(texto_a, texto_b):
        # o post-b é o mais parecido
        r = MagicMock()
        r.score = 0.95 if "post-b" in texto_b or "B-MARCADOR" in texto_b else 0.50
        return r

    posts[1].conteudo = "B-MARCADOR conteudo"
    engine.calculate = MagicMock(side_effect=scores)

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.UPDATE_EXISTING
    assert resultado.post_existente_id == "post-b"


@pytest.mark.asyncio
async def test_candidatos_similares_traz_no_maximo_tres():
    posts = [_post(f"post-{i}") for i in range(6)]
    detector, _, _ = _detector(posts=posts, score=0.10)

    resultado = await detector.check_duplicate(_assignment())

    assert len(resultado.candidatos_similares) == 3


# --- check_duplicate: falha do engine ------------------------------------

@pytest.mark.asyncio
async def test_erro_no_engine_para_todos_os_posts_cria_novo():
    """
    Fallback deliberadamente permissivo: sem conseguir comparar, publica.
    O risco assumido é duplicar em vez de perder a notícia.
    """
    detector, _, _ = _detector(posts=[_post()], erro=RuntimeError("engine fora"))

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.CREATE_NEW
    assert "Erro ao calcular similaridades" in resultado.motivo


@pytest.mark.asyncio
async def test_erro_em_um_post_nao_impede_comparar_os_outros():
    """Falha isolada não descarta os candidatos restantes."""
    posts = [_post("post-ruim"), _post("post-bom")]
    detector, _, engine = _detector(posts=posts)

    chamadas = {"n": 0}

    def as_vezes_falha(a, b):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise RuntimeError("falha no primeiro")
        r = MagicMock()
        r.score = 0.93
        return r

    engine.calculate = MagicMock(side_effect=as_vezes_falha)

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.UPDATE_EXISTING
    assert resultado.post_existente_id == "post-bom"


# --- o achado que motivou este arquivo (resolvido em 2026-08-15) ----------
#
# O teste-sentinela test_threshold_de_080_nao_dispara_em_duplicata_real vivia
# aqui e falhava de propósito quando o threshold fosse corrigido. Foi. Os
# testes abaixo o substituem, como o docstring dele instruía, usando a
# validação com dado de produção que ele pedia: em 2026-08-15 o site publicou
# duas duplicatas reais que o threshold de 0.80 deixou passar (pares Tether e
# Dashjr abaixo, ambos dentro da mesma janela de 24h). Medido com o engine
# TF-IDF sobre os artigos publicados (texto como o detector compara,
# titulo + resumo + conteudo[:500]):
#
#   - duplicata real publicada:            0.7219 e 0.7279
#   - mesma história, ângulos diferentes:  0.3967  (par Clarity Act)
#   - notícias distintas:                  0.2346 a 0.2652
#
# A medição sintética anterior (pares imitados à mão) dava mesmo-evento em
# 0.535-0.619; artigos gerados de verdade convergem mais em vocabulário e
# pontuam mais alto. O threshold 0.55 cobre as duas medições com margem de
# 0.15 sobre o pior não-duplicata real. Falso positivo aqui sobrescreve um
# post publicado (ver test_update_sobrescreve_e_nao_mescla_conteudo), então
# ao recalibrar, erre para cima.

# Fixtures reais: publicados em verticecripto.com.br, capturados em 2026-08-15.
# titulo = og:title, resumo = meta description, conteudo = 500 chars do corpo.
_TETHER_13_08 = dict(
    titulo="Tether Conclui Auditoria Financeira com KPMG: Reforço de Confiança no Mercado Cripto",
    resumo="Descubra os detalhes da auditoria da Tether pela KPMG e como a validação de suas reservas impacta a confiança nas stablecoins e o ecossistema cripto g...",
    conteudo='Tether Anuncia Auditoria Financeira Histórica pela KPMG e Reforça Transparência A Tether, empresa por trás da maior stablecoin USDT , comunicou que a KPMG, uma das quatro maiores firmas de auditoria do mundo, emitiu uma opinião de auditoria sem ressalvas sobre as demonstrações financeiras de 2025 da Tether International. A companhia descreveu o processo como a "maior auditoria financeira inaugural da história", um marco significativo após anos de questionamentos sobre o lastro de seus ativos. Es',
)
_TETHER_14_08 = dict(
    titulo="Auditoria KPMG da Tether Reforça Confiança no USDT e no Mercado Cripto",
    resumo="A auditoria da KPMG na Tether reforça a confiança no USDT, impactando o mercado de criptomoedas. Entenda as implicações para o Brasil e o futuro das s...",
    conteudo='Tether Conquista Auditoria Completa da KPMG, Reforçando Confiança no USDT A Tether, emissora da maior stablecoin do mercado, USDT , anunciou na quinta-feira que a renomada firma de auditoria Big Four, KPMG, emitiu uma opinião sem ressalvas sobre suas demonstrações financeiras de 2025. Este marco representa a "maior auditoria financeira inaugural da história", conforme a empresa, e aborda anos de questionamentos sobre a real sustentação de suas reservas. A KPMG examinou minuciosamente os ativos, ',
)
_DASHJR_MANHA = dict(
    titulo="Bitcoin: Luke Dashjr Removido da Edição de Propostas de Melhoria (BIPs)",
    resumo="A remoção de Luke Dashjr como editor de BIPs no Bitcoin levanta discussões sobre governança e o futuro das propostas de melhoria na rede. Entenda o im...",
    conteudo="Governança do Bitcoin em Foco: Remoção de Editor de BIPs Gera Debate O desenvolvedor de Bitcoin, Luke Dashjr, foi removido de suas funções como editor de Bitcoin Improvement Proposals (BIPs), as propostas de melhoria para a rede. A decisão, que gerou controvérsia, ocorreu após desenvolvedores levantarem preocupações sobre a conduta de Dashjr em relação ao BIP 110. Este incidente sublinha a complexidade da governança descentralizada e a importância da imparcialidade no processo de evolução do pro",
)
_DASHJR_NOITE = dict(
    titulo="Desenvolvedor Luke Dashjr Removido do Cargo de Editor de BIPs do Bitcoin",
    resumo="A remoção de Luke Dashjr como editor de BIPs do Bitcoin levanta questões sobre governança e consenso na rede. Entenda o impacto da falha do BIP-110 e ...",
    conteudo="O desenvolvedor de Bitcoin Luke Dashjr foi removido de sua posição como editor de Propostas de Melhoria do Bitcoin (BIPs), conforme votação de outros desenvolvedores e publicação no GitHub de BIPs no último domingo. A decisão ocorreu após a falha da proposta BIP-110, que visava reduzir o spam na rede, e acusações de que Dashjr teria exercido sua autoridade editorial de forma inconsistente, favorecendo a própria proposta. Este evento sublinha as complexidades da governança descentralizada e a imp",
)
_TESOURO_SANCOES = dict(
    titulo="Regulação: Tesouro dos EUA Sanciona Exchanges Cripto por Lavagem para o Irã",
    resumo="Entenda as sanções do Tesouro dos EUA contra exchanges cripto ligadas ao Irã, o impacto da regulação global e como isso se relaciona com o cenário bra...",
    conteudo='Regulação Global: Tesouro dos EUA Sanciona Exchanges Cripto por Lavagem para o Irã O Tesouro dos Estados Unidos, por meio do Escritório de Controle de Ativos Estrangeiros (OFAC), impôs sanções a duas exchanges de criptomoedas, Shelbit Exchange e Aban Tether, no dia 7 de agosto. As plataformas são acusadas de movimentar milhões de dólares em ativos digitais para as Forças Armadas iranianas e outras entidades já sob sanção. Esta ação faz parte da campanha "Economic Fury", que visa desmantelar as r',
)
_CLARITY_ADIADA = dict(
    titulo="Regulação Cripto nos EUA: Votação do Clarity Act Adiada para Setembro",
    resumo="Entenda o contexto do Clarity Act nos EUA, as tensões políticas e como o atraso na regulação pode influenciar o mercado cripto global e as discussões ...",
    conteudo="A votação do aguardado Clarity Act, legislação fundamental para a regulação de criptomoedas nos Estados Unidos, foi postergada para setembro. A decisão ocorre enquanto os legisladores entram em recesso, adiando o avanço de um projeto de lei que já havia sido aprovado pela Câmara dos Representantes. A medida reflete as contínuas tensões políticas em Washington, com acusações de que os democratas estariam atrasando o processo legislativo. O líder da maioria, John Thune, confirmou que a votação ser",
)
_CLARITY_TRAVA = dict(
    titulo="Regulação Cripto nos EUA: Projeto de Lei Trava, Mas Agências Avançam",
    resumo="Analise como o impasse regulatório nos EUA impacta o mercado cripto global e o que a continuidade das ações das agências significa para investidores b...",
    conteudo="Impasse Legislativo nos EUA: Regulação Cripto Avança por Outras Vias O projeto de lei Digital Asset Market Clarity Act, que buscava estabelecer um arcabouço regulatório claro para criptoativos nos Estados Unidos, não obteve a votação necessária no Senado antes do recesso de verão. Este revés, embora significativo, não representa um fim para a esperança de políticas cripto no país, pois agências reguladoras já implementam diretrizes. A legislação visava definir a distinção entre valores mobiliári",
)


def _detector_de_producao(post_publicado: dict):
    """
    Detector como o news_pipeline constrói: threshold e engine dos settings,
    engine TF-IDF REAL (não mock) — é a interação threshold × engine que estes
    testes travam.
    """
    from app.core.config import settings
    from app.services.deduplication.similarity_engine import TFIDFSimilarity

    assert settings.DEDUPLICATION_ENGINE == "tfidf", (
        "estes testes calibram o threshold para o engine tfidf; se o engine "
        "de produção mudou, a calibração precisa ser refeita (ver comentário "
        "acima das fixtures)"
    )

    repo = MagicMock()
    repo.get_posts_last_24h = AsyncMock(return_value=[
        _post("post-publicado", **post_publicado)
    ])
    detector = DuplicateDetector(
        repository=repo,
        similarity_threshold=settings.DEDUPLICATION_THRESHOLD,
    )
    detector.similarity_engine = TFIDFSimilarity()
    return detector


@pytest.mark.asyncio
@pytest.mark.parametrize("publicado,novo", [
    (_TETHER_13_08, _TETHER_14_08),
    (_DASHJR_MANHA, _DASHJR_NOITE),
])
async def test_config_de_producao_pega_duplicata_real_publicada(publicado, novo):
    """
    Regressão dos dois pares de duplicata que o site publicou (Tether/KPMG em
    13-14/08 e Luke Dashjr duas vezes em 11/08, ambos dentro da janela de
    24h). Com threshold 0.80 os dois pontuavam ~0.72 e viravam CREATE_NEW.
    """
    detector = _detector_de_producao(publicado)

    resultado = await detector.check_duplicate(_assignment(**novo))

    assert resultado.acao == ActionType.UPDATE_EXISTING, (
        f"duplicata real pontuou {resultado.similaridade_maxima:.4f}, abaixo "
        f"do threshold {detector.similarity_threshold} — conteúdo duplicado "
        f"seria PUBLICADO"
    )
    assert resultado.post_existente_id == "post-publicado"


@pytest.mark.asyncio
@pytest.mark.parametrize("publicado,novo", [
    (_TESOURO_SANCOES, _CLARITY_ADIADA),
    (_TESOURO_SANCOES, _CLARITY_TRAVA),
])
async def test_config_de_producao_nao_marca_noticias_distintas(publicado, novo):
    """
    A fronteira do outro lado: notícias distintas da mesma editoria e da mesma
    janela (pares reais, ~0.23-0.27) precisam de folga larga até o threshold,
    porque falso positivo sobrescreve o post existente.
    """
    detector = _detector_de_producao(publicado)

    resultado = await detector.check_duplicate(_assignment(**novo))

    assert resultado.acao == ActionType.CREATE_NEW
    assert resultado.similaridade_maxima < detector.similarity_threshold - 0.15, (
        "par distinto chegou a menos de 0.15 do threshold — a margem contra "
        "falso positivo (que sobrescreve post publicado) está fina demais"
    )


@pytest.mark.asyncio
async def test_mesma_historia_com_angulo_proprio_vira_post_novo():
    """
    Decisão editorial deliberada: o par real do Clarity Act (mesma pauta, 6h
    de diferença, ângulos diferentes — "votação adiada" vs "agências avançam")
    pontua 0.3967 e fica ABAIXO do threshold. Cobertura em evolução gera post
    novo; UPDATE_EXISTING é só para releitura do mesmo fato, porque sobrescreve
    o post alvo. Se este teste falhar após recalibração, o threshold desceu
    demais.
    """
    detector = _detector_de_producao(_CLARITY_ADIADA)

    resultado = await detector.check_duplicate(_assignment(**_CLARITY_TRAVA))

    assert resultado.acao == ActionType.CREATE_NEW


@pytest.mark.asyncio
async def test_update_sobrescreve_e_nao_mescla_conteudo():
    """
    Documenta o custo de um falso positivo nesta camada, que é mais alto que
    na deduplicação de fontes.

    O detector devolve apenas o ID do post a atualizar; quem aplica é
    ArticlePublisher.update_article, que SOBRESCREVE o post inteiro (título,
    corpo, excerpt e meta acompanham o conteúdo novo; só o slug é preservado)
    — sem mesclar e sem guardar histórico.

    Consequências de um falso positivo: o artigo publicado é destruído e a
    nova história não ganha post próprio. Por isso o threshold é calibrado
    errando para o lado conservador (ver comentário acima das fixtures).
    """
    detector, _, _ = _detector(posts=[_post("post-existente")], score=0.95)

    resultado = await detector.check_duplicate(_assignment())

    # O detector não carrega conteúdo a mesclar: só aponta o alvo.
    assert resultado.acao == ActionType.UPDATE_EXISTING
    assert resultado.post_existente_id == "post-existente"
    assert not hasattr(resultado, "conteudo_mesclado")
