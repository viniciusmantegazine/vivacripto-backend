"""
Smart Prompt Generator v2.0 - Editorial Photography Style
Gerador de prompts para imagens de notícias de criptomoedas no estilo EDITORIAL FOTOGRÁFICO

IMPORTANTE: Este módulo gera prompts no padrão visual de CoinDesk, Cointelegraph e
Bitcoin Magazine. NÃO gera ilustrações abstratas, redes blockchain ou efeitos futuristas.

Características dos prompts gerados:
- Elementos visuais CONCRETOS (logos, moedas, prédios, pessoas)
- Estilo FOTOGRÁFICO profissional
- Alta legibilidade para texto sobreposto
- Composições limpas com hierarquia clara
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
    EntityType,
    news_context_analyzer
)
from app.services.ai.visual_elements_bank import (
    EditorialComposition,
    EditorialVisualElementsBank,
    editorial_visual_elements_bank
)


class SmartPromptGenerator:
    """
    Gerador de prompts v2.0 - Editorial Photography Style

    Gera prompts otimizados para DALL-E 3 no estilo editorial fotográfico
    dos grandes portais de notícias de criptomoedas.

    NÃO GERA:
    - Ilustrações abstratas
    - Redes blockchain decorativas
    - Partículas e efeitos de luz
    - Composições futuristas genéricas
    """

    # === CONFIGURAÇÃO DO ESTILO EDITORIAL ===

    # Referência de estilo obrigatória
    STYLE_REFERENCE = "style reference: CoinDesk and Cointelegraph editorial standard"

    # Qualidade e formato
    QUALITY_SUFFIX = (
        "professional editorial photography for cryptocurrency news publication, "
        "high quality journalism photography, "
        "optimized for news article thumbnail, "
        "photo-realistic, NOT abstract illustration, NOT tech art, "
        "clean and professional aesthetic, "
        "high contrast ensuring excellent text readability, "
        "corporate photography quality, sharp focus on subject, "
        "no text, no watermarks, no logos overlaid, "
        "16:9 aspect ratio, 8k resolution"
    )

    # Elementos a EVITAR (lista negativa explícita)
    AVOID_ELEMENTS = (
        "avoid: abstract tech backgrounds, blockchain network visualizations, "
        "digital particles, glowing network effects, futuristic sci-fi elements, "
        "neon cyberpunk aesthetics, matrix-style code rain, "
        "generic tech patterns, floating geometric shapes"
    )

    # Palavras bloqueadas (segurança)
    BLOCKED_WORDS = [
        'hack', 'hacker', 'attack', 'steal', 'theft', 'scam', 'fraud',
        'crash', 'collapse', 'bankrupt', 'death', 'dead', 'kill', 'murder',
        'lawsuit', 'sue', 'arrest', 'prison', 'jail', 'criminal', 'crime',
        'exploit', 'vulnerability', 'breach', 'leak', 'stolen',
        'war', 'conflict', 'bomb', 'terror', 'violence', 'blood',
        'nude', 'naked', 'sexual', 'porn', 'weapon', 'gun', 'knife',
        'drugs', 'cocaine', 'heroin', 'marijuana', 'drug',
    ]

    def __init__(
        self,
        context_analyzer: Optional[NewsContextAnalyzer] = None,
        elements_bank: Optional[EditorialVisualElementsBank] = None
    ):
        """
        Inicializa o gerador de prompts editoriais

        Args:
            context_analyzer: Analisador de contexto (usa singleton se None)
            elements_bank: Banco de elementos visuais (usa singleton se None)
        """
        self.context_analyzer = context_analyzer or news_context_analyzer
        self.elements_bank = elements_bank or editorial_visual_elements_bank

        # Cache de hashes para evitar repetição
        self._recent_prompts: list[str] = []
        self._max_cache_size = 50

        logger.info("SmartPromptGenerator v2.0 (Editorial Style) inicializado")

    def generate_prompt(
        self,
        title: str,
        content: str,
        category: Optional[str] = None
    ) -> str:
        """
        Gera um prompt no estilo EDITORIAL FOTOGRÁFICO

        Args:
            title: Título da notícia
            content: Conteúdo da notícia
            category: Categoria pré-definida (opcional)

        Returns:
            Prompt otimizado para geração de imagem editorial
        """
        try:
            # 1. Analisar contexto da notícia
            context = self.context_analyzer.analyze(title, content, category)
            logger.info(
                f"[PromptGen v2.0] Contexto: "
                f"entity={context.entity_type.value}:{context.primary_entity}, "
                f"sentiment={context.sentiment.value}, "
                f"action={context.action.action}"
            )

            # 2. Gerar composição visual editorial
            composition = self.elements_bank.compose_editorial_elements(
                entity_type=context.entity_type,
                entity_name=context.primary_entity,
                entity_display=context.primary_entity_display,
                sentiment=context.sentiment,
                action=context.action.action,
                has_numeric_data=context.has_numeric_data,
                numeric_context=context.numeric_context,
                keywords=context.keywords
            )

            # 3. Construir prompt editorial
            prompt = self._build_editorial_prompt(context, composition)

            # 4. Sanitizar prompt
            prompt = self._sanitize_prompt(prompt)

            # 5. Garantir variação
            prompt = self._ensure_variation(prompt)

            logger.debug(f"[PromptGen v2.0] Prompt ({len(prompt)} chars): {prompt[:300]}...")
            return prompt

        except Exception as e:
            logger.error(f"[PromptGen v2.0] Erro ao gerar prompt: {e}")
            return self._generate_fallback_prompt(category)

    def _build_editorial_prompt(
        self,
        context: NewsContext,
        composition: EditorialComposition
    ) -> str:
        """
        Constrói o prompt no formato editorial fotográfico

        Estrutura:
        [ESTILO_FOTOGRÁFICO], featuring [ELEMENTO_CONCRETO],
        [BACKGROUND], [PALETA], [ILUMINAÇÃO], [DATA_OVERLAY],
        [QUALIDADE], [ÁREA_TEXTO], [EVITAR]
        """

        # Montar seções do prompt
        sections = []

        # 1. Estilo fotográfico base
        sections.append(composition.photography_style)

        # 2. Elemento visual concreto principal
        sections.append(f"featuring {composition.main_subject}")

        # 3. Background
        sections.append(f"background: {composition.background}")

        # 4. Paleta de cores
        sections.append(f"color palette: {composition.color_palette}")

        # 5. Iluminação
        sections.append(composition.lighting)

        # 6. Overlay de dados (se aplicável)
        if composition.data_overlay:
            sections.append(composition.data_overlay)
        else:
            sections.append("clean product focus without data overlay")

        # 7. Referência de estilo
        sections.append(self.STYLE_REFERENCE)

        # 8. Qualidade e especificações
        sections.append(self.QUALITY_SUFFIX)

        # 9. Área para texto
        sections.append(composition.text_area)

        # 10. Elementos a evitar
        sections.append(self.AVOID_ELEMENTS)

        # Juntar todas as seções
        prompt = ", ".join(sections)

        return prompt

    def _sanitize_prompt(self, prompt: str) -> str:
        """Remove palavras bloqueadas e normaliza o prompt"""
        import re

        prompt_lower = prompt.lower()

        # Remover palavras bloqueadas
        for word in self.BLOCKED_WORDS:
            # Usar regex para substituir palavra completa
            prompt_lower = re.sub(rf'\b{word}\b', '', prompt_lower)

        # Remover espaços múltiplos
        prompt_lower = re.sub(r'\s+', ' ', prompt_lower).strip()

        # Remover vírgulas duplicadas
        prompt_lower = re.sub(r',\s*,', ',', prompt_lower)

        # Garantir que começa com maiúscula
        if prompt_lower:
            prompt_lower = prompt_lower[0].upper() + prompt_lower[1:]

        return prompt_lower

    def _ensure_variation(self, prompt: str) -> str:
        """Garante que o prompt é diferente dos recentes"""

        prompt_hash = self._hash_prompt(prompt)

        # Verificar se é muito similar aos recentes
        if prompt_hash in self._recent_prompts:
            # Adicionar variação sutil que mantém estilo editorial
            variation_elements = [
                "with subtle depth of field effect",
                "with professional studio backdrop",
                "with clean minimalist composition",
                "with balanced exposure",
                "with soft professional shadows",
                "with centered focal point",
                "with rule of thirds composition",
            ]
            variation = random.choice(variation_elements)
            prompt = f"{prompt}, {variation}"
            prompt_hash = self._hash_prompt(prompt)

        # Adicionar ao cache
        self._recent_prompts.append(prompt_hash)
        if len(self._recent_prompts) > self._max_cache_size:
            self._recent_prompts.pop(0)

        return prompt

    def _hash_prompt(self, prompt: str) -> str:
        """Gera hash simplificado do prompt"""
        return hashlib.md5(prompt[:150].encode()).hexdigest()[:8]

    def _generate_fallback_prompt(self, category: Optional[str] = None) -> str:
        """Gera prompt fallback editorial seguro"""

        category_fallbacks = {
            'bitcoin': (
                "Professional product photography of golden Bitcoin physical coin, "
                "centered on clean white surface, "
                "orange-gold color palette with professional lighting, "
                "style reference: CoinDesk editorial standard, "
                "professional editorial photography for cryptocurrency news, "
                "high contrast for text readability, "
                "clear negative space on left third for headline, "
                "photo-realistic, NOT abstract illustration, "
                "avoid: abstract tech backgrounds, blockchain visualizations, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
            'ethereum': (
                "Professional product photography of purple-blue Ethereum diamond logo, "
                "as 3D metallic object on gradient background, "
                "purple and cyan color palette with professional lighting, "
                "style reference: Cointelegraph editorial standard, "
                "professional editorial photography for cryptocurrency news, "
                "high contrast for text readability, "
                "clear negative space for headline overlay, "
                "photo-realistic, NOT abstract illustration, "
                "avoid: network visualizations, particle effects, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
            'defi': (
                "Professional fintech interface photography, "
                "clean DeFi protocol visualization on modern backdrop, "
                "teal and professional blue color palette, "
                "style reference: CoinDesk editorial standard, "
                "professional editorial photography for cryptocurrency news, "
                "high contrast for text readability, "
                "clear space for headline text, "
                "photo-realistic, NOT abstract illustration, "
                "avoid: abstract blockchain networks, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
            'regulacao': (
                "Government building or institutional architecture photography, "
                "official regulatory setting with professional lighting, "
                "navy and gold institutional color palette, "
                "style reference: CoinDesk editorial standard, "
                "professional editorial photography for cryptocurrency news, "
                "high contrast for text readability, "
                "clear negative space for headline, "
                "photo-realistic, NOT abstract illustration, "
                "avoid: tech backgrounds, digital effects, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
        }

        cat_key = category.lower() if category else 'bitcoin'

        # Fallback genérico se categoria não encontrada
        if cat_key not in category_fallbacks:
            return (
                "Professional editorial photography for cryptocurrency news, "
                "clean financial market visualization with professional aesthetic, "
                "modern blue and white color palette, "
                "style reference: CoinDesk editorial standard, "
                "professional journalism photography quality, "
                "high contrast ensuring excellent text readability, "
                "clear negative space on left third for headline overlay, "
                "photo-realistic, NOT abstract illustration, NOT tech art, "
                "avoid: abstract tech backgrounds, blockchain particles, network visualizations, "
                "no text, no watermarks, 16:9 aspect ratio, 8k resolution"
            )

        return category_fallbacks[cat_key]

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
                'entity_type': context.entity_type.value,
                'primary_entity': context.primary_entity,
                'primary_entity_display': context.primary_entity_display,
                'sentiment': context.sentiment.value,
                'news_type': context.news_type.value,
                'action': context.action.action,
                'has_numeric_data': context.has_numeric_data,
                'numeric_context': context.numeric_context,
                'keywords': context.keywords,
                'confidence_score': context.confidence_score,
                'prompt_length': len(prompt),
                'prompt_version': 'v2.0-editorial',
            }
        }


# Singleton para uso global
smart_prompt_generator = SmartPromptGenerator()
