"""
News Context Analyzer v1.0
Analisa notícias de criptomoedas para extrair contexto semântico para geração de imagens

Este módulo identifica:
- Categoria principal (Bitcoin, Ethereum, Altcoins, DeFi, Regulação, etc.)
- Sentimento (bullish, bearish, neutro, alerta)
- Tipo de notícia (preço, regulação, tecnologia, adoção, segurança, análise)
- Entidades mencionadas (exchanges, bancos, governos, empresas, pessoas)
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from app.core.logging import logger


class NewsSentiment(Enum):
    """Sentimento da notícia para direcionamento visual"""
    BULLISH = "bullish"      # Alta, otimismo, crescimento
    BEARISH = "bearish"      # Baixa, pessimismo, queda
    NEUTRAL = "neutral"      # Informativo, análise, neutro
    WARNING = "warning"      # Alerta, cuidado, risco


class NewsType(Enum):
    """Tipo de notícia para composição visual"""
    PRICE = "price"                # Movimentação de preços, mercado
    REGULATION = "regulation"      # Regulação, governos, leis
    TECHNOLOGY = "technology"      # Atualizações técnicas, inovação
    ADOPTION = "adoption"          # Adoção empresarial/institucional
    SECURITY = "security"          # Hacks, segurança, vulnerabilidades
    ANALYSIS = "analysis"          # Análises, previsões, opiniões
    PARTNERSHIP = "partnership"    # Parcerias, integrações
    LAUNCH = "launch"              # Lançamentos, novos produtos
    LEGAL = "legal"                # Processos, ações legais


@dataclass
class EntityMention:
    """Entidade mencionada na notícia"""
    name: str
    entity_type: str  # exchange, bank, government, company, person, crypto
    relevance_score: float = 1.0


@dataclass
class NewsContext:
    """Contexto completo extraído da notícia"""
    category: str
    sentiment: NewsSentiment
    news_type: NewsType
    entities: list[EntityMention] = field(default_factory=list)
    primary_crypto: Optional[str] = None
    secondary_cryptos: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    confidence_score: float = 0.0


class NewsContextAnalyzer:
    """
    Analisador de contexto de notícias para geração inteligente de imagens

    Analisa título e conteúdo para extrair informações semânticas que
    direcionam a geração de imagens únicas e relevantes.
    """

    # === PADRÕES DE SENTIMENTO ===

    BULLISH_PATTERNS = [
        # Português
        r'\b(alta|sobe|subiu|dispara|disparam|valoriza|valorização|crescimento|cresce)\b',
        r'\b(recorde|máxima|topo|pico|rompe|rompeu|supera|superou|ultrapassa)\b',
        r'\b(otimista|otimismo|bullish|bull|positivo|ganho|lucro|recupera)\b',
        r'\b(adoção|adota|aceita|aprova|aprovação|integra|parceria)\b',
        r'\b(institucional|institucionalização|entrada|fluxo positivo)\b',
        # Inglês
        r'\b(surge|surges|rally|rallies|soars|rises|climbs|jumps|spikes)\b',
        r'\b(all-time high|ath|breakout|breaks out|bullish|moon|pumps)\b',
        r'\b(gains|profit|recovery|rebounds|adoption|approved|accepts)\b',
    ]

    BEARISH_PATTERNS = [
        # Português
        r'\b(queda|cai|caiu|despenca|despencam|desvaloriza|desvalorização)\b',
        r'\b(mínima|fundo|baixa|recua|recuou|perde|perdeu|afunda)\b',
        r'\b(pessimista|pessimismo|bearish|bear|negativo|prejuízo|perda)\b',
        r'\b(venda|vendas|liquidação|liquidações|saída|fuga|êxodo)\b',
        r'\b(crash|colapso|derrete|capitulação|fear|medo|pânico)\b',
        # Inglês
        r'\b(drops|plunges|falls|crashes|dumps|tumbles|slides|sinks)\b',
        r'\b(bearish|correction|selloff|sell-off|capitulation|fear)\b',
        r'\b(losses|loses|plummets|declines|downturn|slump)\b',
    ]

    WARNING_PATTERNS = [
        # Português
        r'\b(hack|hacker|hackeado|ataque|atacado|roubo|roubado|golpe)\b',
        r'\b(fraude|scam|esquema|pirâmide|rug pull|exploit|explorado)\b',
        r'\b(vulnerabilidade|brecha|falha|bug|crítico|urgente|alerta)\b',
        r'\b(investigação|investiga|processo|multa|sanção|banido)\b',
        r'\b(risco|arriscado|cuidado|atenção|perigo|perigoso|suspende)\b',
        # Inglês
        r'\b(hacked|breach|stolen|theft|scam|fraud|exploit|vulnerability)\b',
        r'\b(warning|alert|caution|risk|danger|sued|investigation)\b',
        r'\b(suspended|banned|delisted|shutdown|insolvency|bankrupt)\b',
    ]

    # === PADRÕES DE TIPO DE NOTÍCIA ===

    TYPE_PATTERNS = {
        NewsType.PRICE: [
            r'\b(preço|cotação|valor|us\$|dólar|usd|brl|r\$)\b',
            r'\b(price|trading|market cap|volume|bid|ask|spot)\b',
            r'\b(gráfico|candlestick|suporte|resistência|fibonacci)\b',
            r'\b(chart|support|resistance|technical analysis)\b',
            r'\b\d+[\.,]?\d*\s*(%|mil|bilhão|trilhão|k|m|b)\b',
        ],
        NewsType.REGULATION: [
            r'\b(regulação|regulamentação|lei|legislação|congresso|senado)\b',
            r'\b(sec|cftc|cvm|bacen|banco central|governo|governamental)\b',
            r'\b(compliance|kyc|aml|licença|autorização|proibição)\b',
            r'\b(regulation|regulatory|government|congress|senate|bill)\b',
            r'\b(legal framework|policy|legislation|mandate|decree)\b',
        ],
        NewsType.TECHNOLOGY: [
            r'\b(atualização|upgrade|fork|hard fork|soft fork|mainnet)\b',
            r'\b(protocolo|algoritmo|consenso|proof of|layer 2|l2)\b',
            r'\b(desenvolvimento|desenvolvedor|código|github|release)\b',
            r'\b(update|upgrade|improvement|proposal|eip|bip|testnet)\b',
            r'\b(blockchain|smart contract|dapp|defi protocol)\b',
        ],
        NewsType.ADOPTION: [
            r'\b(adoção|aceita|integra|integração|aceitar|pagamento)\b',
            r'\b(empresa|corporação|institucional|banco|fintech)\b',
            r'\b(mastercard|visa|paypal|apple|google|amazon|microsoft)\b',
            r'\b(adoption|accepts|integration|payment|merchant|retail)\b',
            r'\b(institutional|corporate|mainstream|mass adoption)\b',
        ],
        NewsType.SECURITY: [
            r'\b(hack|hacker|ataque|vulnerabilidade|exploit|brecha)\b',
            r'\b(roubo|roubado|stolen|theft|breach|compromised)\b',
            r'\b(segurança|security|audit|auditoria|bug bounty)\b',
            r'\b(phishing|malware|ransomware|backdoor|zero-day)\b',
        ],
        NewsType.ANALYSIS: [
            r'\b(análise|analista|previsão|projeção|perspectiva)\b',
            r'\b(opinião|especialista|expert|fundador|ceo)\b',
            r'\b(analysis|analyst|prediction|forecast|outlook)\b',
            r'\b(research|report|study|survey|according to)\b',
        ],
        NewsType.PARTNERSHIP: [
            r'\b(parceria|parceiro|colaboração|acordo|aliança)\b',
            r'\b(partnership|partner|collaboration|deal|alliance)\b',
            r'\b(integração|integra|junto|juntas|união)\b',
        ],
        NewsType.LAUNCH: [
            r'\b(lança|lançamento|estreia|novo|nova|inaugura)\b',
            r'\b(launch|launches|launches|debuts|introduces|unveils)\b',
            r'\b(release|releases|rollout|goes live|live now)\b',
        ],
        NewsType.LEGAL: [
            r'\b(processo|ação judicial|tribunal|juiz|multa)\b',
            r'\b(lawsuit|sue|sued|court|judge|settlement|fine)\b',
            r'\b(legal action|litigation|verdict|ruling|appeal)\b',
        ],
    }

    # === ENTIDADES CONHECIDAS ===

    KNOWN_ENTITIES = {
        # Exchanges
        'exchange': [
            'binance', 'coinbase', 'kraken', 'ftx', 'bybit', 'okx', 'kucoin',
            'huobi', 'bitfinex', 'gemini', 'bitstamp', 'mercado bitcoin',
            'bitso', 'ripio', 'foxbit', 'novadax', 'crypto.com'
        ],
        # Governos e Reguladores
        'government': [
            'sec', 'cftc', 'fed', 'federal reserve', 'banco central', 'bacen',
            'cvm', 'receita federal', 'congresso', 'senado', 'casa branca',
            'white house', 'treasury', 'tesouro', 'eua', 'brasil', 'china',
            'união europeia', 'european union', 'eu', 'hong kong', 'singapura',
            'el salvador', 'argentina', 'nigeria', 'índia', 'russia'
        ],
        # Bancos e Instituições
        'bank': [
            'jpmorgan', 'jp morgan', 'goldman sachs', 'morgan stanley',
            'blackrock', 'fidelity', 'vanguard', 'grayscale', 'ark invest',
            'bank of america', 'citibank', 'hsbc', 'santander', 'itaú',
            'bradesco', 'nubank', 'btg pactual'
        ],
        # Empresas Tech
        'company': [
            'tesla', 'microstrategy', 'square', 'block', 'paypal', 'visa',
            'mastercard', 'apple', 'google', 'meta', 'facebook', 'twitter',
            'x', 'microsoft', 'nvidia', 'amazon', 'stripe'
        ],
        # Pessoas influentes
        'person': [
            'elon musk', 'michael saylor', 'vitalik buterin', 'changpeng zhao',
            'cz', 'satoshi nakamoto', 'gary gensler', 'jerome powell',
            'cathie wood', 'brian armstrong', 'sam bankman-fried', 'sbf',
            'do kwon', 'justin sun', 'charles hoskinson', 'jack dorsey'
        ],
        # Criptomoedas principais
        'crypto': [
            'bitcoin', 'btc', 'ethereum', 'eth', 'ether', 'solana', 'sol',
            'cardano', 'ada', 'ripple', 'xrp', 'polkadot', 'dot', 'avalanche',
            'avax', 'chainlink', 'link', 'polygon', 'matic', 'dogecoin', 'doge',
            'shiba inu', 'shib', 'litecoin', 'ltc', 'uniswap', 'uni', 'aave',
            'bnb', 'binance coin', 'tether', 'usdt', 'usdc', 'dai', 'busd',
            'toncoin', 'ton', 'tron', 'trx', 'cosmos', 'atom', 'near', 'aptos',
            'arbitrum', 'arb', 'optimism', 'op', 'sui', 'sei', 'celestia', 'tia'
        ]
    }

    # Mapeamento de criptos para suas cores/identidades visuais
    CRYPTO_VISUAL_IDENTITY = {
        'bitcoin': {'color': 'golden orange', 'symbol': 'B', 'vibe': 'solid and valuable'},
        'btc': {'color': 'golden orange', 'symbol': 'B', 'vibe': 'solid and valuable'},
        'ethereum': {'color': 'purple and cyan', 'symbol': 'diamond', 'vibe': 'innovative and connected'},
        'eth': {'color': 'purple and cyan', 'symbol': 'diamond', 'vibe': 'innovative and connected'},
        'solana': {'color': 'purple gradient', 'symbol': 'wave', 'vibe': 'fast and modern'},
        'sol': {'color': 'purple gradient', 'symbol': 'wave', 'vibe': 'fast and modern'},
        'cardano': {'color': 'blue', 'symbol': 'geometric', 'vibe': 'academic and structured'},
        'ada': {'color': 'blue', 'symbol': 'geometric', 'vibe': 'academic and structured'},
        'ripple': {'color': 'blue and white', 'symbol': 'ripple', 'vibe': 'institutional and global'},
        'xrp': {'color': 'blue and white', 'symbol': 'ripple', 'vibe': 'institutional and global'},
        'dogecoin': {'color': 'golden yellow', 'symbol': 'dog', 'vibe': 'playful and community'},
        'doge': {'color': 'golden yellow', 'symbol': 'dog', 'vibe': 'playful and community'},
        'polygon': {'color': 'purple', 'symbol': 'hexagon', 'vibe': 'scalable and efficient'},
        'matic': {'color': 'purple', 'symbol': 'hexagon', 'vibe': 'scalable and efficient'},
        'avalanche': {'color': 'red', 'symbol': 'triangle', 'vibe': 'powerful and fast'},
        'avax': {'color': 'red', 'symbol': 'triangle', 'vibe': 'powerful and fast'},
        'bnb': {'color': 'golden yellow', 'symbol': 'B', 'vibe': 'exchange and utility'},
        'chainlink': {'color': 'blue', 'symbol': 'hexagon chain', 'vibe': 'connected and reliable'},
        'link': {'color': 'blue', 'symbol': 'hexagon chain', 'vibe': 'connected and reliable'},
    }

    def __init__(self):
        """Inicializa o analisador compilando os padrões regex"""
        # Pré-compilar padrões para performance
        self._bullish_regex = [re.compile(p, re.IGNORECASE) for p in self.BULLISH_PATTERNS]
        self._bearish_regex = [re.compile(p, re.IGNORECASE) for p in self.BEARISH_PATTERNS]
        self._warning_regex = [re.compile(p, re.IGNORECASE) for p in self.WARNING_PATTERNS]

        self._type_regex = {
            news_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for news_type, patterns in self.TYPE_PATTERNS.items()
        }

    def analyze(self, title: str, content: str, category: Optional[str] = None) -> NewsContext:
        """
        Analisa uma notícia e extrai seu contexto completo

        Args:
            title: Título da notícia
            content: Conteúdo/corpo da notícia
            category: Categoria pré-definida (opcional)

        Returns:
            NewsContext com todas as informações extraídas
        """
        full_text = f"{title} {content}".lower()

        # Analisar sentimento
        sentiment = self._analyze_sentiment(full_text)

        # Identificar tipo de notícia
        news_type = self._identify_news_type(full_text)

        # Extrair entidades
        entities = self._extract_entities(full_text)

        # Identificar criptomoedas mencionadas
        primary_crypto, secondary_cryptos = self._identify_cryptos(full_text, category)

        # Extrair keywords relevantes
        keywords = self._extract_keywords(full_text)

        # Calcular confiança da análise
        confidence = self._calculate_confidence(sentiment, news_type, entities)

        context = NewsContext(
            category=category or 'altcoins',
            sentiment=sentiment,
            news_type=news_type,
            entities=entities,
            primary_crypto=primary_crypto,
            secondary_cryptos=secondary_cryptos,
            keywords=keywords,
            confidence_score=confidence
        )

        logger.info(
            f"Contexto analisado: sentiment={sentiment.value}, "
            f"type={news_type.value}, primary_crypto={primary_crypto}, "
            f"entities={len(entities)}, confidence={confidence:.2f}"
        )

        return context

    def _analyze_sentiment(self, text: str) -> NewsSentiment:
        """
        Analisa o sentimento geral da notícia

        Prioridade: WARNING > BEARISH/BULLISH > NEUTRAL
        """
        warning_score = sum(1 for regex in self._warning_regex if regex.search(text))
        bullish_score = sum(1 for regex in self._bullish_regex if regex.search(text))
        bearish_score = sum(1 for regex in self._bearish_regex if regex.search(text))

        # Warning tem prioridade máxima
        if warning_score >= 2:
            return NewsSentiment.WARNING

        # Comparar bullish vs bearish
        if bullish_score > bearish_score and bullish_score >= 2:
            return NewsSentiment.BULLISH
        elif bearish_score > bullish_score and bearish_score >= 2:
            return NewsSentiment.BEARISH

        # Se houver sinais mistos ou poucos sinais, é neutro
        return NewsSentiment.NEUTRAL

    def _identify_news_type(self, text: str) -> NewsType:
        """Identifica o tipo principal da notícia"""
        type_scores = {}

        for news_type, regexes in self._type_regex.items():
            score = sum(1 for regex in regexes if regex.search(text))
            if score > 0:
                type_scores[news_type] = score

        if not type_scores:
            return NewsType.ANALYSIS  # Default para análises gerais

        return max(type_scores, key=type_scores.get)

    def _extract_entities(self, text: str) -> list[EntityMention]:
        """Extrai entidades mencionadas na notícia"""
        entities = []

        for entity_type, entity_list in self.KNOWN_ENTITIES.items():
            for entity in entity_list:
                if entity.lower() in text:
                    # Calcular relevância baseada na frequência
                    count = text.count(entity.lower())
                    relevance = min(1.0, count * 0.3)  # Max 1.0

                    entities.append(EntityMention(
                        name=entity,
                        entity_type=entity_type,
                        relevance_score=relevance
                    ))

        # Ordenar por relevância e limitar a 10 principais
        entities.sort(key=lambda x: x.relevance_score, reverse=True)
        return entities[:10]

    def _identify_cryptos(self, text: str, category: Optional[str]) -> tuple[Optional[str], list[str]]:
        """
        Identifica a criptomoeda principal e secundárias mencionadas

        Returns:
            Tuple de (crypto_principal, lista_de_secundarias)
        """
        crypto_mentions = {}

        for crypto in self.KNOWN_ENTITIES['crypto']:
            count = text.count(crypto.lower())
            if count > 0:
                # Normalizar nomes (btc -> bitcoin, eth -> ethereum)
                normalized = self._normalize_crypto_name(crypto)
                crypto_mentions[normalized] = crypto_mentions.get(normalized, 0) + count

        if not crypto_mentions:
            # Usar categoria como fallback
            if category:
                return category.lower(), []
            return None, []

        # Ordenar por frequência
        sorted_cryptos = sorted(crypto_mentions.items(), key=lambda x: x[1], reverse=True)

        primary = sorted_cryptos[0][0]
        secondary = [c[0] for c in sorted_cryptos[1:5]]  # Top 4 secundárias

        return primary, secondary

    def _normalize_crypto_name(self, crypto: str) -> str:
        """Normaliza símbolos para nomes completos"""
        mappings = {
            'btc': 'bitcoin',
            'eth': 'ethereum',
            'ether': 'ethereum',
            'sol': 'solana',
            'ada': 'cardano',
            'dot': 'polkadot',
            'avax': 'avalanche',
            'link': 'chainlink',
            'matic': 'polygon',
            'doge': 'dogecoin',
            'shib': 'shiba inu',
            'ltc': 'litecoin',
            'xrp': 'ripple',
            'uni': 'uniswap',
            'arb': 'arbitrum',
            'op': 'optimism',
            'atom': 'cosmos',
            'trx': 'tron',
            'tia': 'celestia',
        }
        return mappings.get(crypto.lower(), crypto.lower())

    def _extract_keywords(self, text: str) -> list[str]:
        """Extrai palavras-chave relevantes para contexto visual"""
        keywords = []

        # Padrões de contexto visual
        visual_patterns = [
            (r'\b(etf|spot etf|bitcoin etf)\b', 'ETF'),
            (r'\b(halving|halvening)\b', 'halving'),
            (r'\b(staking|stake)\b', 'staking'),
            (r'\b(mining|mineração|minerador)\b', 'mining'),
            (r'\b(nft|nfts|colecionável)\b', 'NFT'),
            (r'\b(metaverse|metaverso)\b', 'metaverse'),
            (r'\b(defi|finanças descentralizadas)\b', 'DeFi'),
            (r'\b(dao|organização descentralizada)\b', 'DAO'),
            (r'\b(layer 2|l2|rollup)\b', 'layer2'),
            (r'\b(wallet|carteira)\b', 'wallet'),
            (r'\b(exchange|corretora)\b', 'exchange'),
            (r'\b(whale|baleia)\b', 'whale'),
            (r'\b(airdrop|distribuição)\b', 'airdrop'),
            (r'\b(token|tokens)\b', 'token'),
            (r'\b(smart contract|contrato inteligente)\b', 'smart_contract'),
        ]

        for pattern, keyword in visual_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                keywords.append(keyword)

        return keywords[:5]  # Limitar a 5 keywords

    def _calculate_confidence(
        self,
        sentiment: NewsSentiment,
        news_type: NewsType,
        entities: list[EntityMention]
    ) -> float:
        """Calcula score de confiança da análise"""
        confidence = 0.5  # Base

        # Sentimento definido aumenta confiança
        if sentiment != NewsSentiment.NEUTRAL:
            confidence += 0.15

        # Tipo identificado aumenta confiança
        if news_type != NewsType.ANALYSIS:
            confidence += 0.15

        # Entidades encontradas aumentam confiança
        if entities:
            confidence += min(0.2, len(entities) * 0.04)

        return min(1.0, confidence)

    def get_crypto_visual_identity(self, crypto_name: str) -> dict:
        """Retorna a identidade visual de uma criptomoeda"""
        normalized = self._normalize_crypto_name(crypto_name)
        return self.CRYPTO_VISUAL_IDENTITY.get(
            normalized,
            {'color': 'blue and cyan', 'symbol': 'abstract', 'vibe': 'innovative'}
        )


# Singleton para uso global
news_context_analyzer = NewsContextAnalyzer()
