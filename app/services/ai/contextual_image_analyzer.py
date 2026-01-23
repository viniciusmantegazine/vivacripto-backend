"""
Contextual Image Analyzer v1.0 - AI-Powered Deep Context Analysis

Analisa o CONTEÚDO COMPLETO da notícia usando IA para extrair contexto semântico profundo
para geração de imagens editoriais que CONTAM A HISTÓRIA da notícia.

PROBLEMA RESOLVIDO:
O sistema anterior (v3.x) analisava apenas keywords do título usando regex patterns.
Isso resultava em imagens genéricas que não refletiam a história real da notícia.

SOLUÇÃO:
Este módulo usa IA (Gemini/Claude) para fazer análise profunda do conteúdo completo,
extraindo elementos visuais ESPECÍFICOS e CONCRETOS que representam a história.

EXEMPLO DE DIFERENÇA:

ANTES (baseado em keywords):
Título: "Altcoins: 2026 marca virada para mercados 24/7"
Análise regex: ["Altcoins", "2026", "mercados", "24/7"]
Prompt: "diverse cryptocurrency symbols, trading floor, 24/7 concept"
Resultado: Imagem genérica de várias moedas

DEPOIS (baseado em contexto completo):
Título: "Altcoins: 2026 marca virada para mercados 24/7"
Conteúdo: "A NYSE anunciou parceria com Coinbase para lançar primeira
plataforma de negociação de altcoins 24/7 regulamentada..."
Análise IA: Entende que é sobre NYSE + Coinbase + regulamentação
Prompt: "NYSE building with Coinbase branding, regulatory approval,
24/7 global trading clock, institutional setting"
Resultado: Imagem específica contando a história real

Changelog:
- v1.0: Implementação inicial com análise contextual via Gemini
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

from app.core.logging import logger
from app.core.config import settings

# Google Gemini imports
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google GenAI SDK não instalado. Análise contextual via Gemini indisponível.")


class ContextualTone(Enum):
    """Tom da notícia para direcionamento visual"""
    POSITIVE = "positive"           # Boa notícia, celebração, conquista
    POSITIVE_HISTORIC = "positive-historic"  # Marco histórico positivo
    NEGATIVE = "negative"           # Má notícia, alerta, problema
    NEGATIVE_URGENT = "negative-urgent"      # Crise, emergência
    NEUTRAL = "neutral"             # Informativo, sem julgamento
    ANALYTICAL = "analytical"       # Análise, opinião, previsão


@dataclass
class VisualElement:
    """Elemento visual específico extraído da análise"""
    description: str
    priority: int = 1  # 1 = mais importante
    source_context: Optional[str] = None  # De onde no texto foi extraído


@dataclass
class ContextualAnalysisResult:
    """
    Resultado da análise contextual profunda usando IA

    Contém todos os elementos necessários para gerar um prompt
    que CONTA A HISTÓRIA VISUAL da notícia.
    """
    # Resumo narrativo
    story_summary: str  # "SEC aprova primeiro ETF de Bitcoin após anos de espera"

    # Conceito visual principal
    visual_concept: str  # "Momento histórico de aprovação regulatória"

    # Elementos visuais chave (específicos desta história)
    key_visual_elements: List[str]

    # Entidades mencionadas
    people: List[str]  # ["Gary Gensler", "Larry Fink"]
    institutions: List[str]  # ["SEC", "BlackRock", "NYSE"]
    cryptocurrencies: List[str]  # ["Bitcoin"] - APENAS as mencionadas

    # Contexto específico
    specific_event: Optional[str]  # "Aprovação do primeiro ETF spot de Bitcoin"
    geographic_location: Optional[str]  # "Estados Unidos"

    # Dados numéricos relevantes
    numeric_data: List[str]  # ["15%", "$52.000", "$30-50 bilhões"]

    # Tom e importância
    tone: ContextualTone
    importance: str  # "breaking", "major", "standard", "analysis"

    # Elementos contextuais adicionais
    contextual_elements: List[str]

    # Indicador de contexto genérico
    is_generic_context: bool = False

    # Confiança da análise (0.0 a 1.0)
    confidence_score: float = 0.8

    # Versão do analisador
    analyzer_version: str = "contextual-v1.0"


class ContextualImageAnalyzer:
    """
    Analisador de contexto usando IA para geração de imagens editoriais.

    Usa o conteúdo COMPLETO da notícia (não apenas o título) para entender
    a história e gerar prompts que representam visualmente o contexto real.
    """

    # Modelo Gemini para análise de texto
    GEMINI_TEXT_MODEL = "gemini-2.5-flash"

    # Limite de caracteres do conteúdo para análise
    MAX_CONTENT_LENGTH = 3000

    # Prompt de análise contextual
    ANALYSIS_PROMPT_TEMPLATE = '''Você é um especialista em análise de notícias para geração de imagens editoriais profissionais.

Analise esta notícia de criptomoedas e extraia informações ESPECÍFICAS e CONCRETAS para criar uma imagem editorial que CONTE A HISTÓRIA VISUAL desta notícia em um único olhar.

TÍTULO: {title}

CONTEÚDO COMPLETO:
{content}

REGRAS CRÍTICAS:
1. Foque em elementos ESPECÍFICOS e CONCRETOS mencionados no texto
2. Se pessoas são mencionadas (CEOs, reguladores), inclua-as
3. Se empresas/instituições são mencionadas, inclua-as
4. Liste APENAS as criptomoedas realmente mencionadas na notícia
5. Se o texto fala de "altcoins" ou "criptomoedas" de forma genérica, indique is_generic_context=true
6. O conceito visual deve representar a HISTÓRIA, não apenas símbolos genéricos

Retorne APENAS um JSON válido com esta estrutura:
{{
  "story_summary": "Resumo da história em 1-2 frases que explica o que aconteceu",
  "visual_concept": "Descrição de como visualizar esta história em uma imagem (2-3 frases)",
  "key_visual_elements": [
    "Elemento visual específico 1 desta história",
    "Elemento visual específico 2 desta história",
    "Elemento visual específico 3 desta história",
    "Elemento visual específico 4 desta história"
  ],
  "people": ["Nome de pessoa 1", "Nome de pessoa 2"],
  "institutions": ["Empresa 1", "Instituição 1", "Órgão regulador"],
  "cryptocurrencies": ["Cripto específica mencionada"],
  "specific_event": "Descrição do evento concreto que aconteceu",
  "geographic_location": "País ou cidade se mencionado, ou null",
  "numeric_data": ["15%", "$50.000", "24 horas"],
  "tone": "positive|positive-historic|negative|negative-urgent|neutral|analytical",
  "importance": "breaking|major|standard|analysis",
  "contextual_elements": ["Detalhe contextual relevante 1", "Detalhe contextual 2"],
  "is_generic_context": false
}}

IMPORTANTE:
- Se a notícia fala de "altcoins", "criptomoedas" ou "mercado cripto" de forma GENÉRICA (sem mencionar moedas específicas), defina is_generic_context=true e deixe cryptocurrencies vazio ou com ["diverse cryptocurrencies"]
- Seja ESPECÍFICO ao contexto DESTA notícia, não genérico
- Pense como um fotojornalista: qual cena conta esta história?'''

    def __init__(self):
        """Inicializa o analisador contextual"""
        self.gemini_client = None
        self.use_gemini = False

        if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            try:
                self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.use_gemini = True
                logger.info("ContextualImageAnalyzer v1.0: Gemini configurado para análise contextual")
            except Exception as e:
                logger.warning(f"Falha ao inicializar Gemini para análise contextual: {e}")
        else:
            logger.warning("ContextualImageAnalyzer v1.0: Gemini não disponível, usando fallback")

    async def analyze(
        self,
        title: str,
        content: str,
        category: Optional[str] = None
    ) -> ContextualAnalysisResult:
        """
        Analisa o contexto completo da notícia usando IA.

        Args:
            title: Título da notícia
            content: Conteúdo COMPLETO da notícia
            category: Categoria opcional

        Returns:
            ContextualAnalysisResult com análise profunda do contexto
        """
        try:
            if self.use_gemini and self.gemini_client:
                return await self._analyze_with_gemini(title, content, category)
            else:
                return self._analyze_fallback(title, content, category)

        except Exception as e:
            logger.error(f"[ContextualAnalyzer] Erro na análise: {e}", exc_info=True)
            return self._analyze_fallback(title, content, category)

    async def _analyze_with_gemini(
        self,
        title: str,
        content: str,
        category: Optional[str] = None
    ) -> ContextualAnalysisResult:
        """
        Análise contextual usando Gemini.
        """
        # Truncar conteúdo se necessário
        content_truncated = content[:self.MAX_CONTENT_LENGTH] if len(content) > self.MAX_CONTENT_LENGTH else content

        # Montar prompt de análise
        analysis_prompt = self.ANALYSIS_PROMPT_TEMPLATE.format(
            title=title,
            content=content_truncated
        )

        logger.info(f"[ContextualAnalyzer] Analisando: {title[:60]}...")

        # Chamar Gemini para análise
        response = await self.gemini_client.aio.models.generate_content(
            model=self.GEMINI_TEXT_MODEL,
            contents=analysis_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,  # Baixa temperatura para respostas consistentes
            )
        )

        # Extrair e parsear resposta
        response_text = response.text if hasattr(response, 'text') else str(response)

        # Limpar possíveis marcadores de código
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            analysis_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.warning(f"[ContextualAnalyzer] Erro ao parsear JSON: {e}")
            logger.debug(f"[ContextualAnalyzer] Resposta raw: {response_text[:500]}")
            return self._analyze_fallback(title, content, category)

        # Converter para dataclass
        result = ContextualAnalysisResult(
            story_summary=analysis_data.get('story_summary', ''),
            visual_concept=analysis_data.get('visual_concept', ''),
            key_visual_elements=analysis_data.get('key_visual_elements', []),
            people=analysis_data.get('people', []),
            institutions=analysis_data.get('institutions', []),
            cryptocurrencies=analysis_data.get('cryptocurrencies', []),
            specific_event=analysis_data.get('specific_event'),
            geographic_location=analysis_data.get('geographic_location'),
            numeric_data=analysis_data.get('numeric_data', []),
            tone=self._parse_tone(analysis_data.get('tone', 'neutral')),
            importance=analysis_data.get('importance', 'standard'),
            contextual_elements=analysis_data.get('contextual_elements', []),
            is_generic_context=analysis_data.get('is_generic_context', False),
            confidence_score=0.85,
            analyzer_version="contextual-v1.0-gemini"
        )

        logger.info(
            f"[ContextualAnalyzer] Análise completa: "
            f"story='{result.story_summary[:50]}...', "
            f"cryptos={result.cryptocurrencies}, "
            f"institutions={result.institutions[:3]}, "
            f"tone={result.tone.value}, "
            f"is_generic={result.is_generic_context}"
        )

        return result

    def _parse_tone(self, tone_str: str) -> ContextualTone:
        """Converte string de tom para enum"""
        tone_map = {
            'positive': ContextualTone.POSITIVE,
            'positive-historic': ContextualTone.POSITIVE_HISTORIC,
            'negative': ContextualTone.NEGATIVE,
            'negative-urgent': ContextualTone.NEGATIVE_URGENT,
            'neutral': ContextualTone.NEUTRAL,
            'analytical': ContextualTone.ANALYTICAL,
        }
        return tone_map.get(tone_str.lower(), ContextualTone.NEUTRAL)

    def _analyze_fallback(
        self,
        title: str,
        content: str,
        category: Optional[str] = None
    ) -> ContextualAnalysisResult:
        """
        Análise de fallback usando heurísticas simples quando Gemini não está disponível.

        Este é um fallback básico que tenta extrair contexto usando patterns.
        NÃO é tão preciso quanto a análise via IA.
        """
        logger.warning("[ContextualAnalyzer] Usando fallback heurístico (Gemini indisponível)")

        full_text = f"{title} {content}".lower()

        # Extrair criptomoedas mencionadas
        cryptos = self._extract_cryptos_from_text(full_text)

        # Extrair instituições mencionadas
        institutions = self._extract_institutions_from_text(full_text)

        # Extrair pessoas mencionadas (básico)
        people = self._extract_people_from_text(full_text)

        # Detectar se é contexto genérico
        is_generic = self._detect_generic_context(title.lower())

        # Detectar tom
        tone = self._detect_tone(title.lower())

        # Extrair dados numéricos
        numeric_data = self._extract_numeric_data(title)

        return ContextualAnalysisResult(
            story_summary=title,  # Fallback usa o título como resumo
            visual_concept=f"News visualization about {', '.join(cryptos) if cryptos else 'cryptocurrency market'}",
            key_visual_elements=[
                f"Professional {category or 'crypto'} themed photography",
                "Clean editorial composition",
                "Financial news aesthetic",
            ],
            people=people,
            institutions=institutions,
            cryptocurrencies=cryptos if not is_generic else ['diverse cryptocurrencies'],
            specific_event=None,
            geographic_location=None,
            numeric_data=numeric_data,
            tone=tone,
            importance='standard',
            contextual_elements=[],
            is_generic_context=is_generic,
            confidence_score=0.5,  # Baixa confiança para fallback
            analyzer_version="contextual-v1.0-fallback"
        )

    def _extract_cryptos_from_text(self, text: str) -> List[str]:
        """Extrai criptomoedas mencionadas no texto"""
        crypto_patterns = {
            'bitcoin': ['bitcoin', 'btc'],
            'ethereum': ['ethereum', 'eth', 'ether'],
            'solana': ['solana', 'sol'],
            'cardano': ['cardano', 'ada'],
            'xrp': ['xrp', 'ripple'],
            'dogecoin': ['dogecoin', 'doge'],
            'polkadot': ['polkadot', 'dot'],
            'litecoin': ['litecoin', 'ltc'],
            'avalanche': ['avalanche', 'avax'],
            'chainlink': ['chainlink', 'link'],
        }

        found = []
        for crypto, patterns in crypto_patterns.items():
            for pattern in patterns:
                if re.search(rf'\b{pattern}\b', text, re.IGNORECASE):
                    if crypto.capitalize() not in found:
                        found.append(crypto.capitalize())
                    break

        return found

    def _extract_institutions_from_text(self, text: str) -> List[str]:
        """Extrai instituições mencionadas no texto"""
        institutions_map = {
            'sec': 'SEC',
            'cftc': 'CFTC',
            'fed': 'Federal Reserve',
            'federal reserve': 'Federal Reserve',
            'blackrock': 'BlackRock',
            'jpmorgan': 'JPMorgan',
            'jp morgan': 'JPMorgan',
            'goldman sachs': 'Goldman Sachs',
            'fidelity': 'Fidelity',
            'grayscale': 'Grayscale',
            'binance': 'Binance',
            'coinbase': 'Coinbase',
            'nyse': 'NYSE',
            'nasdaq': 'NASDAQ',
            'tesla': 'Tesla',
            'microstrategy': 'MicroStrategy',
        }

        found = []
        for pattern, display_name in institutions_map.items():
            if re.search(rf'\b{pattern}\b', text, re.IGNORECASE):
                if display_name not in found:
                    found.append(display_name)

        return found

    def _extract_people_from_text(self, text: str) -> List[str]:
        """Extrai pessoas mencionadas no texto (básico)"""
        people_patterns = {
            'gary gensler': 'Gary Gensler',
            'gensler': 'Gary Gensler',
            'elon musk': 'Elon Musk',
            'michael saylor': 'Michael Saylor',
            'vitalik buterin': 'Vitalik Buterin',
            'vitalik': 'Vitalik Buterin',
            'changpeng zhao': 'CZ (Changpeng Zhao)',
            'cz': 'CZ',
            'cathie wood': 'Cathie Wood',
            'jerome powell': 'Jerome Powell',
            'larry fink': 'Larry Fink',
        }

        found = []
        for pattern, display_name in people_patterns.items():
            if re.search(rf'\b{pattern}\b', text, re.IGNORECASE):
                if display_name not in found:
                    found.append(display_name)

        return found

    def _detect_generic_context(self, title: str) -> bool:
        """Detecta se o título é sobre criptomoedas de forma genérica"""
        generic_patterns = [
            r'\baltcoins?\b',
            r'\bcriptomoedas?\b',
            r'\bmercado\s+cripto\b',
            r'\bcrypto\s+market\b',
            r'\bcryptocurrenc(y|ies)\b',
            r'\bativos\s+digitais\b',
        ]

        for pattern in generic_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return True

        return False

    def _detect_tone(self, title: str) -> ContextualTone:
        """Detecta o tom da notícia"""
        positive_words = ['sobe', 'alta', 'recorde', 'dispara', 'aprovado', 'sucesso', 'lança']
        negative_words = ['cai', 'queda', 'despenca', 'alerta', 'risco', 'hack', 'processo']

        positive_count = sum(1 for w in positive_words if w in title)
        negative_count = sum(1 for w in negative_words if w in title)

        if 'histórico' in title or 'primeiro' in title:
            return ContextualTone.POSITIVE_HISTORIC if positive_count >= negative_count else ContextualTone.NEUTRAL
        elif positive_count > negative_count:
            return ContextualTone.POSITIVE
        elif negative_count > positive_count:
            return ContextualTone.NEGATIVE

        return ContextualTone.NEUTRAL

    def _extract_numeric_data(self, text: str) -> List[str]:
        """Extrai dados numéricos do texto"""
        patterns = [
            r'\d+[\.,]?\d*\s*%',  # Percentagens
            r'\$\s*\d+[\.,]?\d*\s*(mil|milhão|milhões|bilhão|bilhões|k|m|b)?',  # Preços USD
            r'US\$\s*\d+[\.,]?\d*',  # Preços US$
            r'\d+\s*(horas?|dias?|semanas?|meses?)',  # Tempo
        ]

        found = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = ''.join(match)
                if match and match not in found:
                    found.append(match)

        return found[:5]  # Limitar a 5 itens


# Singleton para uso global
contextual_image_analyzer = ContextualImageAnalyzer()
