"""
Smart Prompt Generator v1.0
Gerador inteligente de prompts para imagens de notícias de criptomoedas

Este módulo combina análise de contexto com elementos visuais para criar
prompts únicos, relevantes e visualmente profissionais.
"""

import hashlib
import random
from typing import Optional

from app.core.logging import logger
from app.services.ai.news_context_analyzer import (
    NewsContext,
    NewsContextAnalyzer,
    NewsSentiment,
    NewsType,
    news_context_analyzer
)
from app.services.ai.visual_elements_bank import (
    VisualComposition,
    VisualElementsBank,
    visual_elements_bank
)


class SmartPromptGenerator:
    """
    Gerador inteligente de prompts para DALL-E 3

    Combina:
    - Análise de contexto da notícia
    - Banco de elementos visuais
    - Sistema de variação para evitar repetição
    - Otimização para geração de imagens de alta qualidade
    """

    # Prefixo base para todas as imagens
    BASE_STYLE = "Professional cryptocurrency news editorial imagery"

    # Sufixo de qualidade para todas as imagens
    QUALITY_SUFFIX = (
        "cinematic lighting, ultra high detail, professional news media quality, "
        "photorealistic rendering, editorial photography style, "
        "no text, no watermarks, no logos, no symbols, no letters, "
        "16:9 aspect ratio, 8k resolution"
    )

    # Palavras bloqueadas que podem causar rejeição ou imagens inadequadas
    BLOCKED_WORDS = [
        'hack', 'hacker', 'attack', 'steal', 'theft', 'scam', 'fraud',
        'crash', 'collapse', 'bankrupt', 'death', 'dead', 'kill', 'murder',
        'lawsuit', 'sue', 'arrest', 'prison', 'jail', 'criminal', 'crime',
        'exploit', 'vulnerability', 'breach', 'leak', 'stolen',
        'war', 'conflict', 'bomb', 'terror', 'violence', 'blood',
        'nude', 'naked', 'sexual', 'porn', 'weapon', 'gun', 'knife',
        'drugs', 'cocaine', 'heroin', 'marijuana', 'drug',
    ]

    # Templates de prompt por tipo de notícia para maior variação
    TYPE_TEMPLATES = {
        NewsType.PRICE: [
            "{style}, {central}, with dynamic market visualization showing {sentiment_visual}, "
            "{secondary}, {palette}, {mood}, {composition}, {lighting}, {background}, {quality}",

            "{style}, financial data landscape featuring {central}, "
            "market {sentiment_visual} patterns, {secondary}, "
            "{palette}, {mood}, {composition}, {lighting}, {quality}",
        ],
        NewsType.REGULATION: [
            "{style}, {central} integrated with institutional architectural elements, "
            "{secondary}, {palette}, {mood}, {composition}, {lighting}, {background}, {quality}",

            "{style}, governmental framework visualization with {central}, "
            "regulatory structure elements, {secondary}, "
            "{palette}, {mood}, {composition}, {lighting}, {quality}",
        ],
        NewsType.TECHNOLOGY: [
            "{style}, futuristic technology showcase featuring {central}, "
            "innovative digital infrastructure, {secondary}, "
            "{palette}, {mood}, {composition}, {lighting}, {background}, {quality}",

            "{style}, next-generation blockchain visualization with {central}, "
            "cutting-edge protocol elements, {secondary}, "
            "{palette}, {mood}, {composition}, {lighting}, {quality}",
        ],
        NewsType.ADOPTION: [
            "{style}, expansive growth visualization featuring {central}, "
            "mainstream integration elements, {secondary}, "
            "{palette}, {mood}, {composition}, {lighting}, {background}, {quality}",

            "{style}, connected network expansion with {central}, "
            "adoption wave patterns, {secondary}, "
            "{palette}, {mood}, {composition}, {lighting}, {quality}",
        ],
        NewsType.SECURITY: [
            "{style}, security infrastructure featuring {central}, "
            "protective elements and {sentiment_visual}, {secondary}, "
            "{palette}, {mood}, {composition}, {lighting}, {background}, {quality}",
        ],
        NewsType.ANALYSIS: [
            "{style}, analytical data visualization featuring {central}, "
            "research and insight elements, {secondary}, "
            "{palette}, {mood}, {composition}, {lighting}, {background}, {quality}",
        ],
        NewsType.PARTNERSHIP: [
            "{style}, collaborative visualization featuring {central}, "
            "synergy and connection elements, {secondary}, "
            "{palette}, {mood}, {composition}, {lighting}, {background}, {quality}",
        ],
        NewsType.LAUNCH: [
            "{style}, debut visualization featuring {central}, "
            "launch and new beginning elements, {secondary}, "
            "{palette}, {mood}, {composition}, {lighting}, {background}, {quality}",
        ],
        NewsType.LEGAL: [
            "{style}, judicial visualization featuring {central}, "
            "legal and courtroom elements, {secondary}, "
            "{palette}, {mood}, {composition}, {lighting}, {background}, {quality}",
        ],
    }

    # Visualizações de sentimento para contexto
    SENTIMENT_VISUALS = {
        NewsSentiment.BULLISH: [
            "ascending momentum",
            "upward trajectory",
            "rising energy",
            "growth patterns",
            "ascending formations",
        ],
        NewsSentiment.BEARISH: [
            "descending patterns",
            "downward flow",
            "receding energy",
            "declining formations",
            "contracting patterns",
        ],
        NewsSentiment.NEUTRAL: [
            "balanced equilibrium",
            "stable patterns",
            "steady flow",
            "analytical formations",
            "data visualization",
        ],
        NewsSentiment.WARNING: [
            "alert patterns",
            "cautionary elements",
            "protective barriers",
            "security formations",
            "warning indicators",
        ],
    }

    def __init__(
        self,
        context_analyzer: Optional[NewsContextAnalyzer] = None,
        elements_bank: Optional[VisualElementsBank] = None
    ):
        """
        Inicializa o gerador de prompts

        Args:
            context_analyzer: Analisador de contexto (usa singleton se None)
            elements_bank: Banco de elementos visuais (usa singleton se None)
        """
        self.context_analyzer = context_analyzer or news_context_analyzer
        self.elements_bank = elements_bank or visual_elements_bank

        # Cache de hashes para evitar repetição
        self._recent_prompts: list[str] = []
        self._max_cache_size = 50

    def generate_prompt(
        self,
        title: str,
        content: str,
        category: Optional[str] = None
    ) -> str:
        """
        Gera um prompt otimizado para DALL-E 3 baseado no contexto da notícia

        Args:
            title: Título da notícia
            content: Conteúdo da notícia
            category: Categoria pré-definida (opcional)

        Returns:
            Prompt otimizado para geração de imagem
        """
        try:
            # 1. Analisar contexto da notícia
            context = self.context_analyzer.analyze(title, content, category)
            logger.info(
                f"Contexto analisado para prompt: "
                f"cat={context.category}, sent={context.sentiment.value}, "
                f"type={context.news_type.value}"
            )

            # 2. Gerar composição visual
            composition = self.elements_bank.compose_visual_elements(
                category=context.category,
                sentiment=context.sentiment,
                news_type=context.news_type
            )

            # 3. Construir prompt com variação
            prompt = self._build_prompt(context, composition)

            # 4. Sanitizar prompt
            prompt = self._sanitize_prompt(prompt)

            # 5. Verificar e garantir variação
            prompt = self._ensure_variation(prompt, context)

            logger.debug(f"Prompt gerado ({len(prompt)} chars): {prompt[:200]}...")
            return prompt

        except Exception as e:
            logger.error(f"Erro ao gerar prompt inteligente: {e}")
            # Fallback para prompt genérico seguro
            return self._generate_fallback_prompt(category)

    def _build_prompt(self, context: NewsContext, composition: VisualComposition) -> str:
        """Constrói o prompt combinando contexto e composição visual"""

        # Selecionar template baseado no tipo de notícia
        templates = self.TYPE_TEMPLATES.get(
            context.news_type,
            self.TYPE_TEMPLATES[NewsType.ANALYSIS]
        )
        template = random.choice(templates)

        # Preparar elementos secundários como string
        secondary_str = ", ".join(composition.secondary_elements)

        # Selecionar visual de sentimento
        sentiment_visuals = self.SENTIMENT_VISUALS.get(
            context.sentiment,
            self.SENTIMENT_VISUALS[NewsSentiment.NEUTRAL]
        )
        sentiment_visual = random.choice(sentiment_visuals)

        # Construir prompt usando template
        prompt = template.format(
            style=self.BASE_STYLE,
            central=composition.central_element,
            secondary=secondary_str,
            palette=f"color palette: {composition.color_palette}",
            mood=f"{composition.mood} atmosphere",
            composition=composition.composition_style,
            lighting=composition.lighting,
            background=f"background: {composition.background}",
            quality=self.QUALITY_SUFFIX,
            sentiment_visual=sentiment_visual
        )

        # Adicionar contexto específico se houver crypto identificada
        if context.primary_crypto:
            crypto_identity = self.context_analyzer.get_crypto_visual_identity(
                context.primary_crypto
            )
            prompt = prompt.replace(
                composition.central_element,
                f"{composition.central_element} with {crypto_identity['color']} accents"
            )

        return prompt

    def _sanitize_prompt(self, prompt: str) -> str:
        """Remove palavras bloqueadas e sanitiza o prompt"""
        prompt_lower = prompt.lower()

        for word in self.BLOCKED_WORDS:
            # Substituir palavras bloqueadas por alternativas seguras
            prompt_lower = prompt_lower.replace(word, "")

        # Remover espaços múltiplos
        import re
        prompt_lower = re.sub(r'\s+', ' ', prompt_lower).strip()

        # Manter capitalização do original onde possível
        # Garantir que começa com maiúscula
        if prompt_lower:
            prompt_lower = prompt_lower[0].upper() + prompt_lower[1:]

        return prompt_lower

    def _ensure_variation(self, prompt: str, context: NewsContext) -> str:
        """Garante que o prompt é suficientemente diferente dos recentes"""

        prompt_hash = self._hash_prompt(prompt)

        # Verificar se é muito similar aos recentes
        if prompt_hash in self._recent_prompts:
            # Adicionar variação extra
            variation_elements = [
                "with subtle lens flare",
                "with bokeh background effect",
                "with volumetric lighting",
                "with atmospheric haze",
                "with dramatic shadows",
                "with reflective surfaces",
                "with depth of field effect",
                "with crystalline textures",
            ]
            variation = random.choice(variation_elements)
            prompt = prompt.replace(
                self.QUALITY_SUFFIX,
                f"{variation}, {self.QUALITY_SUFFIX}"
            )
            prompt_hash = self._hash_prompt(prompt)

        # Adicionar ao cache
        self._recent_prompts.append(prompt_hash)
        if len(self._recent_prompts) > self._max_cache_size:
            self._recent_prompts.pop(0)

        return prompt

    def _hash_prompt(self, prompt: str) -> str:
        """Gera hash simplificado do prompt para comparação"""
        # Usar apenas primeiros 100 chars para hash
        return hashlib.md5(prompt[:100].encode()).hexdigest()[:8]

    def _generate_fallback_prompt(self, category: Optional[str] = None) -> str:
        """Gera prompt fallback seguro em caso de erro"""

        category_fallbacks = {
            'bitcoin': (
                "Professional cryptocurrency news imagery, abstract golden digital asset "
                "visualization with ascending trend patterns, warm amber and gold color palette, "
                "dynamic composition with depth, cinematic lighting, professional news media quality, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
            'ethereum': (
                "Professional cryptocurrency news imagery, abstract purple crystalline network "
                "visualization with connected nodes, violet and cyan color palette, "
                "layered composition with depth, ethereal lighting, professional news media quality, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
            'defi': (
                "Professional cryptocurrency news imagery, abstract decentralized finance "
                "visualization with flowing liquidity patterns, teal and aquamarine color palette, "
                "dynamic composition, clean lighting, professional news media quality, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
            'regulacao': (
                "Professional cryptocurrency news imagery, abstract institutional framework "
                "visualization with balanced geometric elements, navy and gold color palette, "
                "symmetrical composition, formal lighting, professional news media quality, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
        }

        cat_key = category.lower() if category else 'bitcoin'
        return category_fallbacks.get(cat_key, category_fallbacks['bitcoin'])

    def generate_prompt_with_metadata(
        self,
        title: str,
        content: str,
        category: Optional[str] = None
    ) -> dict:
        """
        Gera prompt com metadados completos para logging e debug

        Returns:
            Dict com prompt e metadados da análise
        """
        context = self.context_analyzer.analyze(title, content, category)
        prompt = self.generate_prompt(title, content, category)

        return {
            'prompt': prompt,
            'metadata': {
                'category': context.category,
                'sentiment': context.sentiment.value,
                'news_type': context.news_type.value,
                'primary_crypto': context.primary_crypto,
                'secondary_cryptos': context.secondary_cryptos,
                'entities_count': len(context.entities),
                'keywords': context.keywords,
                'confidence_score': context.confidence_score,
                'prompt_length': len(prompt),
            }
        }


# Singleton para uso global
smart_prompt_generator = SmartPromptGenerator()
