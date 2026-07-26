"""
Visual Elements Bank v3.2 - Contextual Editorial Photography Style + Quality Protection
Banco de elementos visuais FOTOGRÁFICOS E CONTEXTUAIS para geração de imagens editoriais

IMPORTANTE: Este módulo gera elementos visuais que CONTAM A HISTÓRIA da notícia,
não apenas mostram a entidade principal. Cada imagem deve comunicar a ação/evento
em um único olhar.

## PROTEÇÃO ANTI-WATERMARK E QUALIDADE (v3.2)

Todos os elementos visuais agora incluem implicitamente:
- Instruções para composição COMPLETA (sem elementos cortados)
- Ênfase em fotografia ORIGINAL (não reprodução de stock photos)
- Referências a "professional", "clean", "complete framing"

## REGRA CRÍTICA DE CORRESPONDÊNCIA TÍTULO-IMAGEM (v3.1)

Quando o título usa termos GENÉRICOS como "Altcoins", "Criptomoedas", "Mercado cripto":
- THEME_SUBJECTS SEMPRE retorna subjects com MÚLTIPLAS criptos
- NUNCA retorna uma cripto específica sozinha (ex: Cardano, Litecoin)
- Subjects genéricos enfatizam "MULTIPLE", "diverse", "variety"

Padrão de referência: Estilo editorial profissional ORIGINAL

Changelog v3.2:
- Atualizada documentação para refletir proteções de qualidade
- TEXT_AREAS agora incluem "complete framing" implicitamente
- Todos os subjects enfatizam "professional", "clean" composition

Changelog v3.1:
- Subjects genéricos expandidos para enfatizar MÚLTIPLAS criptos
- get_theme_subject agora aceita entity_name para contextos genéricos
- Adicionados mais subjects genéricos (diverse altcoins ecosystem, etc)

Changelog v3.0:
- Adicionado ACTION_VISUAL_ELEMENTS para representar ações visualmente
- Adicionado DUAL_ENTITY_TEMPLATES para notícias relacionais
- Adicionado BACKGROUNDS_BY_TYPE para backgrounds contextuais
- Adicionado EVENT_VISUAL_ELEMENTS para eventos específicos
- Adicionado DRAMA_LEVELS para magnitude de eventos
- Adicionado JOURNALISTIC_SCENES para storytelling visual
- Adicionado VISUAL_HIERARCHY para importância de notícias
- Melhorado sistema de composição para incluir contexto narrativo
"""

import random
from dataclasses import dataclass, field
from typing import Optional, List

from app.services.ai.news_context_analyzer import (
    EntityType,
    NewsSentiment,
    NewsType
)


@dataclass
class EditorialComposition:
    """
    Composição visual editorial completa para um prompt v3.2

    IMPORTANTE v3.2: Todos os elementos desta composição são projetados
    para gerar imagens ORIGINAIS sem watermarks ou elementos cortados.
    A proteção principal é aplicada pelo SmartPromptGenerator, mas esta
    classe fornece elementos que reforçam a qualidade.
    """
    # Estilo fotográfico base
    photography_style: str

    # Elemento visual concreto principal
    main_subject: str

    # Elemento de ação visual (NOVO)
    action_element: Optional[str] = None

    # Cena jornalística (NOVO)
    journalistic_scene: Optional[str] = None

    # Background/cenário
    background: str = ""

    # Paleta de cores
    color_palette: str = ""

    # Overlay de dados (se aplicável)
    data_overlay: Optional[str] = None

    # Visualização de percentual (NOVO)
    percentage_visual: Optional[str] = None

    # Nível de dramaticidade (NOVO)
    drama_level: str = ""

    # Estilo de iluminação
    lighting: str = ""

    # Área para texto
    text_area: str = ""

    # Hierarquia visual (NOVO)
    visual_hierarchy: str = ""

    # Composição dual-entity (NOVO)
    dual_entity_scene: Optional[str] = None

    # Elemento de evento específico (NOVO)
    event_element: Optional[str] = None


