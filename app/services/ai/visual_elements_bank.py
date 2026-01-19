"""
Visual Elements Bank v2.0 - Editorial Photography Style
Banco de elementos visuais FOTOGRÁFICOS E CONCRETOS para geração de imagens editoriais

IMPORTANTE: Este módulo NÃO contém elementos abstratos como redes blockchain,
partículas digitais ou efeitos futuristas. Todos os elementos são CONCRETOS
e seguem o padrão visual dos grandes portais de notícias cripto.

Padrão de referência: CoinDesk, Cointelegraph, Bitcoin Magazine
"""

from dataclasses import dataclass
from typing import Optional

from app.services.ai.news_context_analyzer import (
    EntityType,
    NewsSentiment,
    NewsType
)


@dataclass
class EditorialComposition:
    """Composição visual editorial completa para um prompt"""
    # Estilo fotográfico base
    photography_style: str

    # Elemento visual concreto principal
    main_subject: str

    # Background/cenário
    background: str

    # Paleta de cores
    color_palette: str

    # Overlay de dados (se aplicável)
    data_overlay: Optional[str]

    # Estilo de iluminação
    lighting: str

    # Área para texto
    text_area: str


class EditorialVisualElementsBank:
    """
    Banco de elementos visuais v2.0 - Editorial Photography Style

    Todos os elementos são CONCRETOS e FOTOGRÁFICOS, não abstratos.
    Segue o padrão visual de CoinDesk, Cointelegraph e Bitcoin Magazine.
    """

    # === ESTILOS FOTOGRÁFICOS BASE POR TIPO DE ENTIDADE ===

    PHOTOGRAPHY_STYLES = {
        # Criptomoedas
        EntityType.CRYPTO: "Professional product photography of cryptocurrency",
        EntityType.STABLECOIN: "Clean product photography of stablecoin",

        # Instituições
        EntityType.EXCHANGE: "Modern fintech corporate photography",
        EntityType.BANK: "Institutional corporate photography with professional lighting",
        EntityType.GOVERNMENT: "Government building or institutional architecture photography",

        # Empresas e pessoas
        EntityType.COMPANY: "Corporate technology product photography",
        EntityType.PERSON: "Professional corporate portrait photography",

        # DeFi e NFT
        EntityType.DEFI: "Modern fintech interface photography with clean design",
        EntityType.NFT: "Digital art gallery photography with modern framing",

        # Tema genérico
        EntityType.THEME: "Professional financial news editorial photography",
    }

    # === ELEMENTOS VISUAIS CONCRETOS POR ENTIDADE ===

    # Criptomoedas - Elementos visuais concretos (NÃO abstratos)
    CRYPTO_SUBJECTS = {
        # Bitcoin
        'bitcoin': "golden Bitcoin physical coin with orange-gold metallic finish, "
                   "centered on clean professional surface",
        'btc': "golden Bitcoin physical coin with orange-gold metallic finish, "
               "centered on clean professional surface",

        # Ethereum
        'ethereum': "purple-blue Ethereum diamond logo as 3D metallic object, "
                    "professional product shot on gradient background",
        'eth': "purple-blue Ethereum diamond logo as 3D metallic object, "
               "professional product shot on gradient background",

        # Solana
        'solana': "purple-teal Solana logo as modern 3D rendered object, "
                  "clean product photography style",
        'sol': "purple-teal Solana logo as modern 3D rendered object, "
               "clean product photography style",

        # XRP
        'xrp': "blue XRP logo as professional 3D metallic symbol, "
               "institutional product photography",
        'ripple': "blue XRP logo as professional 3D metallic symbol, "
                  "institutional product photography",

        # Cardano
        'cardano': "blue Cardano ADA logo as geometric 3D object, "
                   "clean professional product shot",
        'ada': "blue Cardano ADA logo as geometric 3D object, "
               "clean professional product shot",

        # BNB
        'bnb': "golden yellow BNB logo as 3D metallic coin, "
               "professional exchange branding photography",

        # Dogecoin
        'dogecoin': "golden Dogecoin with Shiba Inu emblem, "
                    "playful but professional product photography",
        'doge': "golden Dogecoin with Shiba Inu emblem, "
                "playful but professional product photography",

        # Polygon
        'polygon': "purple Polygon MATIC logo as modern 3D geometric shape, "
                   "clean tech product photography",
        'matic': "purple Polygon MATIC logo as modern 3D geometric shape, "
                 "clean tech product photography",

        # Avalanche
        'avalanche': "red Avalanche triangle logo as bold 3D object, "
                     "dynamic product photography",
        'avax': "red Avalanche triangle logo as bold 3D object, "
                "dynamic product photography",

        # Chainlink
        'chainlink': "blue Chainlink hexagon logo as connected 3D element, "
                     "professional tech product shot",
        'link': "blue Chainlink hexagon logo as connected 3D element, "
                "professional tech product shot",

        # Litecoin
        'litecoin': "silver Litecoin physical coin with metallic finish, "
                    "professional numismatic photography",
        'ltc': "silver Litecoin physical coin with metallic finish, "
               "professional numismatic photography",

        # Polkadot
        'polkadot': "pink-white Polkadot logo as interconnected 3D spheres, "
                    "modern tech product photography",
        'dot': "pink-white Polkadot logo as interconnected 3D spheres, "
               "modern tech product photography",

        # Cosmos
        'cosmos': "purple Cosmos ATOM logo as orbital 3D structure, "
                  "space-themed product photography",
        'atom': "purple Cosmos ATOM logo as orbital 3D structure, "
                "space-themed product photography",

        # Toncoin
        'toncoin': "blue Toncoin logo as modern 3D diamond shape, "
                   "clean messenger-style product shot",
        'ton': "blue Toncoin logo as modern 3D diamond shape, "
               "clean messenger-style product shot",

        # Arbitrum
        'arbitrum': "blue-orange Arbitrum logo as modern 3D symbol, "
                    "layer 2 tech product photography",

        # Optimism
        'optimism': "red Optimism logo as bold 3D circular element, "
                    "optimistic tech product photography",
    }

    # Stablecoins
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
    }

    # Exchanges
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

    # Bancos e Instituições Financeiras
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

    # Governos e Reguladores
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

    # Empresas de Tecnologia
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

    # Pessoas - Descrições genéricas por papel
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

    # Temas genéricos
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
    }

    # === BACKGROUNDS POR SENTIMENTO ===

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
        # Por sentimento
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

        # Por tipo de entidade
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

    # Cores específicas de criptomoedas
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

    # === ÁREA PARA TEXTO (COMPOSIÇÃO) ===

    TEXT_AREAS = [
        "clear negative space on left third for headline text overlay",
        "dedicated text area on bottom third with high contrast background",
        "clean left side composition allowing text placement",
        "professional layout with headline space on left portion",
    ]

    # === MÉTODOS DE COMPOSIÇÃO ===

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

        # Buscar pelo nome da entidade
        if entity_name:
            entity_key = entity_name.lower()

            # Verificar em cada dicionário de assuntos
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

        # Fallback: gerar descrição genérica baseada no tipo
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
        return self.PERSON_SUBJECTS['ceo']  # Default

    def get_theme_subject(self, keywords: list[str]) -> str:
        """Retorna subject temático baseado em keywords"""
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self.THEME_SUBJECTS:
                return self.THEME_SUBJECTS[keyword_lower]

        # Default para mercado genérico
        return self.THEME_SUBJECTS['market']

    def get_background(self, sentiment: NewsSentiment) -> str:
        """Retorna background apropriado para o sentimento"""
        import random
        backgrounds = self.BACKGROUNDS.get(
            sentiment,
            self.BACKGROUNDS[NewsSentiment.NEUTRAL]
        )
        return random.choice(backgrounds)

    def get_color_palette(
        self,
        sentiment: NewsSentiment,
        entity_type: EntityType,
        entity_name: Optional[str]
    ) -> str:
        """Retorna paleta de cores apropriada"""
        import random

        # Para criptos, usar cores específicas
        if entity_type in [EntityType.CRYPTO, EntityType.STABLECOIN] and entity_name:
            entity_key = entity_name.lower()
            if entity_key in self.CRYPTO_COLORS:
                return self.CRYPTO_COLORS[entity_key]

        # Para outros tipos de entidade, tentar paleta específica
        if entity_type in self.COLOR_PALETTES:
            type_palettes = self.COLOR_PALETTES[entity_type]
            if type_palettes and random.random() < 0.6:
                return random.choice(type_palettes)

        # Usar paleta baseada em sentimento
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

        # Determinar tipo de overlay baseado na ação e contexto
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
        import random
        lighting_options = self.LIGHTING_STYLES.get(
            sentiment,
            self.LIGHTING_STYLES[NewsSentiment.NEUTRAL]
        )
        return random.choice(lighting_options)

    def get_text_area(self) -> str:
        """Retorna especificação de área para texto"""
        import random
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
        keywords: list[str]
    ) -> EditorialComposition:
        """
        Compõe todos os elementos visuais em uma composição editorial

        Args:
            entity_type: Tipo da entidade principal
            entity_name: Nome/chave da entidade
            entity_display: Nome para exibição
            sentiment: Sentimento da notícia
            action: Ação principal identificada
            has_numeric_data: Se há dados numéricos
            numeric_context: Tipo de dado numérico
            keywords: Palavras-chave adicionais

        Returns:
            EditorialComposition com todos os elementos selecionados
        """
        # Determinar subject principal
        if entity_type == EntityType.THEME:
            main_subject = self.get_theme_subject(keywords)
        else:
            main_subject = self.get_main_subject(entity_type, entity_name, entity_display)

        return EditorialComposition(
            photography_style=self.get_photography_style(entity_type),
            main_subject=main_subject,
            background=self.get_background(sentiment),
            color_palette=self.get_color_palette(sentiment, entity_type, entity_name),
            data_overlay=self.get_data_overlay(
                has_numeric_data, sentiment, action, numeric_context
            ),
            lighting=self.get_lighting(sentiment),
            text_area=self.get_text_area()
        )


# Singleton para uso global
editorial_visual_elements_bank = EditorialVisualElementsBank()

# Manter compatibilidade com nome antigo (deprecado)
visual_elements_bank = editorial_visual_elements_bank
