"""
Contextual Prompt Builder v1.0 - Narrative-Driven Image Prompts

Constrói prompts narrativos para geração de imagens editoriais baseados no
resultado da análise contextual profunda.

FILOSOFIA:
Cada imagem deve CONTAR A HISTÓRIA da notícia em um único olhar.
Não apenas mostrar logos ou moedas, mas visualizar o EVENTO que aconteceu.

EXEMPLO DE TRANSFORMAÇÃO:

Análise contextual:
- story: "SEC aprova primeiro ETF de Bitcoin à vista dos EUA"
- people: ["Gary Gensler"]
- institutions: ["SEC", "BlackRock", "NYSE"]
- cryptocurrencies: ["Bitcoin"]
- specific_event: "Aprovação do primeiro ETF spot de Bitcoin"
- tone: positive-historic

Prompt gerado:
"Original editorial photo, no watermarks, no stock logos.
Professional editorial photography for cryptocurrency news publication.

STORY CONTEXT:
SEC approves first spot Bitcoin ETF in the US, managed by BlackRock,
marking a historic milestone for institutional crypto adoption.

VISUAL NARRATIVE:
Historic regulatory approval moment with official SEC seal,
Gary Gensler at announcement podium, BlackRock institutional branding,
NYSE trading floor celebrating, Bitcoin symbol prominent.

KEY VISUAL ELEMENTS:
- SEC official seal or approval document
- Gary Gensler professional portrait style
- BlackRock institutional branding
- NYSE building or trading floor
- Bitcoin golden coin prominent
- Celebratory institutional atmosphere

COMPOSITION:
Editorial photojournalism, story-driven narrative, professional news standard.

TONE: positive-historic, milestone, celebration

AVOID:
- Random altcoins not mentioned
- Generic crypto imagery unrelated to this story
- Abstract blockchain visualizations

QUALITY:
No watermarks, complete framing, publication-ready, 16:9 aspect ratio"

Changelog:
- v1.0: Implementação inicial do construtor de prompts narrativos
"""

from dataclasses import dataclass
from typing import Optional, List
import random

from app.core.logging import logger
from app.services.ai.contextual_image_analyzer import (
    ContextualAnalysisResult,
    ContextualTone,
)


@dataclass
class PromptComponents:
    """Componentes do prompt separados para flexibilidade"""
    protection_prefix: str
    style_intro: str
    story_context: str
    visual_narrative: str
    key_elements: str
    subjects_section: str
    composition: str
    tone_section: str
    avoid_section: str
    quality_section: str


