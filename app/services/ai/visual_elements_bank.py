"""
Visual Elements Bank v1.0
Banco de elementos visuais organizados por categoria, sentimento e tipo de notícia

Este módulo contém elementos visuais conceituais que são combinados
para criar prompts de imagem únicos e relevantes ao conteúdo.
"""

import random
from dataclasses import dataclass
from typing import Optional

from app.services.ai.news_context_analyzer import NewsSentiment, NewsType


@dataclass
class VisualComposition:
    """Composição visual completa para um prompt"""
    central_element: str
    secondary_elements: list[str]
    color_palette: str
    mood: str
    composition_style: str
    lighting: str
    background: str


class VisualElementsBank:
    """
    Banco de elementos visuais para geração de prompts dinâmicos

    Organiza elementos por:
    - Categoria de crypto
    - Sentimento da notícia
    - Tipo de notícia
    - Metáforas visuais
    """

    # === ELEMENTOS CENTRAIS POR CATEGORIA ===

    CATEGORY_CENTRAL_ELEMENTS = {
        'bitcoin': [
            "majestic golden Bitcoin coin floating with subtle glow",
            "abstract golden sphere radiating light energy",
            "crystalline amber structure with internal light",
            "monolithic golden monument rising from digital landscape",
            "luminous gold orb surrounded by energy particles",
        ],
        'ethereum': [
            "ethereal purple diamond crystal with internal glow",
            "crystalline violet prism refracting light",
            "abstract purple geometric structure with flowing energy",
            "luminous indigo crystal formation",
            "floating purple gemstone with aurora effects",
        ],
        'solana': [
            "sleek purple gradient wave flowing dynamically",
            "abstract speed lines in purple and cyan gradient",
            "flowing energy stream in vibrant purple tones",
            "dynamic wave pattern with neon purple accents",
        ],
        'cardano': [
            "geometric blue crystalline structure with mathematical precision",
            "abstract blue hexagonal pattern with depth",
            "structured blue architectural form with clean lines",
        ],
        'altcoins': [
            "constellation of colorful digital orbs in space",
            "abstract network of interconnected glowing nodes",
            "dynamic flow of multicolored energy streams",
            "spectrum of digital assets floating in formation",
        ],
        'defi': [
            "abstract interconnected liquid pools with flowing connections",
            "geometric layers of transparent financial structures",
            "network of glowing nodes representing decentralized protocols",
            "flowing streams of liquidity connecting abstract pools",
        ],
        'regulacao': [
            "stylized balance scales with digital elements",
            "abstract governmental architecture with clean lines",
            "geometric framework representing institutional structure",
            "marble pillars with subtle digital integration",
        ],
        'airdrop': [
            "shower of glowing particles descending gracefully",
            "abstract rain of luminous tokens",
            "cascade of digital rewards flowing downward",
            "distribution pattern of glowing energy particles",
        ],
    }

    # === ELEMENTOS SECUNDÁRIOS POR SENTIMENTO ===

    SENTIMENT_SECONDARY_ELEMENTS = {
        NewsSentiment.BULLISH: [
            "ascending trajectory lines with golden glow",
            "upward flowing energy particles",
            "rising graph formations in green tones",
            "expansive light rays spreading upward",
            "growing crystalline formations",
            "dynamic upward momentum visualization",
            "aurora borealis effect in green and gold",
            "ascending staircase of light",
        ],
        NewsSentiment.BEARISH: [
            "descending trajectory lines with subtle red glow",
            "downward flowing particles",
            "declining graph formations in muted tones",
            "contracting energy patterns",
            "dimming light sources",
            "storm clouds in the distance",
            "receding wave patterns",
            "fading geometric structures",
        ],
        NewsSentiment.NEUTRAL: [
            "balanced horizontal lines and grids",
            "stable geometric patterns",
            "equilibrium of opposing forces",
            "calm data streams flowing horizontally",
            "steady pulse of light",
            "symmetrical arrangements",
            "clean analytical visualization",
            "organized data grid patterns",
        ],
        NewsSentiment.WARNING: [
            "alert indicators with amber glow",
            "protective shield elements",
            "cautionary geometric barriers",
            "alert pulse emanating outward",
            "defensive formation patterns",
            "warning beacon effects",
            "protective barrier visualization",
            "security grid patterns",
        ],
    }

    # === PALETAS DE CORES POR SENTIMENTO E CATEGORIA ===

    COLOR_PALETTES = {
        # Por sentimento
        NewsSentiment.BULLISH: [
            "vibrant greens (#00ff88) transitioning to gold (#ffd700), with white highlights",
            "emerald (#50c878) and amber (#ffbf00) gradient, touches of bright white",
            "chartreuse (#7fff00) to warm gold (#daa520), luminous accents",
        ],
        NewsSentiment.BEARISH: [
            "deep reds (#8b0000) fading to dark purple (#2d0a3e), muted highlights",
            "crimson (#dc143c) and charcoal (#36454f) tones, subtle grey accents",
            "burgundy (#800020) transitioning to midnight blue (#191970)",
        ],
        NewsSentiment.NEUTRAL: [
            "cool blues (#0077b6) and silver (#c0c0c0), clean white accents",
            "steel blue (#4682b4) and pearl grey (#e5e4e2), subtle cyan highlights",
            "navy (#000080) to slate (#708090), professional tones",
        ],
        NewsSentiment.WARNING: [
            "amber (#ffbf00) and deep orange (#ff8c00), with red alert accents (#ff4444)",
            "warning yellow (#ffd300) fading to cautious orange (#ff6600)",
            "gold (#ffd700) with red warning pulses (#cc0000)",
        ],
        # Por categoria específica
        'bitcoin': [
            "rich gold (#ffd700) and amber (#ffbf00), with warm orange (#ff8c00) accents",
            "golden yellow (#ffc300) transitioning to bronze (#cd7f32), luminous highlights",
        ],
        'ethereum': [
            "deep purple (#7b2cbf) to cyan (#00d4ff), with violet (#8f00ff) accents",
            "indigo (#4b0082) and electric blue (#7df9ff), magenta highlights",
        ],
        'solana': [
            "vibrant purple (#9945ff) gradient to turquoise (#00c9c9), neon accents",
        ],
        'defi': [
            "teal (#008080) and aquamarine (#7fffd4), with electric blue accents",
            "mint green (#98ff98) transitioning to deep cyan (#008b8b)",
        ],
        'regulacao': [
            "navy blue (#000080) and gold (#ffd700), institutional grey accents",
            "royal blue (#4169e1) with silver (#c0c0c0) and marble white",
        ],
    }

    # === MOODS POR TIPO DE NOTÍCIA ===

    TYPE_MOODS = {
        NewsType.PRICE: [
            "dynamic and energetic with market momentum",
            "active trading atmosphere with movement",
            "pulsing with financial energy",
        ],
        NewsType.REGULATION: [
            "formal and institutional with gravitas",
            "authoritative yet balanced",
            "structured and official atmosphere",
        ],
        NewsType.TECHNOLOGY: [
            "innovative and futuristic with wonder",
            "cutting-edge technological advancement",
            "forward-looking with innovation energy",
        ],
        NewsType.ADOPTION: [
            "welcoming and expansive growth",
            "integration and acceptance atmosphere",
            "mainstream embrace with optimism",
        ],
        NewsType.SECURITY: [
            "protective and vigilant atmosphere",
            "secure fortress mentality",
            "defensive and alert mood",
        ],
        NewsType.ANALYSIS: [
            "analytical and contemplative",
            "thoughtful examination atmosphere",
            "research and insight focused",
        ],
        NewsType.PARTNERSHIP: [
            "collaborative and unified",
            "synergy and connection atmosphere",
            "harmonious integration mood",
        ],
        NewsType.LAUNCH: [
            "exciting debut energy",
            "fresh start and new beginnings",
            "inaugural and celebratory atmosphere",
        ],
        NewsType.LEGAL: [
            "serious judicial atmosphere",
            "legal deliberation mood",
            "courtroom gravitas",
        ],
    }

    # === ESTILOS DE COMPOSIÇÃO ===

    COMPOSITION_STYLES = [
        "centered focal point with radial elements expanding outward",
        "dynamic diagonal composition with energy flow from corner to corner",
        "layered depth composition with foreground, midground, and background",
        "rule of thirds with primary element offset, balancing secondary elements",
        "symmetrical balance with mirrored elements",
        "asymmetrical balance with visual weight distribution",
        "spiral composition drawing eye toward center",
        "leading lines guiding toward focal point",
    ]

    # === ESTILOS DE ILUMINAÇÃO ===

    LIGHTING_STYLES = {
        NewsSentiment.BULLISH: [
            "warm golden hour lighting with lens flare",
            "bright optimistic backlighting with glow",
            "dawn lighting suggesting new beginnings",
            "triumphant spotlight from above",
        ],
        NewsSentiment.BEARISH: [
            "dramatic low-key lighting with deep shadows",
            "stormy diffused lighting with muted tones",
            "twilight fading light atmosphere",
            "moody atmospheric lighting",
        ],
        NewsSentiment.NEUTRAL: [
            "clean studio lighting with balanced exposure",
            "soft ambient lighting with even distribution",
            "professional broadcast lighting",
            "neutral daylight balanced illumination",
        ],
        NewsSentiment.WARNING: [
            "alert beacon lighting with pulsing glow",
            "cautionary amber spotlight",
            "emergency lighting with focused intensity",
            "warning flash illumination",
        ],
    }

    # === ESTILOS DE BACKGROUND ===

    BACKGROUND_STYLES = {
        NewsSentiment.BULLISH: [
            "gradient from deep blue to vibrant sunrise colors",
            "abstract ascending energy field",
            "expansive sky suggesting limitless potential",
            "aurora borealis effect with green and gold",
        ],
        NewsSentiment.BEARISH: [
            "gradient from dark purple to charcoal",
            "abstract storm clouds in the distance",
            "deep space with distant stars",
            "moody atmospheric depth",
        ],
        NewsSentiment.NEUTRAL: [
            "clean gradient from navy to midnight blue",
            "subtle grid pattern suggesting data analysis",
            "professional dark background with subtle texture",
            "abstract data visualization field",
        ],
        NewsSentiment.WARNING: [
            "alert gradient with amber and orange tones",
            "abstract security matrix pattern",
            "protective shield texture",
            "warning grid with subtle pulse",
        ],
    }

    # === METÁFORAS VISUAIS POR CONTEXTO ===

    VISUAL_METAPHORS = {
        # Movimentos de preço
        'price_up': [
            "rocket ascending through clouds",
            "arrow breaking through ceiling",
            "phoenix rising",
            "mountain peak achievement",
        ],
        'price_down': [
            "waterfall descent",
            "autumn leaves falling",
            "sunset fading",
            "tide receding",
        ],
        # Regulação
        'regulation_positive': [
            "green light beacon",
            "open gateway",
            "bridge connecting two shores",
        ],
        'regulation_negative': [
            "barrier or wall",
            "locked vault",
            "red signal light",
        ],
        # Segurança
        'security_breach': [
            "cracked shield",
            "broken barrier",
            "storm damage",
        ],
        'security_strong': [
            "impenetrable fortress",
            "protective dome",
            "guardian shield",
        ],
        # Adoção
        'adoption': [
            "expanding ripples in water",
            "growing tree with spreading branches",
            "network of connecting nodes",
        ],
        # Tecnologia
        'technology': [
            "futuristic portal",
            "quantum circuit patterns",
            "next-generation machinery",
        ],
    }

    def get_central_element(self, category: str) -> str:
        """Retorna um elemento central aleatório para a categoria"""
        elements = self.CATEGORY_CENTRAL_ELEMENTS.get(
            category.lower(),
            self.CATEGORY_CENTRAL_ELEMENTS['altcoins']
        )
        return random.choice(elements)

    def get_secondary_elements(self, sentiment: NewsSentiment, count: int = 2) -> list[str]:
        """Retorna elementos secundários baseados no sentimento"""
        elements = self.SENTIMENT_SECONDARY_ELEMENTS.get(sentiment, [])
        if not elements:
            elements = self.SENTIMENT_SECONDARY_ELEMENTS[NewsSentiment.NEUTRAL]
        return random.sample(elements, min(count, len(elements)))

    def get_color_palette(
        self,
        sentiment: NewsSentiment,
        category: Optional[str] = None
    ) -> str:
        """Retorna uma paleta de cores apropriada"""
        # Tentar primeiro paleta específica da categoria
        if category and category.lower() in self.COLOR_PALETTES:
            category_palettes = self.COLOR_PALETTES[category.lower()]
            if random.random() < 0.6:  # 60% chance de usar paleta da categoria
                return random.choice(category_palettes)

        # Usar paleta do sentimento
        sentiment_palettes = self.COLOR_PALETTES.get(sentiment, [])
        if sentiment_palettes:
            return random.choice(sentiment_palettes)

        # Fallback para paleta neutra
        return random.choice(self.COLOR_PALETTES[NewsSentiment.NEUTRAL])

    def get_mood(self, news_type: NewsType) -> str:
        """Retorna o mood apropriado para o tipo de notícia"""
        moods = self.TYPE_MOODS.get(news_type, self.TYPE_MOODS[NewsType.ANALYSIS])
        return random.choice(moods)

    def get_composition_style(self) -> str:
        """Retorna um estilo de composição aleatório"""
        return random.choice(self.COMPOSITION_STYLES)

    def get_lighting(self, sentiment: NewsSentiment) -> str:
        """Retorna estilo de iluminação baseado no sentimento"""
        lighting = self.LIGHTING_STYLES.get(sentiment, self.LIGHTING_STYLES[NewsSentiment.NEUTRAL])
        return random.choice(lighting)

    def get_background(self, sentiment: NewsSentiment) -> str:
        """Retorna estilo de background baseado no sentimento"""
        backgrounds = self.BACKGROUND_STYLES.get(sentiment, self.BACKGROUND_STYLES[NewsSentiment.NEUTRAL])
        return random.choice(backgrounds)

    def get_visual_metaphor(self, context_key: str) -> Optional[str]:
        """Retorna uma metáfora visual para o contexto"""
        metaphors = self.VISUAL_METAPHORS.get(context_key, [])
        if metaphors:
            return random.choice(metaphors)
        return None

    def compose_visual_elements(
        self,
        category: str,
        sentiment: NewsSentiment,
        news_type: NewsType
    ) -> VisualComposition:
        """
        Compõe todos os elementos visuais em uma composição coerente

        Args:
            category: Categoria da notícia
            sentiment: Sentimento detectado
            news_type: Tipo de notícia

        Returns:
            VisualComposition com todos os elementos selecionados
        """
        return VisualComposition(
            central_element=self.get_central_element(category),
            secondary_elements=self.get_secondary_elements(sentiment, count=2),
            color_palette=self.get_color_palette(sentiment, category),
            mood=self.get_mood(news_type),
            composition_style=self.get_composition_style(),
            lighting=self.get_lighting(sentiment),
            background=self.get_background(sentiment)
        )


# Singleton para uso global
visual_elements_bank = VisualElementsBank()
