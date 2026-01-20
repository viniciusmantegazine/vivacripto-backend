"""
Smart Prompt Generator v3.0 - Contextual Editorial Photography Style
Gerador de prompts para imagens de notícias de criptomoedas com STORYTELLING VISUAL

IMPORTANTE: Este módulo gera prompts que CONTAM A HISTÓRIA da notícia em um único olhar.
Cada imagem deve comunicar imediatamente o contexto, ação e sentimento da notícia.

Padrão de referência: CoinDesk, Cointelegraph, Bitcoin Magazine

Características dos prompts gerados v3.0:
- Elementos visuais CONCRETOS com AÇÃO visual (não apenas logos estáticos)
- Composições DUAL-ENTITY para notícias relacionais
- Backgrounds CONTEXTUAIS por tipo de notícia
- Visualização de PERCENTUAIS quando relevante
- Níveis de DRAMATICIDADE baseados na magnitude
- Cenas JORNALÍSTICAS que contam histórias
- HIERARQUIA VISUAL por importância da notícia
- Prompts OTIMIZADOS e condensados

Changelog v3.0:
- Integração com novos elementos de ação visual
- Suporte a composições dual-entity
- Backgrounds por tipo de notícia
- Visualização de percentuais
- Drama levels por magnitude
- Cenas jornalísticas
- Hierarquia visual
- Safe replacements para palavras sensíveis
- Prompts condensados para melhor eficiência
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
    Gerador de prompts v3.0 - Contextual Editorial Photography Style

    Gera prompts otimizados para Gemini/DALL-E com STORYTELLING VISUAL.
    Cada imagem conta a história da notícia em um único olhar.

    Foco em:
    - Ação visual (não apenas entidades estáticas)
    - Contexto narrativo claro
    - Dramaticidade proporcional à magnitude
    - Composições jornalísticas profissionais
    """

    # === CONFIGURAÇÃO DO ESTILO EDITORIAL v3.0 ===

    # Prefixo de proibição (no início para maior peso)
    AVOID_PREFIX = (
        "NO abstract networks, NO digital particles, NO sci-fi effects, "
        "NO blockchain visualizations, NO neon cyberpunk, NO matrix code. "
    )

    # Referência de estilo condensada
    STYLE_REFERENCE = "CoinDesk/Cointelegraph editorial standard"

    # Qualidade e formato (condensado)
    QUALITY_SUFFIX = (
        "professional editorial news photography, photo-realistic, "
        "high contrast for text readability, sharp focus, "
        "no text, no watermarks, 16:9 aspect ratio"
    )

    # Palavras bloqueadas (segurança) - agora usa safe replacements
    BLOCKED_WORDS = [
        'nude', 'naked', 'sexual', 'porn', 'weapon', 'gun', 'knife',
        'drugs', 'cocaine', 'heroin', 'marijuana', 'drug',
        'murder', 'kill', 'blood', 'gore', 'torture',
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

        logger.info("SmartPromptGenerator v3.0 (Contextual Storytelling) inicializado")

    def generate_prompt(
        self,
        title: str,
        content: str,
        category: Optional[str] = None
    ) -> str:
        """
        Gera um prompt com STORYTELLING VISUAL

        Args:
            title: Título da notícia
            content: Conteúdo da notícia
            category: Categoria pré-definida (opcional)

        Returns:
            Prompt otimizado para geração de imagem editorial com contexto narrativo
        """
        try:
            # 1. Analisar contexto da notícia (v3.0 com percentage e importance)
            context = self.context_analyzer.analyze(title, content, category)
            logger.info(
                f"[PromptGen v3.0] Contexto: "
                f"entity={context.entity_type.value}:{context.primary_entity}, "
                f"sentiment={context.sentiment.value}, "
                f"action={context.action.action}, "
                f"percentage={context.extracted_percentage}, "
                f"importance={context.news_importance}"
            )

            # 2. Gerar composição visual editorial com novos parâmetros v3.0
            composition = self.elements_bank.compose_editorial_elements(
                entity_type=context.entity_type,
                entity_name=context.primary_entity,
                entity_display=context.primary_entity_display,
                sentiment=context.sentiment,
                action=context.action.action,
                has_numeric_data=context.has_numeric_data,
                numeric_context=context.numeric_context,
                keywords=context.keywords,
                # Novos parâmetros v3.0
                news_type=context.news_type,
                secondary_entity=context.secondary_entity_display,
                percentage=context.extracted_percentage,
                importance=context.news_importance,
            )

            # 3. Construir prompt editorial v3.0
            prompt = self._build_editorial_prompt_v3(context, composition)

            # 4. Aplicar safe replacements (em vez de apenas remover)
            prompt = self._apply_safe_replacements(prompt)

            # 5. Sanitizar prompt final
            prompt = self._sanitize_prompt(prompt)

            # 6. Garantir variação
            prompt = self._ensure_variation(prompt)

            logger.debug(f"[PromptGen v3.0] Prompt ({len(prompt)} chars): {prompt[:300]}...")
            return prompt

        except Exception as e:
            logger.error(f"[PromptGen v3.0] Erro ao gerar prompt: {e}")
            return self._generate_fallback_prompt(category)

    def _build_editorial_prompt_v3(
        self,
        context: NewsContext,
        composition: EditorialComposition
    ) -> str:
        """
        Constrói o prompt v3.0 com storytelling visual

        Estrutura otimizada:
        [AVOID_PREFIX] [SCENE/DUAL_ENTITY] [MAIN_SUBJECT] [ACTION_ELEMENT]
        [PERCENTAGE_VISUAL] [EVENT_ELEMENT] [BACKGROUND] [DRAMA_LEVEL]
        [LIGHTING] [COLOR_PALETTE] [HIERARCHY] [TEXT_AREA] [QUALITY]
        """
        sections = []

        # 1. AVOID_PREFIX no início (maior peso)
        sections.append(self.AVOID_PREFIX)

        # 2. Cena jornalística OU composição dual-entity (se disponível)
        if composition.dual_entity_scene:
            sections.append(composition.dual_entity_scene)
        elif composition.journalistic_scene:
            sections.append(composition.journalistic_scene)
        else:
            # Fallback para estilo fotográfico + subject
            sections.append(composition.photography_style)
            sections.append(f"featuring {composition.main_subject}")

        # 3. Elemento de ação visual (NOVO - conta a história)
        if composition.action_element:
            sections.append(composition.action_element)

        # 4. Visualização de percentual (NOVO - dados concretos)
        if composition.percentage_visual:
            sections.append(composition.percentage_visual)

        # 5. Elemento de evento específico (NOVO - halving, ETF, etc)
        if composition.event_element:
            sections.append(composition.event_element)

        # 6. Background contextual (agora por tipo de notícia)
        sections.append(f"setting: {composition.background}")

        # 7. Nível de dramaticidade (NOVO)
        if composition.drama_level:
            sections.append(composition.drama_level)

        # 8. Iluminação
        sections.append(composition.lighting)

        # 9. Paleta de cores
        sections.append(f"colors: {composition.color_palette}")

        # 10. Hierarquia visual (NOVO)
        if composition.visual_hierarchy:
            sections.append(composition.visual_hierarchy)

        # 11. Área para texto
        sections.append(composition.text_area)

        # 12. Referência de estilo e qualidade (condensados)
        sections.append(self.STYLE_REFERENCE)
        sections.append(self.QUALITY_SUFFIX)

        # Juntar seções removendo vazios
        prompt = ", ".join(s for s in sections if s)

        return prompt

    def _apply_safe_replacements(self, prompt: str) -> str:
        """Aplica substituições seguras usando o context analyzer"""
        return self.context_analyzer.apply_safe_replacements(prompt)

    def _sanitize_prompt(self, prompt: str) -> str:
        """Remove palavras bloqueadas restantes e normaliza o prompt"""
        import re

        result = prompt

        # Remover apenas palavras realmente perigosas
        for word in self.BLOCKED_WORDS:
            result = re.sub(rf'\b{word}\b', '', result, flags=re.IGNORECASE)

        # Limpar espaços e vírgulas duplicadas
        result = re.sub(r'\s+', ' ', result).strip()
        result = re.sub(r',\s*,', ',', result)
        result = re.sub(r',\s*$', '', result)

        # Garantir que começa com maiúscula
        if result:
            result = result[0].upper() + result[1:]

        return result

    def _ensure_variation(self, prompt: str) -> str:
        """Garante que o prompt é diferente dos recentes"""
        prompt_hash = self._hash_prompt(prompt)

        if prompt_hash in self._recent_prompts:
            variation_elements = [
                "with subtle depth of field effect",
                "with professional studio backdrop",
                "with clean minimalist composition",
                "with balanced exposure",
                "with soft professional shadows",
                "with centered focal point",
                "with rule of thirds composition",
                "with cinematic aspect",
                "with editorial magazine quality",
            ]
            variation = random.choice(variation_elements)
            prompt = f"{prompt}, {variation}"
            prompt_hash = self._hash_prompt(prompt)

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
                "NO abstract networks. Professional product photography of golden "
                "Bitcoin physical coin, centered on clean white surface, "
                "orange-gold color palette, professional studio lighting, "
                "CoinDesk editorial standard, high contrast for text readability, "
                "clear negative space on left third for headline, photo-realistic, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
            'ethereum': (
                "NO abstract networks. Professional product photography of purple-blue "
                "Ethereum diamond logo as 3D metallic object on gradient background, "
                "purple and cyan color palette, professional lighting, "
                "Cointelegraph editorial standard, high contrast for text readability, "
                "clear negative space for headline overlay, photo-realistic, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
            'defi': (
                "NO abstract networks. Professional fintech interface photography, "
                "clean DeFi protocol visualization on modern backdrop, "
                "teal and professional blue color palette, "
                "CoinDesk editorial standard, high contrast for text readability, "
                "clear space for headline text, photo-realistic, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
            'regulacao': (
                "NO abstract networks. Government building or institutional architecture "
                "photography, official regulatory setting with professional lighting, "
                "navy and gold institutional color palette, "
                "CoinDesk editorial standard, high contrast for text readability, "
                "clear negative space for headline, photo-realistic, "
                "no text, no watermarks, 16:9 aspect ratio"
            ),
        }

        cat_key = category.lower() if category else 'bitcoin'

        if cat_key not in category_fallbacks:
            return (
                "NO abstract networks, NO digital particles. "
                "Professional editorial photography for cryptocurrency news, "
                "clean financial market visualization with professional aesthetic, "
                "modern blue and white color palette, "
                "CoinDesk editorial standard, professional journalism photography, "
                "high contrast for text readability, "
                "clear negative space on left third for headline overlay, "
                "photo-realistic, no text, no watermarks, 16:9 aspect ratio"
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
            Dict com prompt e metadados da análise v3.0
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
                # Novos campos v3.0
                'extracted_percentage': context.extracted_percentage,
                'news_importance': context.news_importance,
                'secondary_entity': context.secondary_entity_display,
                'keywords': context.keywords,
                'confidence_score': context.confidence_score,
                'prompt_length': len(prompt),
                'prompt_version': 'v3.0-contextual-storytelling',
            }
        }


# Singleton para uso global
smart_prompt_generator = SmartPromptGenerator()