class ContextualPromptBuilder:
    """
    Construtor de prompts narrativos para geração de imagens editoriais.

    Usa o resultado da análise contextual para gerar prompts que
    CONTAM A HISTÓRIA da notícia visualmente.
    """

    # === PROTEÇÕES DE QUALIDADE ===

    PROTECTION_PREFIX = (
        "Original editorial photo, no watermarks, no stock logos, no third-party branding. "
    )

    QUALITY_PROTECTION_SUFFIX = (
        "clean complete composition, no cropped elements, no watermarks in corners, "
        "no Getty/Shutterstock/iStock marks, publication-ready original image, "
        "16:9 aspect ratio, high contrast for text readability"
    )

    AVOID_BASE = (
        "NO abstract networks, NO digital particles, NO sci-fi effects, "
        "NO blockchain visualizations, NO neon cyberpunk, NO watermarks"
    )

    # === TEMPLATES DE ESTILO ===

    STYLE_INTRO = "Professional editorial photography for cryptocurrency news publication."

    # === TEMPLATES PARA DIFERENTES TONS ===

    TONE_TEMPLATES = {
        ContextualTone.POSITIVE: {
            'atmosphere': 'optimistic, celebratory, forward-looking',
            'lighting': 'bright professional studio lighting with warm accents',
            'colors': 'clean whites, success greens, warm golds',
        },
        ContextualTone.POSITIVE_HISTORIC: {
            'atmosphere': 'historic milestone, triumphant, landmark moment',
            'lighting': 'dramatic golden hour lighting, triumphant atmosphere',
            'colors': 'rich golds, prestigious navy, pristine whites',
        },
        ContextualTone.NEGATIVE: {
            'atmosphere': 'serious, cautionary, concerned',
            'lighting': 'dramatic low-key lighting with serious shadows',
            'colors': 'warning reds, dark grays, serious tones',
        },
        ContextualTone.NEGATIVE_URGENT: {
            'atmosphere': 'urgent, crisis, immediate attention',
            'lighting': 'high contrast urgent lighting',
            'colors': 'alert crimson, stark whites, emergency tones',
        },
        ContextualTone.NEUTRAL: {
            'atmosphere': 'informative, balanced, objective',
            'lighting': 'balanced professional studio lighting',
            'colors': 'professional blues, neutral grays, clean whites',
        },
        ContextualTone.ANALYTICAL: {
            'atmosphere': 'thoughtful, research-oriented, contemplative',
            'lighting': 'soft analytical lighting, intellectual atmosphere',
            'colors': 'deep blues, analytical grays, scholarly tones',
        },
    }

    # === TEMPLATES PARA PESSOAS ===

    PERSON_TEMPLATES = {
        'Gary Gensler': 'Gary Gensler SEC Chairman portrait style, regulatory authority figure',
        'Elon Musk': 'Elon Musk tech entrepreneur portrait style, innovative visionary',
        'Michael Saylor': 'Michael Saylor corporate executive portrait style, Bitcoin advocate',
        'Vitalik Buterin': 'Vitalik Buterin developer portrait style, Ethereum founder',
        'CZ': 'CZ Binance CEO portrait style, crypto exchange leader',
        'CZ (Changpeng Zhao)': 'Changpeng Zhao Binance CEO portrait style',
        'Cathie Wood': 'Cathie Wood investment manager portrait style, ARK Invest',
        'Jerome Powell': 'Jerome Powell Federal Reserve Chairman portrait style',
        'Larry Fink': 'Larry Fink BlackRock CEO portrait style, institutional leader',
    }

    # === TEMPLATES PARA INSTITUIÇÕES ===

    INSTITUTION_TEMPLATES = {
        'SEC': 'SEC official seal, US Securities and Exchange Commission building',
        'CFTC': 'CFTC official seal, US commodities regulation',
        'Federal Reserve': 'Federal Reserve building Washington DC, central bank',
        'BlackRock': 'BlackRock corporate logo, institutional asset management',
        'JPMorgan': 'JPMorgan Chase corporate building, Wall Street institution',
        'Goldman Sachs': 'Goldman Sachs corporate headquarters, investment banking',
        'Fidelity': 'Fidelity Investments corporate branding, institutional finance',
        'Grayscale': 'Grayscale Investments logo, crypto trust management',
        'Binance': 'Binance exchange logo, global crypto trading platform',
        'Coinbase': 'Coinbase exchange logo, US regulated crypto platform',
        'NYSE': 'New York Stock Exchange building facade, Wall Street landmark',
        'NASDAQ': 'NASDAQ MarketSite Times Square, modern stock exchange',
        'Tesla': 'Tesla corporate logo, electric vehicles and innovation',
        'MicroStrategy': 'MicroStrategy corporate logo, business intelligence and Bitcoin',
    }

    # === TEMPLATES PARA CRIPTOMOEDAS ===

    CRYPTO_TEMPLATES = {
        'Bitcoin': 'golden Bitcoin physical coin with orange-gold metallic finish, BTC symbol',
        'Ethereum': 'purple-blue Ethereum diamond logo, ETH 3D metallic object',
        'Solana': 'purple-teal Solana logo, SOL modern 3D render',
        'Cardano': 'blue Cardano ADA logo, geometric 3D object',
        'XRP': 'blue XRP Ripple logo, institutional 3D symbol',
        'Dogecoin': 'golden Dogecoin with Shiba Inu emblem, DOGE coin',
        'Polkadot': 'pink-white Polkadot logo, DOT interconnected spheres',
        'Litecoin': 'silver Litecoin physical coin, LTC metallic finish',
        'Avalanche': 'red Avalanche triangle logo, AVAX bold 3D',
        'Chainlink': 'blue Chainlink hexagon logo, LINK connected element',
        'diverse cryptocurrencies': (
            'MULTIPLE diverse cryptocurrency coins displayed together '
            '(showing BTC, ETH, SOL, ADA, AVAX, DOT symbols), '
            'professional arrangement of various crypto assets, '
            'NOT single coin focus, diverse portfolio visualization'
        ),
    }

    # === TEMPLATES PARA EVENTOS ===

    EVENT_TEMPLATES = {
        'etf approval': 'ETF approval documentation, official regulatory acceptance ceremony',
        'halving': 'Bitcoin halving countdown clock, mining reward reduction visualization',
        'partnership': 'corporate partnership signing ceremony, collaborative agreement',
        'listing': 'exchange listing announcement, new trading pair celebration',
        'upgrade': 'network upgrade deployment, protocol evolution visualization',
        'hack': 'security breach visualization, digital fortress compromise (no violence)',
        'regulation': 'regulatory framework documentation, government oversight',
        'adoption': 'mainstream payment terminal accepting crypto, consumer adoption',
        'ipo': 'stock market IPO ceremony, company going public celebration',
        'merger': 'corporate merger visualization, companies joining together',
    }

    def __init__(self):
        """Inicializa o construtor de prompts"""
        logger.info("ContextualPromptBuilder v1.0 inicializado")

    def build_prompt(
        self,
        analysis: ContextualAnalysisResult,
        max_length: int = 1500
    ) -> str:
        """
        Constrói um prompt narrativo completo baseado na análise contextual.

        Args:
            analysis: Resultado da análise contextual
            max_length: Tamanho máximo do prompt

        Returns:
            Prompt otimizado para geração de imagem editorial
        """
        try:
            components = self._build_components(analysis)
            prompt = self._assemble_prompt(components)
            prompt = self._optimize_prompt(prompt, max_length)

            logger.debug(f"[PromptBuilder] Prompt gerado ({len(prompt)} chars): {prompt[:200]}...")
            return prompt

        except Exception as e:
            logger.error(f"[PromptBuilder] Erro ao construir prompt: {e}")
            return self._build_fallback_prompt(analysis)

    def _build_components(self, analysis: ContextualAnalysisResult) -> PromptComponents:
        """Constrói os componentes individuais do prompt"""

        # 1. Story Context
        story_context = f"STORY CONTEXT: {analysis.story_summary}"

        # 2. Visual Narrative
        visual_narrative = f"VISUAL NARRATIVE: {analysis.visual_concept}"

        # 3. Key Elements
        key_elements = self._build_key_elements(analysis)

        # 4. Subjects Section (pessoas, instituições, criptos)
        subjects_section = self._build_subjects_section(analysis)

        # 5. Composition Style
        composition = self._build_composition(analysis)

        # 6. Tone Section
        tone_section = self._build_tone_section(analysis)

        # 7. Avoid Section
        avoid_section = self._build_avoid_section(analysis)

        # 8. Quality Section
        quality_section = self.QUALITY_PROTECTION_SUFFIX

        return PromptComponents(
            protection_prefix=self.PROTECTION_PREFIX,
            style_intro=self.STYLE_INTRO,
            story_context=story_context,
            visual_narrative=visual_narrative,
            key_elements=key_elements,
            subjects_section=subjects_section,
            composition=composition,
            tone_section=tone_section,
            avoid_section=avoid_section,
            quality_section=quality_section,
        )

    def _build_key_elements(self, analysis: ContextualAnalysisResult) -> str:
        """Constrói a seção de elementos visuais chave"""
        if not analysis.key_visual_elements:
            return ""

        elements = analysis.key_visual_elements[:6]  # Limitar a 6 elementos
        elements_text = "\n".join(f"- {elem}" for elem in elements)
        return f"KEY VISUAL ELEMENTS:\n{elements_text}"

    def _build_subjects_section(self, analysis: ContextualAnalysisResult) -> str:
        """Constrói a seção de subjects (pessoas, instituições, criptos)"""
        sections = []

        # Pessoas
        if analysis.people:
            people_descriptions = []
            for person in analysis.people[:2]:  # Limitar a 2 pessoas
                if person in self.PERSON_TEMPLATES:
                    people_descriptions.append(self.PERSON_TEMPLATES[person])
                else:
                    people_descriptions.append(f"{person} professional portrait style")

            sections.append(f"PEOPLE: {'; '.join(people_descriptions)}")

        # Instituições
        if analysis.institutions:
            inst_descriptions = []
            for inst in analysis.institutions[:3]:  # Limitar a 3 instituições
                if inst in self.INSTITUTION_TEMPLATES:
                    inst_descriptions.append(self.INSTITUTION_TEMPLATES[inst])
                else:
                    inst_descriptions.append(f"{inst} corporate/official branding")

            sections.append(f"INSTITUTIONS: {'; '.join(inst_descriptions)}")

        # Criptomoedas
        if analysis.cryptocurrencies:
            crypto_descriptions = []
            for crypto in analysis.cryptocurrencies[:2]:  # Limitar a 2 criptos
                if crypto in self.CRYPTO_TEMPLATES:
                    crypto_descriptions.append(self.CRYPTO_TEMPLATES[crypto])
                else:
                    crypto_descriptions.append(f"{crypto} cryptocurrency logo as 3D metallic object")

            # Instrução crítica para criptos específicas
            if not analysis.is_generic_context and analysis.cryptocurrencies:
                crypto_only_list = ', '.join(analysis.cryptocurrencies)
                sections.append(
                    f"CRYPTOCURRENCIES: {'; '.join(crypto_descriptions)}. "
                    f"CRITICAL: Show ONLY {crypto_only_list}, do NOT include other cryptocurrencies"
                )
            else:
                sections.append(f"CRYPTOCURRENCIES: {'; '.join(crypto_descriptions)}")

        # Evento específico
        if analysis.specific_event:
            event_key = self._match_event_template(analysis.specific_event)
            if event_key:
                sections.append(f"SPECIFIC EVENT: {self.EVENT_TEMPLATES[event_key]}")
            else:
                sections.append(f"SPECIFIC EVENT: {analysis.specific_event}")

        # Localização geográfica
        if analysis.geographic_location:
            sections.append(f"LOCATION CONTEXT: {analysis.geographic_location} setting")

        return "\n".join(sections)

    def _match_event_template(self, event_description: str) -> Optional[str]:
        """Encontra template de evento que corresponde à descrição"""
        event_lower = event_description.lower()

        event_keywords = {
            'etf approval': ['etf', 'aprovação', 'approval'],
            'halving': ['halving', 'halvening'],
            'partnership': ['parceria', 'partnership', 'acordo'],
            'listing': ['listagem', 'listing'],
            'upgrade': ['upgrade', 'atualização', 'fork'],
            'hack': ['hack', 'ataque', 'breach', 'roubo'],
            'regulation': ['regulação', 'regulation', 'lei', 'law'],
            'adoption': ['adoção', 'adoption', 'aceita'],
            'ipo': ['ipo', 'abertura de capital'],
            'merger': ['fusão', 'merger', 'aquisição'],
        }

        for event_key, keywords in event_keywords.items():
            if any(kw in event_lower for kw in keywords):
                return event_key

        return None

    def _build_composition(self, analysis: ContextualAnalysisResult) -> str:
        """Constrói a seção de composição"""
        composition_parts = [
            "Editorial photojournalism aesthetic",
            "Story-driven visual narrative",
            "Professional news publication standard",
            "Clear visual storytelling of THIS specific event",
        ]

        # Adicionar contexto específico baseado na importância
        if analysis.importance == 'breaking':
            composition_parts.append("High-impact breaking news composition")
        elif analysis.importance == 'major':
            composition_parts.append("Significant news milestone composition")
        elif analysis.importance == 'analysis':
            composition_parts.append("Thoughtful analytical composition")

        return f"COMPOSITION: {'. '.join(composition_parts)}"

    def _build_tone_section(self, analysis: ContextualAnalysisResult) -> str:
        """Constrói a seção de tom"""
        tone_config = self.TONE_TEMPLATES.get(
            analysis.tone,
            self.TONE_TEMPLATES[ContextualTone.NEUTRAL]
        )

        return (
            f"TONE & ATMOSPHERE: {tone_config['atmosphere']}. "
            f"LIGHTING: {tone_config['lighting']}. "
            f"COLORS: {tone_config['colors']}"
        )

    def _build_avoid_section(self, analysis: ContextualAnalysisResult) -> str:
        """Constrói a seção de elementos a evitar"""
        avoid_items = [self.AVOID_BASE]

        # Evitar criptos não mencionadas
        if analysis.cryptocurrencies and not analysis.is_generic_context:
            mentioned = ', '.join(analysis.cryptocurrencies)
            avoid_items.append(
                f"Random altcoins not mentioned (ONLY show {mentioned})"
            )
        else:
            avoid_items.append("Single specific altcoin focus when topic is generic")

        # Evitar elementos não relacionados à história
        avoid_items.append("Generic cryptocurrency imagery unrelated to this story")
        avoid_items.append("Elements not mentioned in the news story")

        return f"AVOID: {'. '.join(avoid_items)}"

    def _assemble_prompt(self, components: PromptComponents) -> str:
        """Monta o prompt final a partir dos componentes"""
        sections = [
            components.protection_prefix,
            components.style_intro,
            "",
            components.story_context,
            "",
            components.visual_narrative,
            "",
            components.key_elements,
            "",
            components.subjects_section,
            "",
            components.composition,
            "",
            components.tone_section,
            "",
            components.avoid_section,
            "",
            f"QUALITY: {components.quality_section}",
        ]

        # Filtrar seções vazias e juntar
        prompt = "\n".join(s for s in sections if s)

        return prompt

    def _optimize_prompt(self, prompt: str, max_length: int) -> str:
        """Otimiza o prompt para o tamanho máximo"""
        if len(prompt) <= max_length:
            return prompt

        # Estratégia: remover seções menos importantes se necessário
        # Prioridade: protection > story > subjects > composition > tone > avoid > quality

        # Simplificar removendo quebras de linha extras
        prompt = prompt.replace("\n\n", "\n").replace("\n", ", ")

        # Truncar se ainda muito longo
        if len(prompt) > max_length:
            prompt = prompt[:max_length].rsplit(', ', 1)[0]

        return prompt

    def _build_fallback_prompt(self, analysis: ContextualAnalysisResult) -> str:
        """Prompt de fallback em caso de erro"""
        base = self.PROTECTION_PREFIX

        if analysis.cryptocurrencies and not analysis.is_generic_context:
            crypto = analysis.cryptocurrencies[0]
            if crypto in self.CRYPTO_TEMPLATES:
                subject = self.CRYPTO_TEMPLATES[crypto]
            else:
                subject = f"{crypto} cryptocurrency as professional 3D product shot"
        else:
            subject = self.CRYPTO_TEMPLATES['diverse cryptocurrencies']

        return (
            f"{base}"
            f"Professional editorial photography of {subject}, "
            f"clean composition, {self.QUALITY_PROTECTION_SUFFIX}"
        )

    def build_prompt_with_metadata(
        self,
        analysis: ContextualAnalysisResult
    ) -> dict:
        """
        Constrói prompt com metadados para debug e logging.

        Returns:
            Dict com prompt e metadados
        """
        prompt = self.build_prompt(analysis)

        return {
            'prompt': prompt,
            'metadata': {
                'story_summary': analysis.story_summary,
                'visual_concept': analysis.visual_concept,
                'cryptocurrencies': analysis.cryptocurrencies,
                'institutions': analysis.institutions,
                'people': analysis.people,
                'tone': analysis.tone.value,
                'importance': analysis.importance,
                'is_generic_context': analysis.is_generic_context,
                'confidence_score': analysis.confidence_score,
                'analyzer_version': analysis.analyzer_version,
                'prompt_length': len(prompt),
                'prompt_version': 'contextual-narrative-v1.0',
            }
        }


# Singleton para uso global
contextual_prompt_builder = ContextualPromptBuilder()
