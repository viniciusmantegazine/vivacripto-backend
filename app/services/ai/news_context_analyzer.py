"""
News Context Analyzer v2.0 - Editorial Photography Style
Analisa notícias de criptomoedas para extrair contexto semântico para geração de imagens EDITORIAIS

Este módulo identifica:
- Tipo de entidade principal (cripto, empresa, pessoa, instituição, tema)
- Entidade específica (Bitcoin, JPMorgan, SEC, etc.)
- Ação/verbo da notícia (lança, alerta, sobe, cai)
- Sentimento (positivo, negativo, neutro)
- Presença de dados numéricos (para overlay de gráficos)

IMPORTANTE: Este analisador é otimizado para gerar prompts no estilo EDITORIAL FOTOGRÁFICO,
não ilustrações abstratas. Os resultados direcionam a seleção de elementos visuais concretos.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from app.core.logging import logger


class NewsSentiment(Enum):
    """Sentimento da notícia para direcionamento visual editorial"""
    POSITIVE = "positive"    # Alta, otimismo, crescimento, lançamento
    NEGATIVE = "negative"    # Baixa, alerta, crise, risco
    NEUTRAL = "neutral"      # Informativo, análise, neutro


class NewsType(Enum):
    """Tipo de notícia para composição visual editorial"""
    PRICE = "price"                # Movimentação de preços, mercado
    REGULATION = "regulation"      # Regulação, governos, leis
    TECHNOLOGY = "technology"      # Atualizações técnicas, inovação
    ADOPTION = "adoption"          # Adoção empresarial/institucional
    SECURITY = "security"          # Hacks, segurança, vulnerabilidades
    ANALYSIS = "analysis"          # Análises, previsões, opiniões
    PARTNERSHIP = "partnership"    # Parcerias, integrações
    LAUNCH = "launch"              # Lançamentos, novos produtos
    LEGAL = "legal"                # Processos, ações legais
    MINING = "mining"              # Mineração de criptomoedas


class EntityType(Enum):
    """Tipo de entidade principal da notícia"""
    CRYPTO = "crypto"              # Criptomoeda (Bitcoin, Ethereum, etc.)
    EXCHANGE = "exchange"          # Exchange (Binance, Coinbase, etc.)
    BANK = "bank"                  # Banco/instituição financeira
    GOVERNMENT = "government"      # Governo/regulador
    COMPANY = "company"            # Empresa de tecnologia
    PERSON = "person"              # Pessoa (CEO, desenvolvedor, etc.)
    DEFI = "defi"                  # Protocolo DeFi
    NFT = "nft"                    # NFT/arte digital
    STABLECOIN = "stablecoin"      # Stablecoin
    THEME = "theme"                # Tema genérico


@dataclass
class EntityMention:
    """Entidade mencionada na notícia"""
    name: str
    entity_type: EntityType
    display_name: str  # Nome para exibição/busca visual
    relevance_score: float = 1.0


@dataclass
class NewsAction:
    """Ação/verbo principal da notícia"""
    action: str           # Ação simplificada (lanca, alerta, sobe, cai, etc.)
    original_match: str   # Termo original encontrado
    implies_data: bool    # Se a ação implica dados numéricos


@dataclass
class NewsContext:
    """Contexto completo extraído da notícia para geração editorial"""
    # Entidade principal
    entity_type: EntityType
    primary_entity: Optional[str]
    primary_entity_display: str

    # Análise semântica
    sentiment: NewsSentiment
    news_type: NewsType
    action: NewsAction

    # Dados numéricos
    has_numeric_data: bool
    numeric_context: Optional[str]  # "percentage", "price", "volume", etc.

    # Entidades secundárias
    secondary_entities: list[EntityMention] = field(default_factory=list)

    # Keywords para contexto adicional
    keywords: list[str] = field(default_factory=list)

    # Confiança da análise
    confidence_score: float = 0.0


class NewsContextAnalyzer:
    """
    Analisador de contexto de notícias v2.0 - Editorial Photography Style

    Otimizado para extrair informações que direcionam a geração de
    imagens no estilo EDITORIAL FOTOGRÁFICO profissional.
    """

    # === ENTIDADES CONHECIDAS COM IDENTIDADE VISUAL ===

    # Criptomoedas principais com identidade visual
    CRYPTO_ENTITIES = {
        # Bitcoin
        'bitcoin': {'display': 'Bitcoin', 'type': EntityType.CRYPTO, 'aliases': ['btc']},
        'btc': {'display': 'Bitcoin', 'type': EntityType.CRYPTO, 'aliases': []},

        # Ethereum
        'ethereum': {'display': 'Ethereum', 'type': EntityType.CRYPTO, 'aliases': ['eth', 'ether']},
        'eth': {'display': 'Ethereum', 'type': EntityType.CRYPTO, 'aliases': []},

        # Solana
        'solana': {'display': 'Solana', 'type': EntityType.CRYPTO, 'aliases': ['sol']},
        'sol': {'display': 'Solana', 'type': EntityType.CRYPTO, 'aliases': []},

        # XRP/Ripple
        'xrp': {'display': 'XRP', 'type': EntityType.CRYPTO, 'aliases': ['ripple']},
        'ripple': {'display': 'XRP', 'type': EntityType.CRYPTO, 'aliases': []},

        # Cardano
        'cardano': {'display': 'Cardano', 'type': EntityType.CRYPTO, 'aliases': ['ada']},
        'ada': {'display': 'Cardano', 'type': EntityType.CRYPTO, 'aliases': []},

        # BNB
        'bnb': {'display': 'BNB', 'type': EntityType.CRYPTO, 'aliases': ['binance coin']},

        # Dogecoin
        'dogecoin': {'display': 'Dogecoin', 'type': EntityType.CRYPTO, 'aliases': ['doge']},
        'doge': {'display': 'Dogecoin', 'type': EntityType.CRYPTO, 'aliases': []},

        # Polygon
        'polygon': {'display': 'Polygon', 'type': EntityType.CRYPTO, 'aliases': ['matic']},
        'matic': {'display': 'Polygon', 'type': EntityType.CRYPTO, 'aliases': []},

        # Avalanche
        'avalanche': {'display': 'Avalanche', 'type': EntityType.CRYPTO, 'aliases': ['avax']},
        'avax': {'display': 'Avalanche', 'type': EntityType.CRYPTO, 'aliases': []},

        # Chainlink
        'chainlink': {'display': 'Chainlink', 'type': EntityType.CRYPTO, 'aliases': ['link']},
        'link': {'display': 'Chainlink', 'type': EntityType.CRYPTO, 'aliases': []},

        # Polkadot
        'polkadot': {'display': 'Polkadot', 'type': EntityType.CRYPTO, 'aliases': ['dot']},
        'dot': {'display': 'Polkadot', 'type': EntityType.CRYPTO, 'aliases': []},

        # Litecoin
        'litecoin': {'display': 'Litecoin', 'type': EntityType.CRYPTO, 'aliases': ['ltc']},
        'ltc': {'display': 'Litecoin', 'type': EntityType.CRYPTO, 'aliases': []},

        # Uniswap
        'uniswap': {'display': 'Uniswap', 'type': EntityType.DEFI, 'aliases': ['uni']},

        # Aave
        'aave': {'display': 'Aave', 'type': EntityType.DEFI, 'aliases': []},

        # Cosmos
        'cosmos': {'display': 'Cosmos', 'type': EntityType.CRYPTO, 'aliases': ['atom']},
        'atom': {'display': 'Cosmos', 'type': EntityType.CRYPTO, 'aliases': []},

        # Near
        'near': {'display': 'Near Protocol', 'type': EntityType.CRYPTO, 'aliases': []},

        # Arbitrum
        'arbitrum': {'display': 'Arbitrum', 'type': EntityType.CRYPTO, 'aliases': ['arb']},

        # Optimism
        'optimism': {'display': 'Optimism', 'type': EntityType.CRYPTO, 'aliases': ['op']},

        # Aptos
        'aptos': {'display': 'Aptos', 'type': EntityType.CRYPTO, 'aliases': ['apt']},

        # Sui
        'sui': {'display': 'Sui', 'type': EntityType.CRYPTO, 'aliases': []},

        # Toncoin
        'toncoin': {'display': 'Toncoin', 'type': EntityType.CRYPTO, 'aliases': ['ton']},
        'ton': {'display': 'Toncoin', 'type': EntityType.CRYPTO, 'aliases': []},
    }

    # Stablecoins
    STABLECOIN_ENTITIES = {
        'tether': {'display': 'Tether USDT', 'type': EntityType.STABLECOIN, 'aliases': ['usdt']},
        'usdt': {'display': 'Tether USDT', 'type': EntityType.STABLECOIN, 'aliases': []},
        'usdc': {'display': 'USD Coin', 'type': EntityType.STABLECOIN, 'aliases': ['usd coin']},
        'dai': {'display': 'DAI', 'type': EntityType.STABLECOIN, 'aliases': []},
        'busd': {'display': 'Binance USD', 'type': EntityType.STABLECOIN, 'aliases': []},
    }

    # Exchanges
    EXCHANGE_ENTITIES = {
        'binance': {'display': 'Binance', 'type': EntityType.EXCHANGE},
        'coinbase': {'display': 'Coinbase', 'type': EntityType.EXCHANGE},
        'kraken': {'display': 'Kraken', 'type': EntityType.EXCHANGE},
        'bybit': {'display': 'Bybit', 'type': EntityType.EXCHANGE},
        'okx': {'display': 'OKX', 'type': EntityType.EXCHANGE},
        'kucoin': {'display': 'KuCoin', 'type': EntityType.EXCHANGE},
        'huobi': {'display': 'Huobi', 'type': EntityType.EXCHANGE},
        'bitfinex': {'display': 'Bitfinex', 'type': EntityType.EXCHANGE},
        'gemini': {'display': 'Gemini', 'type': EntityType.EXCHANGE},
        'bitstamp': {'display': 'Bitstamp', 'type': EntityType.EXCHANGE},
        'mercado bitcoin': {'display': 'Mercado Bitcoin', 'type': EntityType.EXCHANGE},
        'foxbit': {'display': 'Foxbit', 'type': EntityType.EXCHANGE},
        'novadax': {'display': 'NovaDAX', 'type': EntityType.EXCHANGE},
        'crypto.com': {'display': 'Crypto.com', 'type': EntityType.EXCHANGE},
    }

    # Bancos e Instituições Financeiras
    BANK_ENTITIES = {
        'jpmorgan': {'display': 'JPMorgan', 'type': EntityType.BANK},
        'jp morgan': {'display': 'JPMorgan', 'type': EntityType.BANK},
        'goldman sachs': {'display': 'Goldman Sachs', 'type': EntityType.BANK},
        'morgan stanley': {'display': 'Morgan Stanley', 'type': EntityType.BANK},
        'blackrock': {'display': 'BlackRock', 'type': EntityType.BANK},
        'fidelity': {'display': 'Fidelity', 'type': EntityType.BANK},
        'vanguard': {'display': 'Vanguard', 'type': EntityType.BANK},
        'grayscale': {'display': 'Grayscale', 'type': EntityType.BANK},
        'ark invest': {'display': 'ARK Invest', 'type': EntityType.BANK},
        'bank of america': {'display': 'Bank of America', 'type': EntityType.BANK},
        'citibank': {'display': 'Citibank', 'type': EntityType.BANK},
        'hsbc': {'display': 'HSBC', 'type': EntityType.BANK},
        'santander': {'display': 'Santander', 'type': EntityType.BANK},
        'itaú': {'display': 'Itaú', 'type': EntityType.BANK},
        'itau': {'display': 'Itaú', 'type': EntityType.BANK},
        'bradesco': {'display': 'Bradesco', 'type': EntityType.BANK},
        'nubank': {'display': 'Nubank', 'type': EntityType.BANK},
        'btg pactual': {'display': 'BTG Pactual', 'type': EntityType.BANK},
        'xp': {'display': 'XP Investimentos', 'type': EntityType.BANK},
    }

    # Governos e Reguladores
    GOVERNMENT_ENTITIES = {
        'sec': {'display': 'SEC', 'type': EntityType.GOVERNMENT},
        'cftc': {'display': 'CFTC', 'type': EntityType.GOVERNMENT},
        'fed': {'display': 'Federal Reserve', 'type': EntityType.GOVERNMENT},
        'federal reserve': {'display': 'Federal Reserve', 'type': EntityType.GOVERNMENT},
        'banco central': {'display': 'Banco Central', 'type': EntityType.GOVERNMENT},
        'bacen': {'display': 'Banco Central', 'type': EntityType.GOVERNMENT},
        'cvm': {'display': 'CVM', 'type': EntityType.GOVERNMENT},
        'receita federal': {'display': 'Receita Federal', 'type': EntityType.GOVERNMENT},
        'congresso': {'display': 'Congresso', 'type': EntityType.GOVERNMENT},
        'senado': {'display': 'Senado', 'type': EntityType.GOVERNMENT},
        'casa branca': {'display': 'Casa Branca', 'type': EntityType.GOVERNMENT},
        'white house': {'display': 'Casa Branca', 'type': EntityType.GOVERNMENT},
        'treasury': {'display': 'Tesouro dos EUA', 'type': EntityType.GOVERNMENT},
        'tesouro': {'display': 'Tesouro', 'type': EntityType.GOVERNMENT},
        'união europeia': {'display': 'União Europeia', 'type': EntityType.GOVERNMENT},
        'european union': {'display': 'União Europeia', 'type': EntityType.GOVERNMENT},
        'nyse': {'display': 'NYSE', 'type': EntityType.GOVERNMENT},
        'nasdaq': {'display': 'NASDAQ', 'type': EntityType.GOVERNMENT},
        'b3': {'display': 'B3', 'type': EntityType.GOVERNMENT},
    }

    # Empresas de Tecnologia
    COMPANY_ENTITIES = {
        'tesla': {'display': 'Tesla', 'type': EntityType.COMPANY},
        'microstrategy': {'display': 'MicroStrategy', 'type': EntityType.COMPANY},
        'square': {'display': 'Square', 'type': EntityType.COMPANY},
        'block': {'display': 'Block', 'type': EntityType.COMPANY},
        'paypal': {'display': 'PayPal', 'type': EntityType.COMPANY},
        'visa': {'display': 'Visa', 'type': EntityType.COMPANY},
        'mastercard': {'display': 'Mastercard', 'type': EntityType.COMPANY},
        'apple': {'display': 'Apple', 'type': EntityType.COMPANY},
        'google': {'display': 'Google', 'type': EntityType.COMPANY},
        'meta': {'display': 'Meta', 'type': EntityType.COMPANY},
        'facebook': {'display': 'Meta', 'type': EntityType.COMPANY},
        'twitter': {'display': 'X (Twitter)', 'type': EntityType.COMPANY},
        'x': {'display': 'X (Twitter)', 'type': EntityType.COMPANY},
        'microsoft': {'display': 'Microsoft', 'type': EntityType.COMPANY},
        'nvidia': {'display': 'NVIDIA', 'type': EntityType.COMPANY},
        'amazon': {'display': 'Amazon', 'type': EntityType.COMPANY},
        'stripe': {'display': 'Stripe', 'type': EntityType.COMPANY},
    }

    # Pessoas influentes
    PERSON_ENTITIES = {
        'elon musk': {'display': 'Elon Musk', 'type': EntityType.PERSON, 'role': 'ceo'},
        'michael saylor': {'display': 'Michael Saylor', 'type': EntityType.PERSON, 'role': 'ceo'},
        'vitalik buterin': {'display': 'Vitalik Buterin', 'type': EntityType.PERSON, 'role': 'developer'},
        'vitalik': {'display': 'Vitalik Buterin', 'type': EntityType.PERSON, 'role': 'developer'},
        'changpeng zhao': {'display': 'CZ (Changpeng Zhao)', 'type': EntityType.PERSON, 'role': 'ceo'},
        'cz': {'display': 'CZ (Changpeng Zhao)', 'type': EntityType.PERSON, 'role': 'ceo'},
        'satoshi nakamoto': {'display': 'Satoshi Nakamoto', 'type': EntityType.PERSON, 'role': 'developer'},
        'gary gensler': {'display': 'Gary Gensler', 'type': EntityType.PERSON, 'role': 'regulator'},
        'jerome powell': {'display': 'Jerome Powell', 'type': EntityType.PERSON, 'role': 'regulator'},
        'cathie wood': {'display': 'Cathie Wood', 'type': EntityType.PERSON, 'role': 'investor'},
        'brian armstrong': {'display': 'Brian Armstrong', 'type': EntityType.PERSON, 'role': 'ceo'},
        'sam bankman-fried': {'display': 'Sam Bankman-Fried', 'type': EntityType.PERSON, 'role': 'former_ceo'},
        'sbf': {'display': 'Sam Bankman-Fried', 'type': EntityType.PERSON, 'role': 'former_ceo'},
        'charles hoskinson': {'display': 'Charles Hoskinson', 'type': EntityType.PERSON, 'role': 'developer'},
        'jack dorsey': {'display': 'Jack Dorsey', 'type': EntityType.PERSON, 'role': 'ceo'},
    }

    # === PADRÕES DE AÇÃO/VERBO ===

    ACTION_PATTERNS = {
        # Ações de lançamento/anúncio
        'lanca': {
            'patterns': [r'\b(lança|lançou|lançando|anuncia|anunciou|revela|revelou|apresenta|apresentou|estreia|estreiou|inaugura)\b'],
            'implies_data': False,
            'sentiment_hint': 'positive'
        },
        # Ações de alerta/aviso
        'alerta': {
            'patterns': [r'\b(alerta|alertou|avisa|avisou|adverte|advertiu|cuidado|atenção)\b'],
            'implies_data': False,
            'sentiment_hint': 'negative'
        },
        # Ações de alta de preço
        'sobe': {
            'patterns': [r'\b(sobe|subiu|dispara|disparou|avança|avançou|valoriza|valorizou|cresce|cresceu|recupera|recuperou|ultrapassa|ultrapassou)\b'],
            'implies_data': True,
            'sentiment_hint': 'positive'
        },
        # Ações de queda de preço
        'cai': {
            'patterns': [r'\b(cai|caiu|despenca|despencou|recua|recuou|desvaloriza|desvalorizou|afunda|afundou|colapsa|colapsou|derrete|derreteu)\b'],
            'implies_data': True,
            'sentiment_hint': 'negative'
        },
        # Ações de enfrentamento/desafio
        'enfrenta': {
            'patterns': [r'\b(enfrenta|enfrentou|desafia|desafiou|processa|processou|investiga|investigou)\b'],
            'implies_data': False,
            'sentiment_hint': 'negative'
        },
        # Ações de aprovação/regulação positiva
        'aprova': {
            'patterns': [r'\b(aprova|aprovou|autoriza|autorizou|libera|liberou|permite|permitiu|regulamenta|regulamentou)\b'],
            'implies_data': False,
            'sentiment_hint': 'positive'
        },
        # Ações de rejeição/proibição
        'proibe': {
            'patterns': [r'\b(proíbe|proibiu|bane|baniu|bloqueia|bloqueou|suspende|suspendeu|rejeita|rejeitou)\b'],
            'implies_data': False,
            'sentiment_hint': 'negative'
        },
        # Ações de parceria/integração
        'parceria': {
            'patterns': [r'\b(parceria|parceiro|integra|integrou|colabora|colaborou|une|uniu|aliança)\b'],
            'implies_data': False,
            'sentiment_hint': 'positive'
        },
        # Ações de adoção
        'adota': {
            'patterns': [r'\b(adota|adotou|aceita|aceitou|implementa|implementou|incorpora|incorporou)\b'],
            'implies_data': False,
            'sentiment_hint': 'positive'
        },
        # Ações de hack/segurança
        'hackeia': {
            'patterns': [r'\b(hackeado|hackeada|hack|roubado|roubada|explorado|explorada|invadido|invadida|ataque|atacado)\b'],
            'implies_data': True,
            'sentiment_hint': 'negative'
        },
        # Ações de análise
        'analisa': {
            'patterns': [r'\b(analisa|analisou|prevê|previu|projeta|projetou|estima|estimou|aponta|apontou)\b'],
            'implies_data': True,
            'sentiment_hint': 'neutral'
        },
        # Ações de atualização/upgrade
        'atualiza': {
            'patterns': [r'\b(atualiza|atualizou|upgrade|fork|hard fork|soft fork|migra|migrou)\b'],
            'implies_data': False,
            'sentiment_hint': 'positive'
        },
    }

    # === PADRÕES DE DADOS NUMÉRICOS ===

    NUMERIC_PATTERNS = {
        'percentage': r'\b\d+[\.,]?\d*\s*%',
        'price_usd': r'\$\s*\d+[\.,]?\d*\s*(mil|milhão|milhões|bilhão|bilhões|trilhão|trilhões|k|m|b)?',
        'price_brl': r'r\$\s*\d+[\.,]?\d*',
        'large_number': r'\b\d+[\.,]?\d*\s*(mil|milhão|milhões|bilhão|bilhões|trilhão|trilhões)',
        'market_cap': r'\bmarket cap|capitalização|cap de mercado',
        'volume': r'\bvolume|volume de negociação',
    }

    # === PADRÕES DE TIPO DE NOTÍCIA ===

    TYPE_PATTERNS = {
        NewsType.PRICE: [
            r'\b(preço|cotação|valor|us\$|dólar|usd|brl|r\$)\b',
            r'\b(price|trading|market cap|volume|bid|ask|spot)\b',
            r'\b(alta|baixa|sobe|cai|dispara|despenca|recorde|mínima)\b',
            r'\b\d+[\.,]?\d*\s*%',
        ],
        NewsType.REGULATION: [
            r'\b(regulação|regulamentação|lei|legislação|congresso|senado)\b',
            r'\b(sec|cftc|cvm|bacen|banco central|governo|governamental)\b',
            r'\b(compliance|kyc|aml|licença|autorização|proibição)\b',
            r'\b(regulation|regulatory|government|congress|senate|bill)\b',
        ],
        NewsType.TECHNOLOGY: [
            r'\b(atualização|upgrade|fork|hard fork|soft fork|mainnet)\b',
            r'\b(protocolo|algoritmo|consenso|proof of|layer 2|l2)\b',
            r'\b(desenvolvimento|desenvolvedor|código|github|release)\b',
            r'\b(update|improvement|proposal|eip|bip|testnet)\b',
        ],
        NewsType.ADOPTION: [
            r'\b(adoção|aceita|integra|integração|pagamento)\b',
            r'\b(institucional|corporativo|mainstream)\b',
            r'\b(adoption|accepts|integration|payment|merchant)\b',
        ],
        NewsType.SECURITY: [
            r'\b(hack|hacker|ataque|vulnerabilidade|exploit|brecha)\b',
            r'\b(roubo|roubado|stolen|theft|breach|compromised)\b',
            r'\b(segurança|security|audit|auditoria)\b',
        ],
        NewsType.ANALYSIS: [
            r'\b(análise|analista|previsão|projeção|perspectiva)\b',
            r'\b(opinião|especialista|expert|fundador|ceo)\b',
            r'\b(analysis|analyst|prediction|forecast|outlook)\b',
        ],
        NewsType.PARTNERSHIP: [
            r'\b(parceria|parceiro|colaboração|acordo|aliança)\b',
            r'\b(partnership|partner|collaboration|deal|alliance)\b',
        ],
        NewsType.LAUNCH: [
            r'\b(lança|lançamento|estreia|novo|nova|inaugura)\b',
            r'\b(launch|launches|debuts|introduces|unveils)\b',
        ],
        NewsType.LEGAL: [
            r'\b(processo|ação judicial|tribunal|juiz|multa)\b',
            r'\b(lawsuit|sue|sued|court|judge|settlement|fine)\b',
        ],
        NewsType.MINING: [
            r'\b(mineração|minerador|hashrate|hash rate|mining)\b',
            r'\b(halving|halvening|block reward|difficulty)\b',
        ],
    }

    def __init__(self):
        """Inicializa o analisador compilando os padrões regex"""
        # Compilar padrões de ação
        self._action_regex = {}
        for action, config in self.ACTION_PATTERNS.items():
            self._action_regex[action] = {
                'patterns': [re.compile(p, re.IGNORECASE) for p in config['patterns']],
                'implies_data': config['implies_data'],
                'sentiment_hint': config['sentiment_hint']
            }

        # Compilar padrões numéricos
        self._numeric_regex = {
            key: re.compile(pattern, re.IGNORECASE)
            for key, pattern in self.NUMERIC_PATTERNS.items()
        }

        # Compilar padrões de tipo
        self._type_regex = {
            news_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for news_type, patterns in self.TYPE_PATTERNS.items()
        }

    def analyze(self, title: str, content: str, category: Optional[str] = None) -> NewsContext:
        """
        Analisa uma notícia e extrai seu contexto para geração editorial

        Args:
            title: Título da notícia
            content: Conteúdo/corpo da notícia
            category: Categoria pré-definida (opcional)

        Returns:
            NewsContext com todas as informações para geração de imagem editorial
        """
        full_text = f"{title} {content}".lower()
        title_lower = title.lower()

        # 1. Identificar entidade principal (prioridade no título)
        entity_type, primary_entity, primary_display = self._identify_primary_entity(title_lower, full_text)

        # 2. Identificar ação principal
        action = self._identify_action(title_lower)

        # 3. Detectar dados numéricos
        has_numeric, numeric_context = self._detect_numeric_data(title_lower, full_text)

        # 4. Determinar sentimento
        sentiment = self._determine_sentiment(title_lower, action)

        # 5. Identificar tipo de notícia
        news_type = self._identify_news_type(full_text)

        # 6. Extrair entidades secundárias
        secondary_entities = self._extract_secondary_entities(full_text, primary_entity)

        # 7. Extrair keywords
        keywords = self._extract_keywords(full_text)

        # 8. Calcular confiança
        confidence = self._calculate_confidence(
            entity_type, primary_entity, action, has_numeric
        )

        context = NewsContext(
            entity_type=entity_type,
            primary_entity=primary_entity,
            primary_entity_display=primary_display,
            sentiment=sentiment,
            news_type=news_type,
            action=action,
            has_numeric_data=has_numeric,
            numeric_context=numeric_context,
            secondary_entities=secondary_entities,
            keywords=keywords,
            confidence_score=confidence
        )

        logger.info(
            f"[ContextAnalyzer v2.0] Análise: "
            f"entity={entity_type.value}:{primary_entity}, "
            f"action={action.action}, "
            f"sentiment={sentiment.value}, "
            f"type={news_type.value}, "
            f"has_data={has_numeric}, "
            f"confidence={confidence:.2f}"
        )

        return context

    def _identify_primary_entity(
        self,
        title: str,
        full_text: str
    ) -> tuple[EntityType, Optional[str], str]:
        """
        Identifica a entidade principal da notícia
        Prioridade: título > conteúdo
        Ordem de busca: Crypto > Exchange > Bank > Government > Company > Person
        """

        def search_entities(text: str, entities: dict) -> Optional[tuple[str, dict]]:
            for key, config in entities.items():
                if key in text:
                    return key, config
                # Verificar aliases se existirem
                if 'aliases' in config:
                    for alias in config['aliases']:
                        if alias in text:
                            return key, config
            return None

        # Buscar no título primeiro (maior relevância)
        for entities_dict in [
            self.CRYPTO_ENTITIES,
            self.STABLECOIN_ENTITIES,
            self.EXCHANGE_ENTITIES,
            self.BANK_ENTITIES,
            self.GOVERNMENT_ENTITIES,
            self.COMPANY_ENTITIES,
            self.PERSON_ENTITIES,
        ]:
            result = search_entities(title, entities_dict)
            if result:
                key, config = result
                return config['type'], key, config['display']

        # Se não encontrou no título, buscar no conteúdo
        for entities_dict in [
            self.CRYPTO_ENTITIES,
            self.EXCHANGE_ENTITIES,
            self.BANK_ENTITIES,
        ]:
            result = search_entities(full_text, entities_dict)
            if result:
                key, config = result
                return config['type'], key, config['display']

        # Fallback para tema genérico
        return EntityType.THEME, None, 'cryptocurrency market'

    def _identify_action(self, title: str) -> NewsAction:
        """Identifica a ação/verbo principal no título"""

        for action, config in self._action_regex.items():
            for regex in config['patterns']:
                match = regex.search(title)
                if match:
                    return NewsAction(
                        action=action,
                        original_match=match.group(),
                        implies_data=config['implies_data']
                    )

        # Default para ação neutra
        return NewsAction(
            action='informa',
            original_match='',
            implies_data=False
        )

    def _detect_numeric_data(
        self,
        title: str,
        full_text: str
    ) -> tuple[bool, Optional[str]]:
        """Detecta presença de dados numéricos relevantes"""

        # Prioridade: título > conteúdo
        for text in [title, full_text[:500]]:
            for context_type, regex in self._numeric_regex.items():
                if regex.search(text):
                    return True, context_type

        return False, None

    def _determine_sentiment(self, title: str, action: NewsAction) -> NewsSentiment:
        """Determina o sentimento baseado no título e na ação"""

        # Palavras que indicam sentimento positivo
        positive_words = [
            'sobe', 'subiu', 'alta', 'recorde', 'ultrapassa', 'dispara',
            'aprovado', 'aprova', 'sucesso', 'lança', 'parceria',
            'adota', 'aceita', 'integra', 'bullish', 'otimismo'
        ]

        # Palavras que indicam sentimento negativo
        negative_words = [
            'cai', 'caiu', 'baixa', 'mínima', 'despenca', 'colapsa',
            'alerta', 'risco', 'hack', 'roubado', 'proíbe', 'bane',
            'processo', 'multa', 'investiga', 'bearish', 'crise', 'crash'
        ]

        # Contar ocorrências
        positive_count = sum(1 for word in positive_words if word in title)
        negative_count = sum(1 for word in negative_words if word in title)

        # Usar hint da ação como desempate
        if positive_count > negative_count:
            return NewsSentiment.POSITIVE
        elif negative_count > positive_count:
            return NewsSentiment.NEGATIVE
        elif action.action in ['sobe', 'lanca', 'aprova', 'parceria', 'adota', 'atualiza']:
            return NewsSentiment.POSITIVE
        elif action.action in ['cai', 'alerta', 'enfrenta', 'proibe', 'hackeia']:
            return NewsSentiment.NEGATIVE

        return NewsSentiment.NEUTRAL

    def _identify_news_type(self, text: str) -> NewsType:
        """Identifica o tipo principal da notícia"""
        type_scores = {}

        for news_type, regexes in self._type_regex.items():
            score = sum(1 for regex in regexes if regex.search(text))
            if score > 0:
                type_scores[news_type] = score

        if not type_scores:
            return NewsType.ANALYSIS

        return max(type_scores, key=type_scores.get)

    def _extract_secondary_entities(
        self,
        text: str,
        primary_entity: Optional[str]
    ) -> list[EntityMention]:
        """Extrai entidades secundárias mencionadas"""
        entities = []

        all_entities = {
            **self.CRYPTO_ENTITIES,
            **self.STABLECOIN_ENTITIES,
            **self.EXCHANGE_ENTITIES,
            **self.BANK_ENTITIES,
            **self.GOVERNMENT_ENTITIES,
            **self.COMPANY_ENTITIES,
        }

        for key, config in all_entities.items():
            # Pular entidade principal
            if key == primary_entity:
                continue

            if key in text:
                count = text.count(key)
                relevance = min(1.0, count * 0.25)

                entities.append(EntityMention(
                    name=key,
                    entity_type=config['type'],
                    display_name=config['display'],
                    relevance_score=relevance
                ))

        # Ordenar por relevância e limitar
        entities.sort(key=lambda x: x.relevance_score, reverse=True)
        return entities[:5]

    def _extract_keywords(self, text: str) -> list[str]:
        """Extrai palavras-chave para contexto adicional"""
        keywords = []

        keyword_patterns = [
            (r'\b(etf|spot etf|bitcoin etf)\b', 'ETF'),
            (r'\b(halving|halvening)\b', 'halving'),
            (r'\b(staking|stake)\b', 'staking'),
            (r'\b(mining|mineração)\b', 'mining'),
            (r'\b(nft|nfts)\b', 'NFT'),
            (r'\b(defi|finanças descentralizadas)\b', 'DeFi'),
            (r'\b(dao)\b', 'DAO'),
            (r'\b(layer 2|l2|rollup)\b', 'layer2'),
            (r'\b(wallet|carteira)\b', 'wallet'),
            (r'\b(airdrop)\b', 'airdrop'),
            (r'\b(smart contract|contrato inteligente)\b', 'smart_contract'),
            (r'\b(whale|baleia)\b', 'whale'),
        ]

        for pattern, keyword in keyword_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                keywords.append(keyword)

        return keywords[:5]

    def _calculate_confidence(
        self,
        entity_type: EntityType,
        primary_entity: Optional[str],
        action: NewsAction,
        has_numeric: bool
    ) -> float:
        """Calcula score de confiança da análise"""
        confidence = 0.4  # Base

        # Entidade identificada
        if primary_entity:
            confidence += 0.25

        # Tipo de entidade específico (não genérico)
        if entity_type != EntityType.THEME:
            confidence += 0.1

        # Ação específica identificada
        if action.action != 'informa':
            confidence += 0.15

        # Dados numéricos encontrados
        if has_numeric:
            confidence += 0.1

        return min(1.0, confidence)


# Singleton para uso global
news_context_analyzer = NewsContextAnalyzer()
