"""
Smart Prompt Generator v3.2 - Contextual Editorial Photography Style + Quality Protection
Gerador de prompts para imagens de notícias de criptomoedas com STORYTELLING VISUAL

IMPORTANTE: Este módulo gera prompts que CONTAM A HISTÓRIA da notícia em um único olhar.
Cada imagem deve comunicar imediatamente o contexto, ação e sentimento da notícia.

Padrão de referência: Estilo editorial profissional ORIGINAL (não stock photos)

## PROTEÇÃO ANTI-WATERMARK E QUALIDADE (v3.2)

TODOS os prompts gerados agora incluem proteções contra:
- ❌ Watermarks de bancos de imagens (Getty, Shutterstock, iStock, Unsplash, Pexels)
- ❌ Logos de outros sites de notícias (CoinDesk, CoinTelegraph, CoinRepo, Bitcoin Magazine)
- ❌ Símbolos de copyright ou créditos visíveis
- ❌ Elementos cortados ou incompletos nas bordas
- ❌ Texto parcialmente visível (ex: "LOBAL" ao invés de "GLOBAL")

PROTEÇÕES IMPLEMENTADAS:
- PROTECTION_PREFIX: Vai no INÍCIO do prompt para máximo peso
- QUALITY_PROTECTION_SUFFIX: Vai no FINAL do prompt como reforço
- ANTI_WATERMARK_REINFORCEMENTS: Frases de reforço usadas estrategicamente

## REGRA CRÍTICA DE CORRESPONDÊNCIA TÍTULO-IMAGEM (v3.1)

A imagem gerada DEVE corresponder EXATAMENTE ao que está no título da notícia:

1. Se título menciona cripto ESPECÍFICA (Bitcoin, Ethereum, Cardano) → usar APENAS essa cripto
2. Se título usa termo GENÉRICO (Altcoins, Criptomoedas, Mercado) → NUNCA usar cripto específica
   - Deve mostrar MÚLTIPLAS criptos ou conceito abstrato de mercado
3. Se título foca em conceito/empresa/tecnologia sem cripto → NÃO usar logos de criptos

### Exemplos:
- "Altcoins: 2026 marca virada para mercados 24/7" → MÚLTIPLAS criptos, NÃO Cardano sozinha
- "Bitcoin supera US$ 100.000" → APENAS Bitcoin
- "Criptomoedas ganham espaço na regulação" → MÚLTIPLAS criptos, conceito genérico

Características dos prompts gerados v3.2:
- Elementos visuais CONCRETOS com AÇÃO visual (não apenas logos estáticos)
- Composições DUAL-ENTITY para notícias relacionais
- Backgrounds CONTEXTUAIS por tipo de notícia
- Visualização de PERCENTUAIS quando relevante
- Níveis de DRAMATICIDADE baseados na magnitude
- Cenas JORNALÍSTICAS que contam histórias
- HIERARQUIA VISUAL por importância da notícia
- Prompts OTIMIZADOS e condensados
- INSTRUÇÃO CRÍTICA de correspondência título-imagem
- PROTEÇÃO ANTI-WATERMARK em todos os prompts (NOVO v3.2)
- PROTEÇÃO contra elementos cortados/incompletos (NOVO v3.2)

Changelog v3.2:
- Adicionado PROTECTION_PREFIX para proteção anti-watermark no início do prompt
- Adicionado QUALITY_PROTECTION_SUFFIX para proteção no final do prompt
- Adicionados ANTI_WATERMARK_REINFORCEMENTS para reforço estratégico
- Atualizado AVOID_PREFIX para incluir proibições de watermarks
- Atualizado QUALITY_SUFFIX para incluir proteção contra elementos cortados
- Atualizado STYLE_REFERENCE para enfatizar "original" (não stock photo)
- Adicionada função validar_imagem_gerada() para checklist pós-geração
- Adicionada função gerar_prompt_protegido() como wrapper de proteção
- Atualizados todos os prompts de fallback com proteções completas

Changelog v3.1:
- Adicionada instrução crítica de correspondência título-imagem
- Melhorada sanitização de contextos genéricos
- Expandidos padrões de detecção genérica

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
import re
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
    Gerador de prompts v3.2 - Contextual Editorial Photography Style + Quality Protection

    Gera prompts otimizados para Gemini/DALL-E com STORYTELLING VISUAL.
    Cada imagem conta a história da notícia em um único olhar.

    Foco em:
    - Ação visual (não apenas entidades estáticas)
    - Contexto narrativo claro
    - Dramaticidade proporcional à magnitude
    - Composições jornalísticas profissionais
    - PROTEÇÃO contra watermarks, logos indesejados e elementos cortados (v3.2)
    """

    # === CONFIGURAÇÃO DO ESTILO EDITORIAL v3.2 ===

    # === PROTEÇÃO ANTI-WATERMARK E QUALIDADE (NOVO v3.2) ===

    # Prefixo de proteção anti-watermark (vai no INÍCIO do prompt para máximo peso)
    PROTECTION_PREFIX = (
        "Generate ORIGINAL editorial photography, NOT stock photo reproduction. "
        "Create clean professional journalistic image WITHOUT watermarks or third-party branding. "
        "NO Getty Images, NO Shutterstock, NO iStock, NO Unsplash marks. "
        "NO CoinDesk logo, NO CoinTelegraph branding, NO CoinRepo watermark. "
    )

    # Sufixo de proteção de qualidade (vai no FINAL do prompt)
    QUALITY_PROTECTION_SUFFIX = (
        "CRITICAL QUALITY REQUIREMENTS: "
        "absolutely NO watermarks in corners or edges, "
        "NO stock photo service logos (Getty, Shutterstock, iStock, Unsplash, Pexels), "
        "NO news publication branding visible (CoinDesk, CoinTelegraph, CoinRepo, Bitcoin Magazine), "
        "NO copyright symbols or credits text, NO third-party logos, "
        "NO cropped or cut-off elements, NO incomplete text (if text appears it must be fully readable), "
        "complete composition with proper margins, all elements fully visible within frame, "
        "original editorial aesthetic NOT stock photo reproduction, "
        "publication-ready without licensing concerns"
    )

    # Reforços anti-watermark para usar estrategicamente
    ANTI_WATERMARK_REINFORCEMENTS = [
        "without any watermarks",
        "no stock photo marks visible",
        "clean professional image without external branding",
        "original editorial photography",
        "publication-ready quality",
        "no third-party branding marks",
        "journalism standard quality",
        "no copyright marks visible",
        "complete composition without crops",
    ]

    # Prefixo de proibição (mantido + expandido)
    AVOID_PREFIX = (
        "NO abstract networks, NO digital particles, NO sci-fi effects, "
        "NO blockchain visualizations, NO neon cyberpunk, NO matrix code, "
        "NO watermarks, NO stock photo logos, NO third-party branding. "
    )

    # Referência de estilo condensada
    STYLE_REFERENCE = "original editorial standard (NOT stock photo reproduction)"

    # Qualidade e formato (expandido v3.2)
    QUALITY_SUFFIX = (
        "professional editorial news photography, photo-realistic, "
        "high contrast for text readability, sharp focus, "
        "no text overlays, no watermarks, no logos in corners, "
        "complete framing with nothing cropped, 16:9 aspect ratio"
    )

    # NOVO v3.1: Instrução crítica para contextos genéricos
    # Adicionada ao final do prompt quando is_generic_context=True
    GENERIC_CONTEXT_INSTRUCTION = (
        "CRITICAL: This is about ALTCOINS/CRYPTOCURRENCIES in general, NOT a specific coin. "
        "MUST show MULTIPLE diverse cryptocurrency symbols (BTC, ETH, SOL, ADA, AVAX, DOT) together. "
        "DO NOT show only one specific altcoin like Cardano, Litecoin, or Polkadot alone. "
        "Show variety and diversity of the crypto ecosystem, NOT single coin focus."
    )

    # NOVO v3.1: Instrução crítica para cripto específica
    # Adicionada ao final do prompt quando é uma cripto específica mencionada
    SPECIFIC_CRYPTO_INSTRUCTION_TEMPLATE = (
        "CRITICAL: This news is specifically about {crypto_name}. "
        "Show ONLY {crypto_name}, do NOT include other cryptocurrencies. "
        "The image must clearly feature {crypto_name} visual identity."
    )

    # Palavras bloqueadas (segurança) - agora usa safe replacements
    BLOCKED_WORDS = [
        'nude', 'naked', 'sexual', 'porn', 'weapon', 'gun', 'knife',
        'drugs', 'cocaine', 'heroin', 'marijuana', 'drug',
        'murder', 'kill', 'blood', 'gore', 'torture',
    ]

    # NOVO v3.1: Nomes de criptomoedas específicas a serem removidas em contextos genéricos
    SPECIFIC_CRYPTO_NAMES = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol',
        'cardano', 'ada', 'dogecoin', 'doge', 'ripple', 'xrp',
        'litecoin', 'ltc', 'polkadot', 'dot', 'avalanche', 'avax',
        'polygon', 'matic', 'chainlink', 'link', 'cosmos', 'atom',
        'toncoin', 'ton', 'arbitrum', 'arb', 'optimism', 'op',
        'aptos', 'apt', 'sui', 'near', 'shiba', 'shib',
        'uniswap', 'uni', 'aave', 'compound', 'maker', 'mkr',
        'stellar', 'xlm', 'monero', 'xmr', 'tron', 'trx',
        'bnb', 'binance coin', 'pepe', 'bonk', 'wif', 'floki',
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

        logger.info("SmartPromptGenerator v3.2 (Contextual Storytelling + Title Matching + Quality Protection) inicializado")

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
                f"[PromptGen v3.1] Contexto: "
                f"entity={context.entity_type.value}:{context.primary_entity}, "
                f"sentiment={context.sentiment.value}, "
                f"action={context.action.action}, "
                f"percentage={context.extracted_percentage}, "
                f"importance={context.news_importance}, "
                f"is_generic={context.is_generic_context}"
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

            # 6. NOVO v3.1: Sanitizar contextos genéricos (remover moedas específicas)
            prompt = self._sanitize_generic_context(prompt, context)

            # 7. Validar e otimizar prompt (remover duplicatas, limitar tamanho)
            prompt = self._validate_and_optimize_prompt(prompt)

            # 8. Garantir variação
            prompt = self._ensure_variation(prompt)

            logger.debug(f"[PromptGen v3.1] Prompt ({len(prompt)} chars): {prompt[:300]}...")
            return prompt

        except Exception as e:
            logger.error(f"[PromptGen v3.1] Erro ao gerar prompt: {e}")
            return self._generate_fallback_prompt(category)

    def _build_editorial_prompt_v3(
        self,
        context: NewsContext,
        composition: EditorialComposition
    ) -> str:
        """
        Constrói o prompt v3.2 com storytelling visual, instrução crítica de correspondência
        e PROTEÇÃO ANTI-WATERMARK/ELEMENTOS CORTADOS

        Estrutura otimizada v3.2:
        [PROTECTION_PREFIX] [AVOID_PREFIX] [CRITICAL_INSTRUCTION] [SCENE/DUAL_ENTITY]
        [MAIN_SUBJECT] [ACTION_ELEMENT] [PERCENTAGE_VISUAL] [EVENT_ELEMENT]
        [BACKGROUND] [DRAMA_LEVEL] [LIGHTING] [COLOR_PALETTE] [HIERARCHY]
        [TEXT_AREA] [QUALITY] [QUALITY_PROTECTION_SUFFIX]

        NOVO v3.2: Adiciona proteções anti-watermark no início e fim do prompt
        """
        sections = []

        # 0. PROTECTION_PREFIX no início (MÁXIMO peso - proteção anti-watermark)
        sections.append(self.PROTECTION_PREFIX)

        # 1. AVOID_PREFIX (proibições de estilo)
        sections.append(self.AVOID_PREFIX)

        # 2. NOVO v3.1: INSTRUÇÃO CRÍTICA DE CORRESPONDÊNCIA TÍTULO-IMAGEM
        # Adicionada logo após AVOID_PREFIX para máximo peso
        if context.is_generic_context:
            # Contexto genérico: NUNCA mostrar cripto específica sozinha
            sections.append(self.GENERIC_CONTEXT_INSTRUCTION)
        elif context.entity_type == EntityType.CRYPTO and context.primary_entity:
            # Cripto específica mencionada: mostrar APENAS essa cripto
            crypto_instruction = self.SPECIFIC_CRYPTO_INSTRUCTION_TEMPLATE.format(
                crypto_name=context.primary_entity_display
            )
            sections.append(crypto_instruction)

        # 3. Cena jornalística OU composição dual-entity (se disponível)
        if composition.dual_entity_scene:
            sections.append(composition.dual_entity_scene)
        elif composition.journalistic_scene:
            sections.append(composition.journalistic_scene)
        else:
            # Fallback para estilo fotográfico + subject
            sections.append(composition.photography_style)
            sections.append(f"featuring {composition.main_subject}")

        # 4. Elemento de ação visual (conta a história)
        if composition.action_element:
            sections.append(composition.action_element)

        # 5. Visualização de percentual (dados concretos)
        if composition.percentage_visual:
            sections.append(composition.percentage_visual)

        # 6. Elemento de evento específico (halving, ETF, etc)
        if composition.event_element:
            sections.append(composition.event_element)

        # 7. Background contextual (agora por tipo de notícia)
        sections.append(f"setting: {composition.background}")

        # 8. Nível de dramaticidade
        if composition.drama_level:
            sections.append(composition.drama_level)

        # 9. Iluminação
        sections.append(composition.lighting)

        # 10. Paleta de cores
        sections.append(f"colors: {composition.color_palette}")

        # 11. Hierarquia visual
        if composition.visual_hierarchy:
            sections.append(composition.visual_hierarchy)

        # 12. Área para texto
        sections.append(composition.text_area)

        # 13. Referência de estilo e qualidade (condensados)
        sections.append(self.STYLE_REFERENCE)
        sections.append(self.QUALITY_SUFFIX)

        # 14. NOVO v3.2: PROTEÇÃO DE QUALIDADE no final (reforço crítico)
        sections.append(self.QUALITY_PROTECTION_SUFFIX)

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

    def _validate_and_optimize_prompt(self, prompt: str) -> str:
        """
        Valida e otimiza o prompt antes do envio para a API de imagem.

        - Remove frases duplicadas
        - Limita tamanho do prompt
        - Remove redundâncias

        Args:
            prompt: Prompt a ser otimizado

        Returns:
            Prompt otimizado
        """
        # Dividir em sentenças/frases
        sentences = prompt.split(', ')
        seen = set()
        unique_sentences = []

        for s in sentences:
            # Normalizar para comparação
            s_normalized = s.strip().lower()

            # Ignorar frases vazias ou muito curtas
            if not s_normalized or len(s_normalized) < 3:
                continue

            # Verificar duplicatas
            if s_normalized not in seen:
                seen.add(s_normalized)
                unique_sentences.append(s.strip())

        result = ', '.join(unique_sentences)

        # Limitar tamanho (APIs podem ter limite de ~4000 chars, usamos 1500 para segurança)
        MAX_PROMPT_LENGTH = 1500
        if len(result) > MAX_PROMPT_LENGTH:
            # Cortar no último separador completo
            result = result[:MAX_PROMPT_LENGTH].rsplit(', ', 1)[0]

        return result

    def _sanitize_generic_context(self, prompt: str, context: NewsContext) -> str:
        """
        Remove menções a criptomoedas específicas em contextos genéricos.

        Em notícias como "Altcoins sobem 15%", não queremos que o prompt
        mencione moedas específicas como Bitcoin ou Ethereum, pois isso
        faria a imagem parecer ser sobre uma moeda específica.

        Args:
            prompt: Prompt original
            context: Contexto da notícia

        Returns:
            Prompt com moedas específicas removidas (se contexto genérico)
        """
        # Só aplicar se for contexto genérico
        if not context.is_generic_context:
            return prompt

        result = prompt

        # Substituir nomes de moedas específicas por termos genéricos
        for crypto in self.SPECIFIC_CRYPTO_NAMES:
            # Usar word boundary para não pegar partes de palavras
            pattern = rf'\b{re.escape(crypto)}\b'
            # Substituir por termo genérico apropriado
            result = re.sub(
                pattern,
                'cryptocurrency',
                result,
                flags=re.IGNORECASE
            )

        # Remover referências duplicadas criadas pela substituição
        result = re.sub(
            r'\bcryptocurrency\s+cryptocurrency\b',
            'cryptocurrency',
            result,
            flags=re.IGNORECASE
        )

        logger.debug(f"[PromptGen v3.1] Sanitização de contexto genérico aplicada")

        return result

    def _generate_fallback_prompt(self, category: Optional[str] = None) -> str:
        """
        Gera prompt fallback editorial seguro COM PROTEÇÕES ANTI-WATERMARK v3.2

        Todos os fallbacks agora incluem:
        - Prefixo de proteção anti-watermark
        - Instruções contra logos de terceiros
        - Requisitos de composição completa
        """
        # Proteção comum para todos os fallbacks
        protection_base = (
            "Generate ORIGINAL editorial photography WITHOUT watermarks or third-party branding. "
            "NO Getty Images, NO Shutterstock, NO iStock marks. "
            "NO CoinDesk logo, NO CoinTelegraph branding, NO CoinRepo watermark. "
            "NO abstract networks, NO digital particles. "
        )

        # Proteção final comum
        protection_suffix = (
            "CRITICAL: NO watermarks in corners, NO stock photo logos, "
            "NO third-party branding, NO cropped elements, "
            "complete composition with all elements fully visible, "
            "original editorial quality NOT stock photo reproduction, "
            "publication-ready without licensing concerns"
        )

        category_fallbacks = {
            'bitcoin': (
                f"{protection_base}"
                "Professional product photography of golden Bitcoin physical coin, "
                "centered on clean white surface, orange-gold color palette, "
                "professional studio lighting, original editorial standard, "
                "high contrast for text readability, "
                "clear negative space on left third for headline, photo-realistic, "
                "complete framing with nothing cropped, 16:9 aspect ratio, "
                f"{protection_suffix}"
            ),
            'ethereum': (
                f"{protection_base}"
                "Professional product photography of purple-blue Ethereum diamond logo "
                "as 3D metallic object on gradient background, purple and cyan color palette, "
                "professional lighting, original editorial standard, "
                "high contrast for text readability, "
                "clear negative space for headline overlay, photo-realistic, "
                "complete framing with nothing cropped, 16:9 aspect ratio, "
                f"{protection_suffix}"
            ),
            'defi': (
                f"{protection_base}"
                "Professional fintech interface photography, "
                "clean DeFi protocol visualization on modern backdrop, "
                "teal and professional blue color palette, "
                "original editorial standard, high contrast for text readability, "
                "clear space for headline text, photo-realistic, "
                "complete framing with nothing cropped, 16:9 aspect ratio, "
                f"{protection_suffix}"
            ),
            'regulacao': (
                f"{protection_base}"
                "Government building or institutional architecture photography, "
                "official regulatory setting with professional lighting, "
                "navy and gold institutional color palette, "
                "original editorial standard, high contrast for text readability, "
                "clear negative space for headline, photo-realistic, "
                "complete framing with nothing cropped, 16:9 aspect ratio, "
                f"{protection_suffix}"
            ),
        }

        cat_key = category.lower() if category else 'bitcoin'

        if cat_key not in category_fallbacks:
            return (
                f"{protection_base}"
                "Professional editorial photography for cryptocurrency news, "
                "clean financial market visualization with professional aesthetic, "
                "modern blue and white color palette, "
                "original editorial standard, professional journalism photography, "
                "high contrast for text readability, "
                "clear negative space on left third for headline overlay, "
                "photo-realistic, complete framing with nothing cropped, 16:9 aspect ratio, "
                f"{protection_suffix}"
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
                'prompt_version': 'v3.2-contextual-storytelling-quality-protection',
                'is_generic_context': context.is_generic_context,
            }
        }


    def validar_imagem_gerada(self, titulo_noticia: str) -> dict:
        """
        Retorna checklist de validação para revisão de imagem gerada.

        Esta função fornece um checklist manual para verificar se a imagem
        gerada atende aos padrões de qualidade e não contém watermarks
        ou elementos problemáticos.

        Args:
            titulo_noticia: Título da notícia para referência

        Returns:
            Dict com warnings e checklist manual de verificação
        """
        # Lista de termos que indicam watermark/logo problemático
        termos_proibidos = [
            "getty", "shutterstock", "istock", "unsplash", "pexels",
            "coindesk", "cointelegraph", "coinrepo", "bitcoin magazine",
            "watermark", "copyright", "©", "®", "™"
        ]

        checklist = {
            "verificar_cantos": {
                "descricao": "Verificar se há logos/watermarks nos 4 cantos da imagem",
                "locais": ["canto superior esquerdo", "canto superior direito",
                          "canto inferior esquerdo", "canto inferior direito"],
                "prioridade": "CRÍTICA"
            },
            "verificar_texto_completo": {
                "descricao": "Se há texto visível, confirmar que está completo",
                "exemplos_problema": ["LOBAL ao invés de GLOBAL", "ITCOIN ao invés de BITCOIN"],
                "prioridade": "ALTA"
            },
            "verificar_branding": {
                "descricao": "Confirmar ausência de logos de outros sites/serviços",
                "sites_proibidos": ["CoinDesk", "CoinTelegraph", "CoinRepo", "Getty", "Shutterstock"],
                "prioridade": "CRÍTICA"
            },
            "verificar_crop": {
                "descricao": "Confirmar que nada importante está cortado nas bordas",
                "verificar": ["moedas/logos não cortados", "texto completo", "pessoas com cabeça visível"],
                "prioridade": "ALTA"
            },
            "verificar_qualidade": {
                "descricao": "Confirmar qualidade profissional editorial",
                "criterios": ["foco nítido", "iluminação adequada", "composição equilibrada"],
                "prioridade": "MÉDIA"
            },
            "verificar_correspondencia_titulo": {
                "descricao": f"Verificar se imagem corresponde ao título: '{titulo_noticia}'",
                "verificar": ["cripto correta exibida", "sentimento apropriado", "contexto relevante"],
                "prioridade": "ALTA"
            }
        }

        return {
            "titulo_referencia": titulo_noticia,
            "termos_proibidos": termos_proibidos,
            "checklist_manual": checklist,
            "instrucao": "Revise a imagem verificando cada item do checklist antes de publicar"
        }

    def gerar_prompt_protegido(self, prompt_base: str) -> str:
        """
        Wrapper que adiciona proteções a um prompt base existente.

        Útil para adicionar proteções anti-watermark a prompts já existentes
        ou gerados por outros métodos.

        Args:
            prompt_base: Prompt original sem proteções

        Returns:
            Prompt com proteções anti-watermark adicionadas
        """
        import random

        # Selecionar 2-3 reforços aleatórios
        reforcos = random.sample(self.ANTI_WATERMARK_REINFORCEMENTS, min(3, len(self.ANTI_WATERMARK_REINFORCEMENTS)))
        reforcos_str = ", ".join(reforcos)

        # Montar prompt protegido
        prompt_protegido = (
            f"{self.PROTECTION_PREFIX}"
            f"{prompt_base}, "
            f"{reforcos_str}, "
            f"{self.QUALITY_PROTECTION_SUFFIX}"
        )

        return prompt_protegido.strip()


# Singleton para uso global
smart_prompt_generator = SmartPromptGenerator()
