"""
Smart Prompt Generator v4.0 - AI-Powered Contextual Storytelling + Quality Protection
Gerador de prompts para imagens de notícias de criptomoedas com STORYTELLING VISUAL

## NOVO EM v4.0: ANÁLISE CONTEXTUAL VIA IA

A partir da v4.0, o sistema usa IA (Gemini/Claude) para analisar o CONTEÚDO COMPLETO
da notícia, não apenas extrair keywords do título. Isso resulta em:

✅ Imagens que CONTAM A HISTÓRIA real da notícia
✅ Elementos visuais ESPECÍFICOS ao contexto (pessoas, instituições, eventos)
✅ Conexão direta entre texto e visual
✅ Muito mais relevância e profissionalismo

### EXEMPLO DE DIFERENÇA:

**ANTES (v3.x - baseado em regex/keywords):**
Título: "SEC aprova ETF de Bitcoin"
Análise: keywords=["SEC", "aprova", "ETF", "Bitcoin"]
Prompt: "SEC logo, Bitcoin coin, approval stamp"
Resultado: Imagem genérica de logo + moeda

**DEPOIS (v4.0 - baseado em contexto completo):**
Título: "SEC aprova ETF de Bitcoin"
Conteúdo: "Gary Gensler anunciou... BlackRock será a primeira... NYSE começará negociações..."
Análise IA: Entende todo o contexto, pessoas, instituições, evento histórico
Prompt: "Gary Gensler at SEC podium, BlackRock branding, NYSE trading floor,
        Bitcoin symbol, historic approval atmosphere, institutional celebration"
Resultado: Imagem que CONTA A HISTÓRIA completa

## MODOS DE OPERAÇÃO:

1. **CONTEXTUAL (NOVO - RECOMENDADO):**
   - Usa `generate_prompt_contextual()` (async)
   - Analisa conteúdo completo via Gemini
   - Gera prompts narrativos específicos

2. **LEGACY (compatibilidade):**
   - Usa `generate_prompt()` (sync)
   - Mantém comportamento v3.2 baseado em regex
   - Útil como fallback quando Gemini indisponível

## PROTEÇÃO ANTI-WATERMARK E QUALIDADE (v3.2+)

TODOS os prompts gerados incluem proteções contra:
- ❌ Watermarks de bancos de imagens (Getty, Shutterstock, iStock, Unsplash, Pexels)
- ❌ Logos de outros sites de notícias (CoinDesk, CoinTelegraph, CoinRepo, Bitcoin Magazine)
- ❌ Símbolos de copyright ou créditos visíveis
- ❌ Elementos cortados ou incompletos nas bordas
- ❌ Texto parcialmente visível (ex: "LOBAL" ao invés de "GLOBAL")

Características dos prompts gerados v4.0:
- ANÁLISE CONTEXTUAL PROFUNDA via IA (NOVO v4.0)
- PROMPTS NARRATIVOS que contam histórias (NOVO v4.0)
- Elementos visuais ESPECÍFICOS ao contexto (NOVO v4.0)
- Elementos visuais CONCRETOS com AÇÃO visual
- Composições DUAL-ENTITY para notícias relacionais
- Backgrounds CONTEXTUAIS por tipo de notícia
- Visualização de PERCENTUAIS quando relevante
- Níveis de DRAMATICIDADE baseados na magnitude
- Cenas JORNALÍSTICAS que contam histórias
- HIERARQUIA VISUAL por importância da notícia
- Prompts OTIMIZADOS e condensados
- PROTEÇÃO ANTI-WATERMARK em todos os prompts
- PROTEÇÃO contra elementos cortados/incompletos

Changelog v4.0:
- Adicionada análise contextual profunda via Gemini (ContextualImageAnalyzer)
- Adicionado construtor de prompts narrativos (ContextualPromptBuilder)
- Novo método async generate_prompt_contextual() para análise completa
- Novo método async generate_prompt_with_metadata_contextual() com metadados
- Mantida compatibilidade total com métodos v3.2 (sync)
- Integração transparente: usa contextual se disponível, fallback para legacy

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

# v4.0: Novos módulos de análise contextual
from app.services.ai.contextual_image_analyzer import (
    ContextualImageAnalyzer,
    ContextualAnalysisResult,
    contextual_image_analyzer
)
from app.services.ai.contextual_prompt_builder import (
    ContextualPromptBuilder,
    contextual_prompt_builder
)


class SmartPromptGenerator:
    """
    Gerador de prompts v4.0 - AI-Powered Contextual Storytelling + Quality Protection

    Gera prompts otimizados para Gemini/DALL-E com STORYTELLING VISUAL.
    Cada imagem conta a história da notícia em um único olhar.

    ## NOVIDADE v4.0: ANÁLISE CONTEXTUAL VIA IA

    O método `generate_prompt_contextual()` (async) usa IA para analisar
    o CONTEÚDO COMPLETO da notícia, gerando prompts muito mais relevantes.

    Os métodos `generate_prompt()` e `generate_prompt_with_metadata()` (sync)
    continuam disponíveis para compatibilidade.

    Foco em:
    - ANÁLISE CONTEXTUAL PROFUNDA via IA (NOVO v4.0)
    - Ação visual (não apenas entidades estáticas)
    - Contexto narrativo claro
    - Dramaticidade proporcional à magnitude
    - Composições jornalísticas profissionais
    - PROTEÇÃO contra watermarks, logos indesejados e elementos cortados
    """

    # === CONFIGURAÇÃO DO ESTILO EDITORIAL v3.2 ===

    # === PROTEÇÃO ANTI-WATERMARK E QUALIDADE (v3.2 OTIMIZADO) ===
    # NOTA: Instruções muito longas podem fazer o Gemini falhar.
    # Mantemos as proteções concisas mas efetivas.

    # Prefixo de proteção anti-watermark (CONCISO - vai no INÍCIO do prompt)
    PROTECTION_PREFIX = (
        "Original editorial photo, no watermarks, no stock logos, no third-party branding, "
        "NO news site logos (NO CoinDesk, NO CoinTelegraph, NO Bitcoin Magazine logos). "
    )

    # Sufixo de proteção de qualidade (CONCISO - vai no FINAL do prompt)
    QUALITY_PROTECTION_SUFFIX = (
        "clean complete composition, no cropped elements, no watermarks in corners, "
        "no Getty/Shutterstock/iStock marks, no CoinDesk/CoinTelegraph/news site branding, "
        "publication-ready original image"
    )

    # Reforços anti-watermark para usar estrategicamente
    ANTI_WATERMARK_REINFORCEMENTS = [
        "without watermarks",
        "no stock photo marks",
        "clean professional image",
        "original editorial style",
        "publication-ready",
        "no branding marks",
        "complete composition",
    ]

    # Prefixo de proibição (mantido CONCISO)
    AVOID_PREFIX = (
        "NO abstract networks, NO digital particles, NO sci-fi effects, "
        "NO blockchain visualizations, NO neon cyberpunk, NO watermarks, "
        "NO news website logos or branding (CoinDesk, CoinTelegraph, Bitcoin Magazine, CryptoSlate, Decrypt). "
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

    # Sentenças que NUNCA podem ser cortadas pelo cap de tamanho: carregam o
    # formato (16:9) e as proteções de marca. Elas ficam no FIM do prompt, que
    # era exatamente onde o corte agia — ver _validate_and_optimize_prompt.
    MANDATORY_TAIL_PARTS = (QUALITY_SUFFIX, QUALITY_PROTECTION_SUFFIX)

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
        elements_bank: Optional[EditorialVisualElementsBank] = None,
        contextual_analyzer: Optional[ContextualImageAnalyzer] = None,
        prompt_builder: Optional[ContextualPromptBuilder] = None
    ):
        """
        Inicializa o gerador de prompts editoriais

        Args:
            context_analyzer: Analisador de contexto legacy (usa singleton se None)
            elements_bank: Banco de elementos visuais (usa singleton se None)
            contextual_analyzer: Analisador contextual via IA (NOVO v4.0)
            prompt_builder: Construtor de prompts narrativos (NOVO v4.0)
        """
        # Componentes legacy (v3.2) - mantidos para compatibilidade
        self.context_analyzer = context_analyzer or news_context_analyzer
        self.elements_bank = elements_bank or editorial_visual_elements_bank

        # Componentes v4.0 - análise contextual via IA
        self.contextual_analyzer = contextual_analyzer or contextual_image_analyzer
        self.prompt_builder = prompt_builder or contextual_prompt_builder

        # Cache de hashes para evitar repetição
        self._recent_prompts: list[str] = []
        self._max_cache_size = 50

        logger.info("SmartPromptGenerator v4.0 (AI-Powered Contextual Storytelling + Quality Protection) inicializado")

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

        # Limitar tamanho (Imagen aceita ~480 tokens; 1500 chars é a margem segura)
        MAX_PROMPT_LENGTH = 1500
        if len(result) <= MAX_PROMPT_LENGTH:
            return result

        # ATENÇÃO: não voltar a cortar pelo fim (`result[:MAX].rsplit`).
        # Os guardrails obrigatórios — 16:9, anti-watermark,
        # anti-Getty/Shutterstock e anti-branding de veículos — ficam no FINAL
        # do prompt, então o corte por tamanho os descartava em silêncio.
        # Agora sacrificamos o miolo DESCRITIVO (cena, iluminação, paleta),
        # de trás para frente, e a cauda obrigatória sempre sobrevive.
        mandatory = {
            s.strip().lower()
            for part in self.MANDATORY_TAIL_PARTS
            for s in part.split(', ')
            if s.strip()
        }

        kept = list(unique_sentences)

        def _joined() -> str:
            return ', '.join(s for s in kept if s is not None)

        for i in reversed(range(len(kept))):
            if len(_joined()) <= MAX_PROMPT_LENGTH:
                break
            if kept[i] is not None and kept[i].strip().lower() not in mandatory:
                kept[i] = None

        result = _joined()
        dropped = sum(1 for s in kept if s is None)
        if dropped:
            logger.debug(
                f"[PromptGen] Prompt acima de {MAX_PROMPT_LENGTH} chars: "
                f"{dropped} sentença(s) descritiva(s) removida(s), "
                f"guardrails preservados"
            )

        if len(result) > MAX_PROMPT_LENGTH:
            # Só os guardrails já estouram o cap: preferimos manter as
            # proteções e passar do limite a gerar imagem com marca d'água.
            logger.warning(
                f"[PromptGen] Guardrails obrigatórios somam {len(result)} chars "
                f"(> {MAX_PROMPT_LENGTH}) — cap excedido de propósito"
            )

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

        NOTA: Prompts concisos para evitar rejeição pelo Gemini.
        """
        category_fallbacks = {
            'bitcoin': (
                "Original editorial photo, no watermarks, no stock logos. "
                "Professional product photography of golden Bitcoin physical coin, "
                "centered on clean white surface, orange-gold palette, "
                "professional studio lighting, high contrast, "
                "negative space on left for headline, photo-realistic, "
                "complete framing, 16:9 aspect ratio, no cropped elements"
            ),
            'ethereum': (
                "Original editorial photo, no watermarks, no stock logos. "
                "Professional photography of purple-blue Ethereum diamond logo, "
                "3D metallic object on gradient background, purple and cyan palette, "
                "professional lighting, high contrast, "
                "negative space for headline overlay, photo-realistic, "
                "complete framing, 16:9 aspect ratio, no cropped elements"
            ),
            'defi': (
                "Original editorial photo, no watermarks, no stock logos. "
                "Professional fintech interface photography, "
                "clean DeFi protocol visualization on modern backdrop, "
                "teal and blue palette, high contrast, "
                "space for headline text, photo-realistic, "
                "complete framing, 16:9 aspect ratio, no cropped elements"
            ),
            'regulacao': (
                "Original editorial photo, no watermarks, no stock logos. "
                "Government building or institutional architecture photography, "
                "official regulatory setting with professional lighting, "
                "navy and gold palette, high contrast, "
                "negative space for headline, photo-realistic, "
                "complete framing, 16:9 aspect ratio, no cropped elements"
            ),
        }

        cat_key = category.lower() if category else 'bitcoin'

        if cat_key not in category_fallbacks:
            return (
                "Original editorial photo, no watermarks, no stock logos. "
                "Professional editorial photography for cryptocurrency news, "
                "clean financial market visualization, "
                "modern blue and white palette, professional journalism style, "
                "high contrast, negative space on left for headline, "
                "photo-realistic, complete framing, 16:9 aspect ratio, no cropped elements"
            )

        return category_fallbacks[cat_key]

    def generate_prompt_with_metadata(
        self,
        title: str,
        content: str,
        category: Optional[str] = None
    ) -> dict:
        """
        Gera prompt com metadados completos para logging e debug (MODO LEGACY)

        NOTA: Para análise contextual via IA, use generate_prompt_with_metadata_contextual()

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

    # ====================================================================
    # v4.0: MÉTODOS ASYNC PARA ANÁLISE CONTEXTUAL VIA IA
    # ====================================================================

    async def generate_prompt_contextual(
        self,
        title: str,
        content: str,
        category: Optional[str] = None
    ) -> str:
        """
        Gera um prompt usando ANÁLISE CONTEXTUAL VIA IA (v4.0 RECOMENDADO)

        Este método usa Gemini para analisar o CONTEÚDO COMPLETO da notícia,
        extraindo contexto semântico profundo para gerar prompts que
        CONTAM A HISTÓRIA da notícia visualmente.

        Args:
            title: Título da notícia
            content: Conteúdo COMPLETO da notícia (não apenas resumo)
            category: Categoria pré-definida (opcional)

        Returns:
            Prompt otimizado para geração de imagem editorial com contexto narrativo
        """
        try:
            # 1. Análise contextual profunda via IA
            logger.info(f"[PromptGen v4.0] Análise contextual: {title[:50]}...")
            analysis = await self.contextual_analyzer.analyze(title, content, category)

            logger.info(
                f"[PromptGen v4.0] Análise completa: "
                f"story='{analysis.story_summary[:40]}...', "
                f"cryptos={analysis.cryptocurrencies}, "
                f"institutions={analysis.institutions[:3]}, "
                f"tone={analysis.tone.value}, "
                f"confidence={analysis.confidence_score:.2f}"
            )

            # 2. Construir prompt narrativo
            prompt = self.prompt_builder.build_prompt(analysis)

            # 3. Garantir variação
            prompt = self._ensure_variation(prompt)

            logger.debug(f"[PromptGen v4.0] Prompt ({len(prompt)} chars): {prompt[:300]}...")
            return prompt

        except Exception as e:
            logger.error(f"[PromptGen v4.0] Erro na análise contextual: {e}")
            logger.info("[PromptGen v4.0] Fallback para método legacy...")
            # Fallback para método legacy se análise contextual falhar
            return self.generate_prompt(title, content, category)

    async def generate_prompt_with_metadata_contextual(
        self,
        title: str,
        content: str,
        category: Optional[str] = None
    ) -> dict:
        """
        Gera prompt com metadados usando ANÁLISE CONTEXTUAL VIA IA (v4.0 RECOMENDADO)

        Este método fornece tanto o prompt quanto metadados detalhados da análise
        contextual, útil para logging, debug e auditoria.

        Args:
            title: Título da notícia
            content: Conteúdo COMPLETO da notícia
            category: Categoria opcional

        Returns:
            Dict com prompt e metadados completos da análise contextual
        """
        try:
            # 1. Análise contextual profunda via IA
            analysis = await self.contextual_analyzer.analyze(title, content, category)

            # 2. Construir prompt com metadados
            result = self.prompt_builder.build_prompt_with_metadata(analysis)

            # 3. Garantir variação no prompt
            result['prompt'] = self._ensure_variation(result['prompt'])

            return result

        except Exception as e:
            logger.error(f"[PromptGen v4.0] Erro na análise contextual com metadata: {e}")
            logger.info("[PromptGen v4.0] Fallback para método legacy...")
            # Fallback para método legacy
            return self.generate_prompt_with_metadata(title, content, category)

    async def analyze_news_context(
        self,
        title: str,
        content: str,
        category: Optional[str] = None
    ) -> ContextualAnalysisResult:
        """
        Analisa o contexto da notícia sem gerar prompt (útil para debug)

        Args:
            title: Título da notícia
            content: Conteúdo completo da notícia
            category: Categoria opcional

        Returns:
            ContextualAnalysisResult com análise completa
        """
        return await self.contextual_analyzer.analyze(title, content, category)


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
            Prompt com proteções anti-watermark adicionadas (versão concisa)
        """
        import random

        # Selecionar 2 reforços aleatórios (manter conciso)
        reforcos = random.sample(self.ANTI_WATERMARK_REINFORCEMENTS, 2)
        reforcos_str = ", ".join(reforcos)

        # Montar prompt protegido (conciso para evitar rejeição)
        prompt_protegido = (
            f"{self.PROTECTION_PREFIX}"
            f"{prompt_base}, "
            f"{reforcos_str}"
        )

        return prompt_protegido.strip()


# Singleton para uso global
smart_prompt_generator = SmartPromptGenerator()