class EditorialVisualElementsBank:
    """
    Banco de elementos visuais v3.2 - Contextual Editorial Photography Style + Quality Protection

    Foco em STORYTELLING VISUAL - cada imagem deve contar a história da notícia
    em um único olhar, não apenas mostrar logos ou moedas genéricas.

    PROTEÇÃO DE QUALIDADE v3.2:
    - Todos os elementos enfatizam composição "professional" e "clean"
    - TEXT_AREAS incluem instruções de "complete framing"
    - Subjects são projetados para gerar imagens ORIGINAIS
    """

    # === ELEMENTOS VISUAIS DE AÇÃO (NOVO) ===
    # Representa visualmente o verbo/ação da notícia

    ACTION_VISUAL_ELEMENTS = {
        # Ações de queda/declínio
        'cai': [
            "with dramatic downward arrow indicator prominently displayed",
            "positioned at edge of cliff with sense of falling",
            "with cascading coins tumbling downward effect",
            "sinking below surface level metaphor",
            "with red downward trajectory visualization",
        ],
        'despenca': [
            "in freefall motion blur effect",
            "crashing through floor support level",
            "with shattered glass falling effect",
            "tumbling down steep decline visualization",
        ],

        # Ações de alta/crescimento
        'sobe': [
            "with bold upward arrow indicator prominently displayed",
            "ascending on rising staircase of coins",
            "with rocket launch trajectory behind",
            "breaking through ceiling resistance level",
            "with green upward trajectory visualization",
        ],
        'dispara': [
            "with explosive rocket launch effect",
            "breaking through multiple resistance barriers",
            "soaring upward with momentum trails",
            "piercing through clouds to new heights",
        ],

        # Ações de lançamento/anúncio
        'lanca': [
            "emerging from gift box grand unveiling",
            "in spotlight reveal on professional stage",
            "with launch countdown display backdrop",
            "breaking through wrapping paper reveal",
            "with fireworks celebration atmosphere",
        ],

        # Ações de alerta/aviso
        'alerta': [
            "with warning triangle sign prominently displayed",
            "surrounded by caution tape barriers",
            "with flashing alert beacon lights",
            "behind protective shield barrier",
        ],

        # Ações de enfrentamento/conflito
        'enfrenta': [
            "facing opposing force across dramatic divide",
            "in courtroom setting atmosphere",
            "with versus battle stance composition",
            "standing ground against incoming pressure",
        ],

        # Ações de aprovação/regulação positiva
        'aprova': [
            "with official approval stamp prominently displayed",
            "receiving green checkmark validation",
            "with celebratory gavel approval gesture",
            "under official government seal of approval",
        ],

        # Ações de proibição/rejeição
        'proibe': [
            "behind red prohibition sign barrier",
            "with crossed-out rejection symbol overlay",
            "blocked by official barrier gate",
            "with stop hand gesture indication",
        ],

        # Ações de parceria/integração
        'parceria': [
            "connected with partnership bridge element",
            "in professional handshake composition",
            "with interlocking puzzle pieces joining",
            "united under collaborative framework",
        ],

        # Ações de adoção
        'adota': [
            "being embraced by larger entity structure",
            "integrated into mainstream payment terminal",
            "welcomed into institutional portfolio display",
            "incorporated into corporate ecosystem",
        ],

        # Ações de hack/segurança
        'hackeia': [
            "with broken lock security breach indication",
            "surrounded by shattered digital barrier",
            "with visible crack in protective wall",
            # NÃO usar "under attack": é vocabulário que APIs de imagem
            # recusam/flagram, e esta opção vazava a palavra para o prompt
            # em ~27% das gerações de notícia de segurança.
            "under security incident with warning indicators",
        ],

        # Ações de análise
        'analisa': [
            "under magnifying glass examination",
            "with analytical chart overlay display",
            "in research laboratory setting",
            "with thoughtful contemplation atmosphere",
        ],

        # Ações de atualização/upgrade
        'atualiza': [
            "with upgrade arrow transformation effect",
            "evolving into enhanced version visualization",
            "with progress loading bar completion",
            "transforming with improvement glow effect",
        ],

        # Default para ações não mapeadas
        'informa': [
            "in professional news presentation setting",
            "with informational display backdrop",
        ],
    }

    # === TEMPLATES DUAL-ENTITY (NOVO) ===
    # Para notícias que envolvem duas entidades em interação

    DUAL_ENTITY_TEMPLATES = {
        'enfrenta': "{primary} logo facing {secondary} logo across dramatic divide, "
                    "tension-filled confrontation atmosphere",
        'parceria': "{primary} and {secondary} logos connected by partnership bridge, "
                    "collaborative celebration atmosphere",
        'adota': "{secondary} corporate setting embracing {primary} symbol, "
                 "institutional adoption visualization",
        'proibe': "{secondary} official barrier blocking {primary} symbol, "
                  "regulatory prohibition atmosphere",
        'processa': "{primary} in courtroom setting facing {secondary} legal action, "
                    "judicial confrontation atmosphere",
        'investe': "{secondary} institutional vault containing {primary} assets, "
                   "investment allocation visualization",
        'integra': "{secondary} platform incorporating {primary} functionality, "
                   "technical integration visualization",
        'compete': "{primary} and {secondary} in side-by-side competition stance, "
                   "market rivalry atmosphere",
        'supera': "{primary} positioned above {secondary} in hierarchy, "
                  "market dominance visualization",
    }

    # === BACKGROUNDS POR TIPO DE NOTÍCIA (NOVO) ===
    # Backgrounds contextuais baseados no tipo de notícia

    BACKGROUNDS_BY_TYPE = {
        NewsType.REGULATION: [
            "government building columns in background setting",
            "courthouse facade with institutional architecture",
            "official government chamber or hearing room",
            "regulatory agency headquarters backdrop",
            "legislative building interior with formal atmosphere",
        ],
        NewsType.TECHNOLOGY: [
            "modern data center server room environment",
            "clean tech laboratory backdrop setting",
            "developer workspace with code displays",
            "futuristic but clean technology facility",
            "software development environment hints",
        ],
        NewsType.ADOPTION: [
            "mainstream retail store payment terminal",
            "modern commercial shopping environment",
            "consumer-friendly payment counter setting",
            "mainstream business acceptance backdrop",
            "everyday commerce integration scene",
        ],
        NewsType.SECURITY: [
            "digital vault security chamber setting",
            "cybersecurity operations center backdrop",
            "secure facility with protection elements",
            "fortress-like defensive environment",
            "security monitoring station setting",
        ],
        NewsType.PRICE: [
            "professional trading floor environment",
            "financial market screens backdrop",
            "stock exchange trading atmosphere",
            "investment desk with market displays",
            "professional trading terminal setting",
        ],
        NewsType.ANALYSIS: [
            "research office analytical environment",
            "think tank discussion room setting",
            "financial analysis desk backdrop",
            "expert commentary studio setting",
            "professional research facility",
        ],
        NewsType.PARTNERSHIP: [
            "corporate boardroom meeting setting",
            "professional conference room backdrop",
            "business partnership ceremony venue",
            "collaborative workspace environment",
            "executive meeting room atmosphere",
        ],
        NewsType.LAUNCH: [
            "product launch event stage setting",
            "unveiling ceremony backdrop",
            "press conference announcement venue",
            "grand opening celebration atmosphere",
            "premiere event professional setting",
        ],
        NewsType.LEGAL: [
            "courtroom interior formal setting",
            "legal office professional backdrop",
            "judicial chamber atmosphere",
            "law firm conference room setting",
            "legal proceedings formal environment",
        ],
        NewsType.MINING: [
            "cryptocurrency mining facility interior",
            "data center with mining hardware",
            "industrial mining operation setting",
            "professional mining farm backdrop",
            "high-performance computing facility",
        ],
    }

    # === ELEMENTOS DE EVENTOS ESPECÍFICOS (NOVO) ===
    # Visualizações para eventos conhecidos do mercado cripto

    EVENT_VISUAL_ELEMENTS = {
        'halving': "Bitcoin symbol split in half with countdown timer element, "
                   "historic halving event visualization",
        'etf': "official ETF approval documentation with SEC seal, "
               "institutional trading floor celebration",
        'airdrop': "tokens falling like golden rain from above, "
                   "distribution celebration atmosphere",
        'fork': "blockchain path splitting into two distinct directions, "
                "network divergence visualization",
        'ipo': "stock market opening bell ceremony, "
               "listing celebration atmosphere",
        'mainnet': "network launch countdown with activation visualization, "
                   "mainnet deployment celebration",
        'merge': "two networks combining into unified structure, "
                 "historic merger visualization",
        'upgrade': "system transformation with progress visualization, "
                   "network upgrade deployment",
        'burn': "tokens entering ceremonial burning mechanism, "
                "deflationary event visualization",
        'unlock': "locked tokens being released from vault, "
                  "vesting unlock event visualization",
        'snapshot': "network freeze moment capture visualization, "
                    "snapshot event documentation",
        'listing': "exchange listing announcement celebration, "
                   "new trading pair availability",
    }

    # === NÍVEIS DE DRAMATICIDADE (NOVO) ===
    # Ajusta intensidade visual baseada na magnitude do evento

    DRAMA_LEVELS = {
        'extreme': {
            'description': "highly dramatic composition with maximum visual impact",
            'lighting': "intense dramatic lighting with strong contrasts",
            'motion': "explosive motion effects and energy",
            'threshold': 30,  # >= 30% change
        },
        'high': {
            'description': "dynamic impactful composition with clear visual tension",
            'lighting': "dramatic lighting with pronounced shadows",
            'motion': "visible movement and momentum indication",
            'threshold': 15,  # >= 15% change
        },
        'moderate': {
            'description': "professionally dynamic composition with subtle energy",
            'lighting': "balanced lighting with directional emphasis",
            'motion': "subtle movement suggestion",
            'threshold': 5,  # >= 5% change
        },
        'subtle': {
            'description': "clean professional composition with understated elegance",
            'lighting': "even professional lighting",
            'motion': "static professional presentation",
            'threshold': 0,  # < 5% change
        },
    }

    # === CENAS JORNALÍSTICAS (NOVO) ===
    # Templates de cenas que contam histórias em um olhar

    JOURNALISTIC_SCENES = {
        'price_surge': "trading floor celebration with {crypto} charts showing "
                       "dramatic gains on multiple screens, victorious atmosphere",
        'price_crash': "trading floor tension with {crypto} charts showing "
                       "steep decline on screens, serious concerned atmosphere",
        'regulation_positive': "{entity} receiving official approval in "
                               "governmental setting, celebratory formal atmosphere",
        'regulation_negative': "{entity} facing regulatory barrier in "
                               "official governmental hearing, tense atmosphere",
        'adoption_corporate': "{company} headquarters displaying {crypto} "
                              "acceptance signage, mainstream integration moment",
        'adoption_retail': "modern store payment terminal processing {crypto} "
                           "transaction, everyday commerce integration",
        'security_breach': "{entity} digital fortress with visible breach, "
                           "emergency response atmosphere",
        'partnership_announcement': "{entity1} and {entity2} executives in "
                                    "formal handshake, partnership ceremony",
        'technology_launch': "{entity} unveiling new technology on professional "
                             "stage, product launch atmosphere",
        'legal_action': "{entity} in formal courtroom setting, "
                        "legal proceedings atmosphere",
        'market_analysis': "financial analyst examining {crypto} data on "
                           "multiple screens, research environment",
        'institutional_investment': "{entity} vault containing {crypto} "
                                    "assets, institutional allocation",
        'mining_operation': "{crypto} mining facility with industrial "
                            "equipment, operational environment",
        'network_event': "{crypto} network visualization showing {event} "
                         "in progress, technical milestone",
    }

    # === HIERARQUIA VISUAL (NOVO) ===
    # Ajusta estilo baseado na importância da notícia

    VISUAL_HIERARCHY = {
        'breaking': {
            'style': "urgent breaking news composition with maximum impact",
            'emphasis': "bold dramatic emphasis with immediate attention grab",
            'urgency': "high contrast urgent visual treatment",
        },
        'major': {
            'style': "significant news professional impact composition",
            'emphasis': "clear professional emphasis with strong focal point",
            'urgency': "important news visual treatment",
        },
        'standard': {
            'style': "balanced professional editorial composition",
            'emphasis': "professional standard emphasis",
            'urgency': "standard news visual treatment",
        },
        'analysis': {
            'style': "thoughtful analytical contemplative composition",
            'emphasis': "subtle intellectual emphasis",
            'urgency': "measured analytical visual treatment",
        },
    }

    # === ESTILOS FOTOGRÁFICOS BASE POR TIPO DE ENTIDADE ===

    PHOTOGRAPHY_STYLES = {
        EntityType.CRYPTO: "Professional product photography of cryptocurrency",
        EntityType.STABLECOIN: "Clean product photography of stablecoin",
        EntityType.EXCHANGE: "Modern fintech corporate photography",
        EntityType.BANK: "Institutional corporate photography with professional lighting",
        EntityType.GOVERNMENT: "Government building or institutional architecture photography",
        EntityType.COMPANY: "Corporate technology product photography",
        EntityType.PERSON: "Professional corporate portrait photography",
        EntityType.DEFI: "Modern fintech interface photography with clean design",
        EntityType.NFT: "Digital art gallery photography with modern framing",
        EntityType.THEME: "Professional financial news editorial photography",
    }

    # === ELEMENTOS VISUAIS CONCRETOS POR ENTIDADE ===

    CRYPTO_SUBJECTS = {
        'bitcoin': "golden Bitcoin physical coin with orange-gold metallic finish, "
                   "centered on clean professional surface",
        'btc': "golden Bitcoin physical coin with orange-gold metallic finish, "
               "centered on clean professional surface",
        'ethereum': "purple-blue Ethereum diamond logo as 3D metallic object, "
                    "professional product shot on gradient background",
        'eth': "purple-blue Ethereum diamond logo as 3D metallic object, "
               "professional product shot on gradient background",
        'solana': "purple-teal Solana logo as modern 3D rendered object, "
                  "clean product photography style",
        'sol': "purple-teal Solana logo as modern 3D rendered object, "
               "clean product photography style",
        'xrp': "blue XRP logo as professional 3D metallic symbol, "
               "institutional product photography",
        'ripple': "blue XRP logo as professional 3D metallic symbol, "
                  "institutional product photography",
        'cardano': "blue Cardano ADA logo as geometric 3D object, "
                   "clean professional product shot",
        'ada': "blue Cardano ADA logo as geometric 3D object, "
               "clean professional product shot",
        'bnb': "golden yellow BNB logo as 3D metallic coin, "
               "professional exchange branding photography",
        'dogecoin': "golden Dogecoin with Shiba Inu emblem, "
                    "playful but professional product photography",
        'doge': "golden Dogecoin with Shiba Inu emblem, "
                "playful but professional product photography",
        'polygon': "purple Polygon MATIC logo as modern 3D geometric shape, "
                   "clean tech product photography",
        'matic': "purple Polygon MATIC logo as modern 3D geometric shape, "
                 "clean tech product photography",
        'avalanche': "red Avalanche triangle logo as bold 3D object, "
                     "dynamic product photography",
        'avax': "red Avalanche triangle logo as bold 3D object, "
                "dynamic product photography",
        'chainlink': "blue Chainlink hexagon logo as connected 3D element, "
                     "professional tech product shot",
        'link': "blue Chainlink hexagon logo as connected 3D element, "
                "professional tech product shot",
        'litecoin': "silver Litecoin physical coin with metallic finish, "
                    "professional numismatic photography",
        'ltc': "silver Litecoin physical coin with metallic finish, "
               "professional numismatic photography",
        'polkadot': "pink-white Polkadot logo as interconnected 3D spheres, "
                    "modern tech product photography",
        'dot': "pink-white Polkadot logo as interconnected 3D spheres, "
               "modern tech product photography",
        'cosmos': "purple Cosmos ATOM logo as orbital 3D structure, "
                  "space-themed product photography",
        'atom': "purple Cosmos ATOM logo as orbital 3D structure, "
                "space-themed product photography",
        'toncoin': "blue Toncoin logo as modern 3D diamond shape, "
                   "clean messenger-style product shot",
        'ton': "blue Toncoin logo as modern 3D diamond shape, "
               "clean messenger-style product shot",
        'arbitrum': "blue-orange Arbitrum logo as modern 3D symbol, "
                    "layer 2 tech product photography",
        'arb': "blue-orange Arbitrum logo as modern 3D symbol, "
               "layer 2 tech product photography",
        'optimism': "red Optimism logo as bold 3D circular element, "
                    "optimistic tech product photography",
        'op': "red Optimism logo as bold 3D circular element, "
              "optimistic tech product photography",
        'aptos': "teal-green Aptos logo as modern hexagonal 3D object, "
                 "clean Web3 product photography",
        'apt': "teal-green Aptos logo as modern hexagonal 3D object, "
               "clean Web3 product photography",
        'sui': "blue Sui water droplet logo as fluid 3D element, "
               "modern Move language tech photography",
        'near': "dark Near Protocol logo with gradient accent, "
                "sharded blockchain product photography",
    }

    STABLECOIN_SUBJECTS = {
        'usdt': "green Tether USDT logo on stable professional surface, "
                "representing stability and trust",
        'tether': "green Tether USDT logo on stable professional surface, "
                  "representing stability and trust",
        'usdc': "blue USD Coin USDC logo as clean circular element, "
                "institutional stablecoin photography",
        'dai': "yellow DAI logo as modern decentralized symbol, "
               "DeFi stablecoin product photography",
        'busd': "yellow Binance USD logo on exchange-branded surface, "
                "professional stablecoin photography",
        'frax': "blue-purple FRAX logo as algorithmic stablecoin symbol, "
                "DeFi stability visualization",
        'tusd': "TrueUSD logo as institutional stablecoin symbol, "
                "trust and transparency photography",
        'lusd': "LUSD Liquity logo as decentralized stablecoin symbol, "
                "DeFi collateral visualization",
        'pyusd': "PayPal USD logo on payment platform backdrop, "
                 "mainstream stablecoin adoption photography",
        'usdd': "USDD Tron logo as algorithmic stablecoin, "
                "decentralized stability photography",
        'gusd': "Gemini Dollar logo on regulated exchange backdrop, "
                "institutional compliant stablecoin photography",
    }

    EXCHANGE_SUBJECTS = {
        'binance': "Binance logo prominently displayed on modern trading interface backdrop, "
                   "professional fintech photography",
        'coinbase': "Coinbase logo on clean modern tech surface, "
                    "professional American exchange branding",
        'kraken': "Kraken logo on professional trading environment, "
                  "established exchange corporate photography",
        'bybit': "Bybit logo on modern derivatives trading backdrop, "
                 "professional exchange photography",
        'okx': "OKX logo on global trading platform interface, "
               "modern exchange corporate photography",
        'gemini': "Gemini logo on institutional trading surface, "
                  "regulated exchange professional photography",
        'mercado bitcoin': "Mercado Bitcoin logo on Brazilian fintech backdrop, "
                           "Latin American exchange photography",
    }

    BANK_SUBJECTS = {
        'jpmorgan': "JPMorgan Chase corporate logo on institutional banking backdrop, "
                    "Wall Street corporate photography",
        'jp morgan': "JPMorgan Chase corporate logo on institutional banking backdrop, "
                     "Wall Street corporate photography",
        'goldman sachs': "Goldman Sachs logo on premium institutional setting, "
                         "investment banking corporate photography",
        'blackrock': "BlackRock logo on asset management corporate backdrop, "
                     "institutional investment photography",
        'fidelity': "Fidelity Investments logo on professional financial setting, "
                    "institutional brokerage photography",
        'grayscale': "Grayscale logo on crypto investment trust backdrop, "
                     "institutional crypto photography",
        'morgan stanley': "Morgan Stanley logo on wealth management backdrop, "
                          "premium institutional photography",
        'nubank': "Nubank purple logo on modern Brazilian fintech backdrop, "
                  "digital banking photography",
        'itau': "Itau logo on traditional Brazilian banking backdrop, "
                "established institution photography",
        'itaú': "Itau logo on traditional Brazilian banking backdrop, "
                "established institution photography",
        'bradesco': "Bradesco logo on Brazilian banking corporate setting, "
                    "traditional bank photography",
        'btg pactual': "BTG Pactual logo on investment banking backdrop, "
                       "Brazilian institutional photography",
        'xp': "XP Investimentos logo on modern Brazilian investment backdrop, "
              "tech-forward brokerage photography",
    }

    GOVERNMENT_SUBJECTS = {
        'sec': "SEC official seal or government building facade, "
               "US regulatory institutional photography",
        'cftc': "CFTC official logo on regulatory government backdrop, "
                "US commodities regulation photography",
        'fed': "Federal Reserve building in Washington DC, "
               "central bank architectural photography",
        'federal reserve': "Federal Reserve building in Washington DC, "
                           "central bank architectural photography",
        'nyse': "New York Stock Exchange building facade with columns, "
                "Wall Street architectural photography",
        'nasdaq': "NASDAQ MarketSite in Times Square, "
                  "modern stock exchange photography",
        'banco central': "Brazilian Central Bank building or official seal, "
                         "institutional government photography",
        'cvm': "CVM Brazilian securities commission official imagery, "
               "regulatory institutional photography",
        'congresso': "Brazilian Congress building in Brasilia, "
                     "government architectural photography",
        'senado': "Senate chamber or building facade, "
                  "legislative institutional photography",
        'casa branca': "White House building exterior, "
                       "US executive branch photography",
        'white house': "White House building exterior, "
                       "US executive branch photography",
        'b3': "B3 Brazilian stock exchange building or logo, "
              "Brazilian financial market photography",
    }

    COMPANY_SUBJECTS = {
        'tesla': "Tesla logo on electric vehicle or corporate backdrop, "
                 "innovative tech company photography",
        'microstrategy': "MicroStrategy corporate logo on business intelligence backdrop, "
                         "enterprise tech photography",
        'paypal': "PayPal logo on digital payment interface, "
                  "fintech corporate photography",
        'visa': "Visa logo on global payment network backdrop, "
                "payment processing photography",
        'mastercard': "Mastercard logo on international payment backdrop, "
                      "payment network photography",
        'apple': "Apple logo on premium tech product surface, "
                 "luxury tech corporate photography",
        'google': "Google logo on modern tech campus backdrop, "
                  "big tech corporate photography",
        'meta': "Meta logo on social media platform backdrop, "
                "tech conglomerate photography",
        'microsoft': "Microsoft logo on enterprise software backdrop, "
                     "enterprise tech photography",
        'nvidia': "NVIDIA logo on AI/GPU computing backdrop, "
                  "semiconductor tech photography",
        'stripe': "Stripe logo on payment infrastructure backdrop, "
                  "fintech developer photography",
    }

    PERSON_SUBJECTS = {
        'ceo': "professional business executive in corporate setting, "
               "CEO portrait photography with confident pose",
        'developer': "tech professional in modern workspace, "
                     "developer portrait with coding environment hints",
        'regulator': "government official in institutional setting, "
                     "regulatory authority portrait photography",
        'investor': "professional investor in financial setting, "
                    "investment professional portrait photography",
        'former_ceo': "business professional in neutral corporate setting, "
                      "executive portrait photography",
    }

    THEME_SUBJECTS = {
        'defi': "interconnected DeFi protocol logos arranged cleanly, "
                "decentralized finance infographic style",
        'nft': "digital art frame or NFT marketplace interface, "
               "digital collectibles photography",
        'mining': "cryptocurrency mining hardware rack, "
                  "ASIC miners in professional data center",
        'wallet': "hardware wallet device on clean surface, "
                  "crypto security product photography",
        'staking': "staking interface visualization with clean design, "
                   "proof of stake conceptual photography",
        'etf': "ETF documentation or trading interface, "
               "exchange traded fund institutional photography",
        'halving': "Bitcoin halving countdown or mining visualization, "
                   "Bitcoin event photography",
        'layer2': "Layer 2 scaling solution logos arranged cleanly, "
                  "scaling technology conceptual photography",
        'airdrop': "token distribution interface visualization, "
                   "crypto airdrop conceptual photography",
        'market': "clean financial charts on professional monitor, "
                  "market analysis photography",

        # === SUBJECTS PARA ALTCOINS/CRIPTOMOEDAS GENÉRICAS (v3.1 MELHORADO) ===
        # CRÍTICO: Estes subjects SEMPRE mostram MÚLTIPLAS criptos, NUNCA uma específica sozinha
        # Usado quando título diz "Altcoins", "Criptomoedas", "Mercado cripto" etc.

        'altcoin': (
            "MULTIPLE diverse cryptocurrency coins displayed together (showing BTC, ETH, SOL, ADA, "
            "AVAX, DOT symbols), professional arrangement of various crypto assets, "
            "NOT single coin focus, variety of tokens representing the altcoin ecosystem, "
            "clean portfolio diversity visualization"
        ),
        'altcoins': (
            "MULTIPLE diverse cryptocurrency coins displayed together (showing BTC, ETH, SOL, ADA, "
            "AVAX, DOT, LINK symbols), professional arrangement of various crypto assets, "
            "NOT single coin focus, variety of tokens representing the altcoin ecosystem, "
            "diverse crypto market visualization, portfolio of different cryptocurrencies"
        ),
        'diverse altcoins': (
            "professional trading display showing MULTIPLE cryptocurrency symbols simultaneously "
            "(BTC, ETH, SOL, ADA, AVAX, DOT, LINK, MATIC), diverse altcoin ecosystem representation, "
            "NOT focused on single specific altcoin, variety and diversity of crypto assets, "
            "multi-coin portfolio visualization, generic crypto market overview"
        ),
        'diverse altcoins ecosystem': (
            "professional trading screens showing MULTIPLE diverse cryptocurrency symbols together "
            "(BTC, ETH, SOL, ADA, AVAX, DOT, LINK, MATIC, ATOM), rich variety of crypto assets, "
            "NOT single altcoin focus like Cardano or Litecoin alone, "
            "diverse multi-coin ecosystem visualization, professional market overview with variety"
        ),
        'tokens': (
            "MULTIPLE different token representations as professional 3D coins, "
            "diverse crypto assets without focus on single brand, "
            "variety of token symbols displayed together, portfolio diversity visualization"
        ),
        'criptomoedas': (
            "professional arrangement of MULTIPLE diverse crypto coins together, "
            "various cryptocurrency symbols (BTC, ETH, SOL, ADA, AVAX) in balanced composition, "
            "NOT single coin, market diversity photography showing crypto variety"
        ),
        'criptomoeda': (
            "professional arrangement of MULTIPLE diverse crypto coins together, "
            "various cryptocurrency symbols in balanced composition, "
            "market diversity photography showing crypto ecosystem variety"
        ),
        'crypto': (
            "clean cryptocurrency market visualization showing MULTIPLE assets, "
            "professional financial dashboard with diverse coins displayed, "
            "NOT single crypto focus, variety of cryptocurrency symbols"
        ),
        'cryptos': (
            "clean cryptocurrency market visualization showing MULTIPLE diverse assets, "
            "professional financial dashboard with various coins (BTC, ETH, SOL, etc), "
            "diverse portfolio representation, NOT single coin focus"
        ),
        'cryptocurrency market': (
            "professional trading floor displaying MULTIPLE cryptocurrency symbols simultaneously, "
            "diverse digital assets on financial screens (BTC, ETH, SOL, ADA, AVAX visible), "
            "NOT single coin focus, market overview showing variety of cryptocurrencies"
        ),
        # Subject genérico para mercado cripto
        'mercado_cripto': (
            "professional trading floor with MULTIPLE cryptocurrency displays, "
            "diverse digital assets on financial screens (BTC, ETH, SOL, ADA, AVAX, DOT), "
            "NOT single coin focus, market overview visualization showing variety"
        ),
    }

    # === BACKGROUNDS POR SENTIMENTO (mantido para fallback) ===

    BACKGROUNDS = {
        NewsSentiment.POSITIVE: [
            "clean white background with soft green gradient accent",
            "professional light gray background with subtle gold highlights",
            "modern white surface with natural lighting",
            "bright professional backdrop with optimistic tones",
        ],
        NewsSentiment.NEGATIVE: [
            "dark professional background with subtle red accent",
            "serious charcoal gray background with muted lighting",
            "professional dark backdrop with warning undertones",
            "deep navy background with serious atmosphere",
        ],
        NewsSentiment.NEUTRAL: [
            "clean professional gray background",
            "modern blue-gray gradient backdrop",
            "neutral white background with balanced lighting",
            "professional corporate blue backdrop",
        ],
    }

    # === PALETAS DE CORES EDITORIAIS ===

    COLOR_PALETTES = {
        NewsSentiment.POSITIVE: [
            "bright greens (#00D47E), golds (#FFD700), clean whites",
            "optimistic emerald (#50C878), warm amber (#FFBF00), pristine white",
            "success green (#28A745), highlight gold (#DAA520), professional white",
        ],
        NewsSentiment.NEGATIVE: [
            "warning reds (#FF4757), dark grays (#2C3E50), serious blacks",
            "alert crimson (#DC143C), charcoal (#36454F), deep navy (#191970)",
            "caution orange (#FF6B35), dark blue (#1E3A5F), muted tones",
        ],
        NewsSentiment.NEUTRAL: [
            "professional blues (#2E5BFF), cool grays (#95A5A6), clean whites",
            "corporate navy (#1C3F6E), silver (#C0C0C0), balanced tones",
            "analytical blue (#4682B4), neutral gray (#708090), professional whites",
        ],
        EntityType.CRYPTO: [
            "crypto-specific colors matching the coin identity",
        ],
        EntityType.BANK: [
            "corporate navy (#1C3F6E), institutional gold (#C9A961), pristine whites",
            "professional blue (#003366), silver accents, clean whites",
        ],
        EntityType.GOVERNMENT: [
            "official navy (#000080), government gold, marble white",
            "institutional blue (#003366), serious gray, formal tones",
        ],
        EntityType.EXCHANGE: [
            "fintech blue (#0066CC), modern teal (#008080), clean whites",
            "trading green (#00C853), professional gray, digital accents",
        ],
    }

    CRYPTO_COLORS = {
        'bitcoin': "orange-gold (#F7931A), warm amber (#FFD700), clean whites",
        'btc': "orange-gold (#F7931A), warm amber (#FFD700), clean whites",
        'ethereum': "deep purple (#627EEA), cyan (#00D4FF), violet accents",
        'eth': "deep purple (#627EEA), cyan (#00D4FF), violet accents",
        'solana': "vibrant purple (#9945FF), turquoise (#14F195), gradient tones",
        'sol': "vibrant purple (#9945FF), turquoise (#14F195), gradient tones",
        'xrp': "institutional blue (#23292F), white, professional tones",
        'ripple': "institutional blue (#23292F), white, professional tones",
        'cardano': "Cardano blue (#0033AD), clean white, geometric accents",
        'ada': "Cardano blue (#0033AD), clean white, geometric accents",
        'bnb': "Binance yellow (#F3BA2F), gold accents, professional black",
        'dogecoin': "Doge gold (#C2A633), playful yellow, friendly tones",
        'doge': "Doge gold (#C2A633), playful yellow, friendly tones",
        'polygon': "Polygon purple (#8247E5), modern violet, clean whites",
        'matic': "Polygon purple (#8247E5), modern violet, clean whites",
        'avalanche': "Avalanche red (#E84142), bold crimson, powerful whites",
        'avax': "Avalanche red (#E84142), bold crimson, powerful whites",
        'chainlink': "Chainlink blue (#375BD2), connected navy, tech whites",
        'link': "Chainlink blue (#375BD2), connected navy, tech whites",
        # Litecoin
        'litecoin': "silver-blue (#345D9D), metallic gray (#A6A9AA), professional whites",
        'ltc': "silver-blue (#345D9D), metallic gray (#A6A9AA), professional whites",
        # Polkadot
        'polkadot': "Polkadot pink (#E6007A), white dots, modern magenta accents",
        'dot': "Polkadot pink (#E6007A), white dots, modern magenta accents",
        # Cosmos
        'cosmos': "Cosmos purple (#5064FB), deep space blue (#2E3148), starfield whites",
        'atom': "Cosmos purple (#5064FB), deep space blue (#2E3148), starfield whites",
        # Toncoin
        'toncoin': "Toncoin blue (#0088CC), telegram gradient, messenger whites",
        'ton': "Toncoin blue (#0088CC), telegram gradient, messenger whites",
        # Arbitrum
        'arbitrum': "Arbitrum blue (#28A0F0), orange accent (#FF6B00), tech whites",
        'arb': "Arbitrum blue (#28A0F0), orange accent (#FF6B00), tech whites",
        # Optimism
        'optimism': "Optimism red (#FF0420), bold crimson, optimistic whites",
        'op': "Optimism red (#FF0420), bold crimson, optimistic whites",
        # Aptos
        'aptos': "Aptos teal (#06BCC1), modern gradient, Web3 whites",
        'apt': "Aptos teal (#06BCC1), modern gradient, Web3 whites",
        # Sui
        'sui': "Sui blue (#6FBCF0), water gradient, fluid whites",
        # Near
        'near': "Near black (#000000), gradient accent (#00C1DE), stark whites",
    }

    # === OVERLAYS DE DADOS ===

    DATA_OVERLAYS = {
        'price_up': "semi-transparent green candlestick chart showing upward trend, "
                    "professional trading data visualization",
        'price_down': "semi-transparent red price chart showing downward movement, "
                      "professional market decline visualization",
        'percentage': "clean percentage indicator with relevant color, "
                      "professional data point overlay",
        'volume': "trading volume bars visualization, "
                  "professional volume data overlay",
        'market_cap': "market capitalization data display, "
                      "professional market size visualization",
        'comparison': "side-by-side comparison chart, "
                      "professional comparative data overlay",
        'neutral_data': "clean analytical chart overlay, "
                        "professional neutral data visualization",
    }

    # === VISUALIZAÇÃO DE PERCENTUAIS (NOVO) ===

    PERCENTAGE_VISUALS = {
        'extreme_positive': "massive +{value}% indicator prominently displayed in bold green, "
                            "explosive gain visualization",
        'high_positive': "bold +{value}% indicator clearly visible in green, "
                         "significant gain visualization",
        'moderate_positive': "+{value}% indicator visible in soft green, "
                             "moderate gain indication",
        'slight_positive': "subtle +{value}% indicator in light green, "
                           "minor positive movement",
        'extreme_negative': "massive -{value}% indicator prominently displayed in bold red, "
                            "dramatic loss visualization",
        'high_negative': "bold -{value}% indicator clearly visible in red, "
                         "significant loss visualization",
        'moderate_negative': "-{value}% indicator visible in soft red, "
                             "moderate decline indication",
        'slight_negative': "subtle -{value}% indicator in light red, "
                           "minor negative movement",
        'neutral': "0% stable indicator in neutral gray, "
                   "stability visualization",
    }

    # === ESTILOS DE ILUMINAÇÃO EDITORIAL ===

    LIGHTING_STYLES = {
        NewsSentiment.POSITIVE: [
            "bright professional studio lighting with optimistic warmth",
            "natural daylight with golden hour warmth",
            "clean high-key lighting with soft shadows",
            "uplifting studio lighting with highlight accents",
        ],
        NewsSentiment.NEGATIVE: [
            "dramatic low-key lighting with serious shadows",
            "professional moody lighting with controlled contrast",
            "serious studio lighting with muted warmth",
            "cautionary lighting with subtle warning tones",
        ],
        NewsSentiment.NEUTRAL: [
            "balanced professional studio lighting",
            "clean neutral daylight balanced illumination",
            "professional broadcast quality lighting",
            "even studio lighting with balanced exposure",
        ],
    }

    # TEXT_AREAS v3.2: Agora incluem instruções de composição completa
    TEXT_AREAS = [
        "clear negative space on left third for headline text overlay, complete framing with nothing cropped",
        "dedicated text area on bottom third with high contrast background, all elements fully visible within frame",
        "clean left side composition allowing text placement, professional complete framing",
        "professional layout with headline space on left portion, no elements cut off at edges",
    ]

    # === PREFERÊNCIAS DE ENTIDADE POR AÇÃO ===
    # Define quais tipos de entidade são mais relevantes para cada ação

    ACTION_ENTITY_PREFERENCES = {
        'enfrenta': [EntityType.GOVERNMENT, EntityType.COMPANY],
        'parceria': [EntityType.COMPANY, EntityType.EXCHANGE, EntityType.BANK],
        'adota': [EntityType.COMPANY, EntityType.BANK],
        'processa': [EntityType.GOVERNMENT, EntityType.COMPANY],
        'investe': [EntityType.BANK, EntityType.COMPANY],
        'integra': [EntityType.COMPANY, EntityType.EXCHANGE],
        'compete': [EntityType.CRYPTO, EntityType.EXCHANGE],
        'supera': [EntityType.CRYPTO],
        'proibe': [EntityType.GOVERNMENT],
        'aprova': [EntityType.GOVERNMENT],
    }

    # === MÉTODOS DE COMPOSIÇÃO ===

    def get_action_element(self, action: str) -> Optional[str]:
        """Retorna elemento visual de ação apropriado (NOVO)"""
        action_lower = action.lower()
        if action_lower in self.ACTION_VISUAL_ELEMENTS:
            return random.choice(self.ACTION_VISUAL_ELEMENTS[action_lower])
        return None

    def get_best_secondary_entity(
        self,
        secondary_entities: List,
        action: str
    ) -> Optional[str]:
        """
        Retorna a entidade secundária mais relevante para o contexto da ação.

        Args:
            secondary_entities: Lista de EntityMention
            action: Ação principal da notícia

        Returns:
            Display name da entidade mais relevante ou None
        """
        if not secondary_entities:
            return None

        action_lower = action.lower()
        preferred_types = self.ACTION_ENTITY_PREFERENCES.get(action_lower, [])

        # Buscar entidade do tipo preferido
        if preferred_types:
            for entity_type in preferred_types:
                for entity in secondary_entities:
                    if entity.entity_type == entity_type:
                        return entity.display_name

        # Fallback para primeira entidade (maior relevância)
        return secondary_entities[0].display_name

    def get_dual_entity_scene(
        self,
        primary: str,
        secondary: str,
        action: str
    ) -> Optional[str]:
        """Retorna cena com duas entidades em interação (NOVO)"""
        action_lower = action.lower()
        if action_lower in self.DUAL_ENTITY_TEMPLATES:
            template = self.DUAL_ENTITY_TEMPLATES[action_lower]
            return template.format(primary=primary, secondary=secondary)
        return None

    def get_background_by_type(
        self,
        news_type: NewsType,
        sentiment: NewsSentiment
    ) -> str:
        """Retorna background contextual baseado no tipo de notícia (NOVO)"""
        if news_type in self.BACKGROUNDS_BY_TYPE:
            return random.choice(self.BACKGROUNDS_BY_TYPE[news_type])
        # Fallback para background por sentimento
        return random.choice(self.BACKGROUNDS.get(
            sentiment,
            self.BACKGROUNDS[NewsSentiment.NEUTRAL]
        ))

    def get_event_element(self, keywords: List[str]) -> Optional[str]:
        """Retorna elemento visual para eventos específicos (NOVO)"""
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self.EVENT_VISUAL_ELEMENTS:
                return self.EVENT_VISUAL_ELEMENTS[keyword_lower]
        return None

    def get_drama_level(
        self,
        percentage: Optional[float],
        action: str
    ) -> dict:
        """Retorna nível de dramaticidade baseado na magnitude (NOVO)"""
        # Ações que implicam alta dramaticidade
        high_drama_actions = ['dispara', 'despenca', 'colapsa', 'explode', 'hackeia']

        if action.lower() in high_drama_actions:
            return self.DRAMA_LEVELS['extreme']

        if percentage is not None:
            abs_pct = abs(percentage)
            for level_name, level_data in self.DRAMA_LEVELS.items():
                if abs_pct >= level_data['threshold']:
                    return level_data

        return self.DRAMA_LEVELS['subtle']

    def get_percentage_visual(
        self,
        percentage: float,
        sentiment: NewsSentiment
    ) -> Optional[str]:
        """Retorna visualização concreta de percentual (NOVO)"""
        if percentage is None:
            return None

        abs_pct = abs(percentage)
        is_positive = percentage >= 0

        if abs_pct >= 30:
            key = 'extreme_positive' if is_positive else 'extreme_negative'
        elif abs_pct >= 10:
            key = 'high_positive' if is_positive else 'high_negative'
        elif abs_pct >= 3:
            key = 'moderate_positive' if is_positive else 'moderate_negative'
        elif abs_pct > 0:
            key = 'slight_positive' if is_positive else 'slight_negative'
        else:
            key = 'neutral'

        template = self.PERCENTAGE_VISUALS.get(key)
        if template:
            return template.format(value=abs(int(percentage)))
        return None

    def get_journalistic_scene(
        self,
        scene_type: str,
        **kwargs
    ) -> Optional[str]:
        """Retorna template de cena jornalística (NOVO)"""
        if scene_type in self.JOURNALISTIC_SCENES:
            template = self.JOURNALISTIC_SCENES[scene_type]
            try:
                return template.format(**kwargs)
            except KeyError:
                return template
        return None

    def get_visual_hierarchy(self, importance: str) -> dict:
        """Retorna estilo de hierarquia visual (NOVO)"""
        return self.VISUAL_HIERARCHY.get(
            importance,
            self.VISUAL_HIERARCHY['standard']
        )

    def get_photography_style(self, entity_type: EntityType) -> str:
        """Retorna o estilo fotográfico base para o tipo de entidade"""
        return self.PHOTOGRAPHY_STYLES.get(
            entity_type,
            self.PHOTOGRAPHY_STYLES[EntityType.THEME]
        )

    def get_main_subject(
        self,
        entity_type: EntityType,
        entity_name: Optional[str],
        entity_display: str
    ) -> str:
        """Retorna o elemento visual concreto principal"""
        if entity_name:
            entity_key = entity_name.lower()

            if entity_type == EntityType.CRYPTO:
                if entity_key in self.CRYPTO_SUBJECTS:
                    return self.CRYPTO_SUBJECTS[entity_key]
            elif entity_type == EntityType.STABLECOIN:
                if entity_key in self.STABLECOIN_SUBJECTS:
                    return self.STABLECOIN_SUBJECTS[entity_key]
            elif entity_type == EntityType.EXCHANGE:
                if entity_key in self.EXCHANGE_SUBJECTS:
                    return self.EXCHANGE_SUBJECTS[entity_key]
            elif entity_type == EntityType.BANK:
                if entity_key in self.BANK_SUBJECTS:
                    return self.BANK_SUBJECTS[entity_key]
            elif entity_type == EntityType.GOVERNMENT:
                if entity_key in self.GOVERNMENT_SUBJECTS:
                    return self.GOVERNMENT_SUBJECTS[entity_key]
            elif entity_type == EntityType.COMPANY:
                if entity_key in self.COMPANY_SUBJECTS:
                    return self.COMPANY_SUBJECTS[entity_key]

        fallback_templates = {
            EntityType.CRYPTO: f"{entity_display} cryptocurrency logo as professional 3D product, "
                               f"clean editorial photography",
            EntityType.STABLECOIN: f"{entity_display} stablecoin logo on stable professional surface",
            EntityType.EXCHANGE: f"{entity_display} exchange logo on modern trading backdrop",
            EntityType.BANK: f"{entity_display} corporate logo on institutional setting",
            EntityType.GOVERNMENT: f"{entity_display} official imagery or building",
            EntityType.COMPANY: f"{entity_display} corporate logo on tech backdrop",
            EntityType.PERSON: "professional business portrait in corporate setting",
            EntityType.DEFI: "DeFi protocol interface visualization with clean design",
            EntityType.NFT: "digital art or NFT marketplace interface",
            EntityType.THEME: "cryptocurrency market visualization with professional aesthetic",
        }

        return fallback_templates.get(
            entity_type,
            f"{entity_display} on clean professional backdrop"
        )

    def get_person_subject(self, role: Optional[str]) -> str:
        """Retorna descrição de subject para pessoas baseado no papel"""
        if role and role in self.PERSON_SUBJECTS:
            return self.PERSON_SUBJECTS[role]
        return self.PERSON_SUBJECTS['ceo']

    def get_theme_subject(self, keywords: list[str], entity_name: Optional[str] = None) -> str:
        """
        Retorna subject temático baseado em keywords ou entity_name

        NOVO v3.1: Prioriza entity_name para contextos genéricos como 'altcoins'
        """
        # NOVO v3.1: Primeiro verificar se entity_name é um subject genérico
        if entity_name:
            entity_lower = entity_name.lower()
            if entity_lower in self.THEME_SUBJECTS:
                return self.THEME_SUBJECTS[entity_lower]

        # Depois verificar keywords
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self.THEME_SUBJECTS:
                return self.THEME_SUBJECTS[keyword_lower]

        # Fallback para market genérico
        return self.THEME_SUBJECTS['cryptocurrency market']

    def get_background(self, sentiment: NewsSentiment) -> str:
        """Retorna background apropriado para o sentimento (fallback)"""
        backgrounds = self.BACKGROUNDS.get(
            sentiment,
            self.BACKGROUNDS[NewsSentiment.NEUTRAL]
        )
        return random.choice(backgrounds)

    def get_color_palette(
        self,
        sentiment: NewsSentiment,
        entity_type: EntityType,
        entity_name: Optional[str],
        entity_display: Optional[str] = None
    ) -> str:
        """Retorna paleta de cores apropriada com fallback inteligente"""
        if entity_type in [EntityType.CRYPTO, EntityType.STABLECOIN] and entity_name:
            entity_key = entity_name.lower()
            if entity_key in self.CRYPTO_COLORS:
                return self.CRYPTO_COLORS[entity_key]
            # Fallback inteligente: gerar paleta genérica para crypto não mapeada
            if entity_display and entity_display != 'cryptocurrency market':
                return f"{entity_display} brand colors, professional cryptocurrency palette, clean whites"

        if entity_type in self.COLOR_PALETTES:
            type_palettes = self.COLOR_PALETTES[entity_type]
            if type_palettes and random.random() < 0.6:
                return random.choice(type_palettes)

        sentiment_palettes = self.COLOR_PALETTES.get(
            sentiment,
            self.COLOR_PALETTES[NewsSentiment.NEUTRAL]
        )
        return random.choice(sentiment_palettes)

    def get_data_overlay(
        self,
        has_data: bool,
        sentiment: NewsSentiment,
        action: str,
        numeric_context: Optional[str]
    ) -> Optional[str]:
        """Retorna overlay de dados apropriado"""
        if not has_data:
            return None

        if action in ['sobe', 'aprova', 'lanca'] and sentiment == NewsSentiment.POSITIVE:
            return self.DATA_OVERLAYS['price_up']
        elif action in ['cai', 'alerta', 'hackeia'] and sentiment == NewsSentiment.NEGATIVE:
            return self.DATA_OVERLAYS['price_down']
        elif numeric_context == 'percentage':
            return self.DATA_OVERLAYS['percentage']
        elif numeric_context == 'volume':
            return self.DATA_OVERLAYS['volume']
        elif numeric_context == 'market_cap':
            return self.DATA_OVERLAYS['market_cap']

        return self.DATA_OVERLAYS['neutral_data']

    def get_lighting(self, sentiment: NewsSentiment) -> str:
        """Retorna estilo de iluminação baseado no sentimento"""
        lighting_options = self.LIGHTING_STYLES.get(
            sentiment,
            self.LIGHTING_STYLES[NewsSentiment.NEUTRAL]
        )
        return random.choice(lighting_options)

    def get_text_area(self) -> str:
        """Retorna especificação de área para texto"""
        return random.choice(self.TEXT_AREAS)

    def compose_editorial_elements(
        self,
        entity_type: EntityType,
        entity_name: Optional[str],
        entity_display: str,
        sentiment: NewsSentiment,
        action: str,
        has_numeric_data: bool,
        numeric_context: Optional[str],
        keywords: list[str],
        # Novos parâmetros opcionais
        news_type: Optional[NewsType] = None,
        secondary_entity: Optional[str] = None,
        percentage: Optional[float] = None,
        importance: str = 'standard',
    ) -> EditorialComposition:
        """
        Compõe todos os elementos visuais em uma composição editorial v3.0

        Agora inclui contexto narrativo completo para storytelling visual.
        """
        # Determinar subject principal
        # NOVO v3.1: Passar entity_name para get_theme_subject para suportar contextos genéricos
        if entity_type == EntityType.THEME:
            main_subject = self.get_theme_subject(keywords, entity_name)
        else:
            main_subject = self.get_main_subject(entity_type, entity_name, entity_display)

        # NOVO: Elemento de ação visual
        action_element = self.get_action_element(action)

        # NOVO: Composição dual-entity se houver entidade secundária
        dual_entity_scene = None
        if secondary_entity:
            dual_entity_scene = self.get_dual_entity_scene(
                entity_display, secondary_entity, action
            )

        # NOVO: Background contextual por tipo de notícia
        if news_type:
            background = self.get_background_by_type(news_type, sentiment)
        else:
            background = self.get_background(sentiment)

        # NOVO: Elemento de evento específico
        event_element = self.get_event_element(keywords)

        # NOVO: Nível de dramaticidade
        drama_data = self.get_drama_level(percentage, action)

        # NOVO: Visualização de percentual
        percentage_visual = None
        if percentage is not None:
            percentage_visual = self.get_percentage_visual(percentage, sentiment)

        # NOVO: Hierarquia visual
        hierarchy_data = self.get_visual_hierarchy(importance)

        # NOVO: Determinar cena jornalística apropriada
        journalistic_scene = None
        if news_type == NewsType.PRICE and sentiment == NewsSentiment.POSITIVE:
            journalistic_scene = self.get_journalistic_scene(
                'price_surge', crypto=entity_display
            )
        elif news_type == NewsType.PRICE and sentiment == NewsSentiment.NEGATIVE:
            journalistic_scene = self.get_journalistic_scene(
                'price_crash', crypto=entity_display
            )
        elif news_type == NewsType.REGULATION and sentiment == NewsSentiment.POSITIVE:
            journalistic_scene = self.get_journalistic_scene(
                'regulation_positive', entity=entity_display
            )
        elif news_type == NewsType.REGULATION and sentiment == NewsSentiment.NEGATIVE:
            journalistic_scene = self.get_journalistic_scene(
                'regulation_negative', entity=entity_display
            )
        elif news_type == NewsType.ADOPTION:
            journalistic_scene = self.get_journalistic_scene(
                'adoption_corporate',
                company=secondary_entity or 'major company',
                crypto=entity_display
            )
        elif news_type == NewsType.SECURITY and sentiment == NewsSentiment.NEGATIVE:
            journalistic_scene = self.get_journalistic_scene(
                'security_breach', entity=entity_display
            )
        elif news_type == NewsType.PARTNERSHIP:
            journalistic_scene = self.get_journalistic_scene(
                'partnership_announcement',
                entity1=entity_display,
                entity2=secondary_entity or 'partner company'
            )
        elif news_type == NewsType.LAUNCH:
            journalistic_scene = self.get_journalistic_scene(
                'technology_launch', entity=entity_display
            )
        elif news_type == NewsType.LEGAL:
            journalistic_scene = self.get_journalistic_scene(
                'legal_action', entity=entity_display
            )
        elif news_type == NewsType.MINING:
            journalistic_scene = self.get_journalistic_scene(
                'mining_operation', crypto=entity_display
            )
        elif news_type == NewsType.ANALYSIS:
            journalistic_scene = self.get_journalistic_scene(
                'market_analysis', crypto=entity_display
            )

        return EditorialComposition(
            photography_style=self.get_photography_style(entity_type),
            main_subject=main_subject,
            action_element=action_element,
            journalistic_scene=journalistic_scene,
            background=background,
            color_palette=self.get_color_palette(sentiment, entity_type, entity_name, entity_display),
            data_overlay=self.get_data_overlay(
                has_numeric_data, sentiment, action, numeric_context
            ),
            percentage_visual=percentage_visual,
            drama_level=drama_data['description'],
            lighting=self.get_lighting(sentiment),
            text_area=self.get_text_area(),
            visual_hierarchy=hierarchy_data['style'],
            dual_entity_scene=dual_entity_scene,
            event_element=event_element,
        )


# Singleton para uso global
editorial_visual_elements_bank = EditorialVisualElementsBank()

# Manter compatibilidade com nome antigo (deprecado)
visual_elements_bank = editorial_visual_elements_bank
