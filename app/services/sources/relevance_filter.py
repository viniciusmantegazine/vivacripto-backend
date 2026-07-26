"""
Filtro de relevância na coleta de notícias.

O pipeline não tinha filtro de tema: qualquer item coletado virava candidato a
artigo, e `category_classifier` defaulta para 'altcoins' quando nada casa. Como
quase toda notícia tem source_count=1, a fila é efetivamente ordenada por
recência — um item de IA publicado minutos antes do run ia ao topo.

Direção do teste: descarta quando há sinal de OUTRA editoria E não há sinal de
cripto. O inverso (allowlist de cripto) foi medido e falha: perdeu Shiba Inu,
Odos Protocol, HTX e Bitchat, porque vocabulário exaustivo de cripto não existe
de forma estável — nasce nome novo toda semana.
"""
import re
from typing import Dict, Optional, Sequence

from loguru import logger


class RelevanceFilter:
    """Decide se uma notícia coletada pertence à editoria do site."""

    # Pauta de outra editoria. Hoje só IA, que é o agrupamento medido: o
    # Decrypt é tanto publicação de IA quanto de cripto. Só cresce com
    # evidência de feed real, nunca por suposição.
    OFF_BEAT_PATTERNS = (
        # Laboratórios e modelos, por NOME PRÓPRIO. Nome próprio é o que
        # resolve o caso "Chinese AI ... Chinese model GLM 5.2", que não casava
        # com jargão nenhum. Note que NÃO existe um `\bai\b` solto aqui:
        # matéria de cripto cita IA o tempo todo ("Is the AI-to-crypto rotation
        # underway?"), e um padrão largo faria tudo depender do veto.
        r"\bopenai\b", r"\banthropic\b", r"\bhugging ?face\b", r"\bmistral\b",
        r"\bdeepseek\b", r"\bqwen\b", r"\bllama\b", r"\bchatgpt\b", r"\bgpt-?\d",
        r"\bclaude\b", r"\bglm\b", r"\bthinking machines\b",
        r"\bblack forest labs\b", r"\bmidjourney\b", r"\bopenrouter\b",
        # NAO acrescentar substantivo geral de tecnologia aqui. Esta lista ja
        # teve `nvidia`, `gpus?`, `data ?centers?`, `benchmarks?`,
        # `quantum comput`, `robots?` e `self-driving`. Ablacao leave-one-out
        # contra o feed vivo: os sete custavam ZERO descartes, juntos ou
        # separados, e derrubavam noticia legitima de cripto —
        # "Riot Platforms converts Texas data center to high-performance
        # compute" (minerador de bitcoin), "Fed holds benchmark rate steady",
        # "A16z leads round in decentralized GPU marketplace". O pivo de
        # minerador para data center de IA e pauta central de cripto e nao
        # carrega termo nenhum do veto.
        #
        # O criterio desta lista e: NOME PROPRIO de laboratorio/modelo de IA,
        # ou jargao especifico de IA. Nunca substantivo que cripto tambem usa.
        # Jargão de IA
        r"\bai (model|lab|labs|startup|safety|agent|agents|kill switch)\b",
        r"\bllms?\b", r"\blarge language model", r"\bchatbot",
        r"\b(image|video|frontier|open-weight) models?\b",
        r"\bopen-?source ai\b",
    )

    # Veto. Precisa ser ESPECÍFICA: moeda nomeada, ticker, exchange nomeada,
    # empresa de cripto, jargão próprio.
    #
    # PROIBIDO acrescentar palavra genérica de negócios aqui. Na primeira
    # medição o veto tinha `hack`, e isso deixou passar "Nvidia, Meta, and
    # Microsoft Tell Washington: Don't Kill Open-Source AI" — o resumo dizia
    # "survive a hack", e uma palavra que qualquer setor usa anulou dois sinais
    # corretos. Mesma proibição para: protocol, exchange, treasury, node,
    # bridge, ledger, circle, ada.
    #
    # `gemini` fica AQUI e não na OFF_BEAT: é exchange de cripto (Winklevoss)
    # além de modelo do Google. A ambiguidade foi resolvida para o lado
    # permissivo, que é o barato.
    CRYPTO_SIGNAL_PATTERNS = (
        # Guarda-chuva
        r"\bcrypto", r"\bblockchain\b", r"\bweb3\b", r"\bdefi\b", r"\bnfts?\b",
        r"\bdaos?\b", r"\bstablecoins?\b", r"\baltcoins?\b", r"\bmemecoins?\b",
        r"\bdigital assets?\b", r"\bon-?chain\b", r"\btokens?\b", r"\btokeni[sz]",
        # Moedas e tickers
        r"\bbitcoins?\b", r"\bbtc\b", r"\bethereum\b", r"\beth\b", r"\bsolana\b",
        r"\bxrp\b", r"\bripple\b", r"\bcardano\b", r"\bdogecoins?\b", r"\bshiba\b",
        r"\blitecoin\b", r"\bpolkadot\b", r"\bchainlink\b", r"\btether\b",
        r"\busdt\b", r"\busdc\b", r"\bbnb\b",
        # Exchanges e empresas
        r"\bbinance\b", r"\bcoinbase\b", r"\bkraken\b", r"\bbybit\b", r"\bhtx\b",
        r"\bokx\b", r"\bgemini\b", r"\bmicrostrategy\b", r"\bgrayscale\b",
        r"\bgalaxy\b", r"\bpantera\b", r"\bmetamask\b", r"\bopensea\b",
        r"\buniswap\b",
        # Jargão próprio
        r"\bhodl\b", r"\bsatoshi\b", r"\bhalving\b", r"\bhashrate\b",
        r"\bairdrops?\b", r"\bstaking\b", r"\bvalidators?\b", r"\brollups?\b",
        r"\bl2s?\b", r"\bdexe?s?\b", r"\btvl\b", r"\bmining\b", r"\bminers?\b",
        r"\bsmart contracts?\b", r"\betfs?\b", r"\bwallets?\b", r"\bcustody\b",
    )

    def __init__(self):
        self._off_beat = self._compile(self.OFF_BEAT_PATTERNS, "OFF_BEAT_PATTERNS")
        self._crypto = self._compile(
            self.CRYPTO_SIGNAL_PATTERNS, "CRYPTO_SIGNAL_PATTERNS"
        )

    @staticmethod
    def _compile(patterns: Sequence[str], nome: str) -> Optional["re.Pattern[str]"]:
        """
        Compila o vocabulário. Padrão inválido desativa o filtro em vez de
        derrubar a construção do NewsAggregator — e com ele o pipeline inteiro.
        """
        try:
            return re.compile("|".join(patterns), re.IGNORECASE)
        except Exception as e:
            logger.error(
                f"Vocabulário {nome} inválido ({e}); "
                f"filtro de relevância DESATIVADO, tudo passa"
            )
            return None

    def rejection_reason(self, news: Dict) -> Optional[str]:
        """
        Devolve o termo de outra editoria que motivou o descarte, ou None se a
        notícia for relevante.

        Uma primitiva só, devolvendo decisão e motivo juntos: o chamador testa
        `is None` e usa o valor na linha de log. Evita ter is_relevant() e
        reason() que podem divergir.

        O chamador DEVE testar `is None`, nunca truthiness: um vocabulário
        vazio compila para um casamento de largura zero, e o método pode
        legitimamente devolver `''`.
        """
        try:
            if self._off_beat is None or self._crypto is None:
                return None

            texto = f"{news.get('title', '')} {news.get('description', '')}"

            off_beat_match = self._off_beat.search(texto)
            if not off_beat_match:
                return None
            if self._crypto.search(texto):
                return None
            return off_beat_match.group(0)

        except Exception as e:
            # Falha ABRE. Mesma assimetria do threshold de deduplicação:
            # descartar notícia real é o erro caro, porque o leitor nunca a vê
            # e ninguém percebe. Artigo fora de tema é visível e removível.
            logger.warning(f"Erro no filtro de relevância ({e}); deixando passar")
            return None
