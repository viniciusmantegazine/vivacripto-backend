"""
Testes unitários para o sistema de geração de imagens v4.0/v10.0 - Contextual AI Analysis

Testa:
- ContextualImageAnalyzer: análise contextual profunda via IA
- ContextualPromptBuilder: construção de prompts narrativos
- SmartPromptGenerator v4.0: integração com análise contextual
- Fallback para modo legacy quando IA não disponível

NOVIDADE v4.0/v10.0:
O sistema agora usa o CONTEÚDO COMPLETO da notícia para gerar prompts
que CONTAM A HISTÓRIA visualmente, não apenas mostram logos genéricos.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from app.services.ai.contextual_image_analyzer import (
    ContextualImageAnalyzer,
    ContextualAnalysisResult,
    ContextualTone,
)
from app.services.ai.contextual_prompt_builder import (
    ContextualPromptBuilder,
)
from app.services.ai.smart_prompt_generator import SmartPromptGenerator


class TestContextualImageAnalyzer:
    """Testes para o analisador contextual via IA"""

    @pytest.fixture
    def analyzer(self):
        return ContextualImageAnalyzer()

    # === Testes de Fallback (quando Gemini não disponível) ===

    def test_fallback_extracts_cryptos_from_text(self, analyzer):
        """Fallback deve extrair criptomoedas do texto"""
        text = "Bitcoin e Ethereum estão em alta. Solana também subiu."
        cryptos = analyzer._extract_cryptos_from_text(text.lower())

        assert 'Bitcoin' in cryptos
        assert 'Ethereum' in cryptos
        assert 'Solana' in cryptos

    def test_fallback_extracts_institutions_from_text(self, analyzer):
        """Fallback deve extrair instituições do texto"""
        text = "A SEC aprovou o ETF da BlackRock após análise do JPMorgan."
        institutions = analyzer._extract_institutions_from_text(text.lower())

        assert 'SEC' in institutions
        assert 'BlackRock' in institutions
        assert 'JPMorgan' in institutions

    def test_fallback_extracts_people_from_text(self, analyzer):
        """Fallback deve extrair pessoas do texto"""
        text = "Gary Gensler anunciou a decisão. Elon Musk comentou no Twitter."
        people = analyzer._extract_people_from_text(text.lower())

        assert 'Gary Gensler' in people
        assert 'Elon Musk' in people

    def test_fallback_detects_generic_context(self, analyzer):
        """Fallback deve detectar contexto genérico"""
        assert analyzer._detect_generic_context("altcoins sobem 15%") is True
        assert analyzer._detect_generic_context("criptomoedas em alta") is True
        assert analyzer._detect_generic_context("mercado cripto aquece") is True
        assert analyzer._detect_generic_context("bitcoin sobe 15%") is False
        assert analyzer._detect_generic_context("ethereum atinge recorde") is False

    def test_fallback_detects_positive_tone(self, analyzer):
        """Fallback deve detectar tom positivo"""
        assert analyzer._detect_tone("bitcoin sobe 20%") == ContextualTone.POSITIVE
        assert analyzer._detect_tone("eth atinge recorde histórico") == ContextualTone.POSITIVE_HISTORIC
        assert analyzer._detect_tone("criptomoedas disparam") == ContextualTone.POSITIVE

    def test_fallback_detects_negative_tone(self, analyzer):
        """Fallback deve detectar tom negativo"""
        assert analyzer._detect_tone("bitcoin despenca 15%") == ContextualTone.NEGATIVE
        assert analyzer._detect_tone("alerta sobre riscos no mercado") == ContextualTone.NEGATIVE
        # "crash" precisa estar com palavra negativa conhecida no fallback
        assert analyzer._detect_tone("queda no mercado cripto") == ContextualTone.NEGATIVE

    def test_fallback_extracts_numeric_data(self, analyzer):
        """Fallback deve extrair dados numéricos"""
        text = "Bitcoin subiu 15% e agora vale $52.000. Volume de 24 horas é recorde."
        numeric = analyzer._extract_numeric_data(text)

        assert any('15%' in n or '15 %' in n for n in numeric)
        # Verifica se captura pelo menos valor em dólar ou período de tempo
        assert len(numeric) >= 1

    @pytest.mark.asyncio
    async def test_fallback_analysis_returns_valid_result(self, analyzer):
        """Análise fallback deve retornar resultado válido"""
        # Forçar fallback desabilitando Gemini
        analyzer.use_gemini = False

        result = await analyzer.analyze(
            title="Bitcoin atinge US$ 100.000 após aprovação de ETF",
            content="O Bitcoin atingiu recorde histórico após SEC aprovar ETF. BlackRock lidera.",
            category="bitcoin"
        )

        assert isinstance(result, ContextualAnalysisResult)
        assert result.analyzer_version == "contextual-v1.0-fallback"
        assert result.confidence_score == 0.5  # Baixa confiança para fallback
        assert 'Bitcoin' in result.cryptocurrencies or 'diverse cryptocurrencies' in result.cryptocurrencies


class TestContextualPromptBuilder:
    """Testes para o construtor de prompts narrativos"""

    @pytest.fixture
    def builder(self):
        return ContextualPromptBuilder()

    @pytest.fixture
    def sample_analysis(self):
        """Análise de exemplo para testes"""
        return ContextualAnalysisResult(
            story_summary="SEC aprova primeiro ETF de Bitcoin à vista dos EUA, gerenciado pela BlackRock",
            visual_concept="Momento histórico de aprovação regulatória com elementos institucionais",
            key_visual_elements=[
                "SEC official approval document",
                "Gary Gensler at announcement",
                "BlackRock corporate branding",
                "NYSE trading floor celebration",
                "Bitcoin golden coin prominent"
            ],
            people=["Gary Gensler"],
            institutions=["SEC", "BlackRock", "NYSE"],
            cryptocurrencies=["Bitcoin"],
            specific_event="Aprovação do primeiro ETF spot de Bitcoin nos EUA",
            geographic_location="Estados Unidos",
            numeric_data=["15%", "$52.000"],
            tone=ContextualTone.POSITIVE_HISTORIC,
            importance="breaking",
            contextual_elements=["Investidores comemoram", "Mercado em alta"],
            is_generic_context=False,
            confidence_score=0.9,
            analyzer_version="contextual-v1.0-test"
        )

    def test_build_prompt_returns_string(self, builder, sample_analysis):
        """Build prompt deve retornar string válida"""
        prompt = builder.build_prompt(sample_analysis)

        assert isinstance(prompt, str)
        assert len(prompt) > 200

    def test_build_prompt_includes_protection(self, builder, sample_analysis):
        """Prompt deve incluir proteção anti-watermark"""
        prompt = builder.build_prompt(sample_analysis)
        prompt_lower = prompt.lower()

        assert "no watermarks" in prompt_lower
        assert "original" in prompt_lower

    def test_build_prompt_includes_story_context(self, builder, sample_analysis):
        """Prompt deve incluir contexto da história"""
        prompt = builder.build_prompt(sample_analysis)

        assert "SEC" in prompt
        assert "Bitcoin" in prompt

    def test_build_prompt_includes_visual_elements(self, builder, sample_analysis):
        """Prompt deve incluir elementos visuais chave"""
        prompt = builder.build_prompt(sample_analysis)

        # Pelo menos alguns dos elementos chave devem estar presentes
        assert "BlackRock" in prompt or "NYSE" in prompt

    def test_build_prompt_includes_tone(self, builder, sample_analysis):
        """Prompt deve incluir tom apropriado"""
        prompt = builder.build_prompt(sample_analysis)
        prompt_lower = prompt.lower()

        # Para tom positivo-histórico, deve ter atmosfera celebratória
        assert "historic" in prompt_lower or "milestone" in prompt_lower or "triumphant" in prompt_lower

    def test_build_prompt_includes_crypto_restriction(self, builder, sample_analysis):
        """Prompt deve incluir restrição de criptos quando específico"""
        prompt = builder.build_prompt(sample_analysis)
        prompt_lower = prompt.lower()

        # Deve ter instrução para mostrar APENAS Bitcoin
        assert "only" in prompt_lower and "bitcoin" in prompt_lower

    def test_build_prompt_with_metadata(self, builder, sample_analysis):
        """Build prompt com metadata deve retornar dict completo"""
        result = builder.build_prompt_with_metadata(sample_analysis)

        assert 'prompt' in result
        assert 'metadata' in result
        assert 'story_summary' in result['metadata']
        assert 'cryptocurrencies' in result['metadata']
        assert 'tone' in result['metadata']

    def test_build_prompt_for_generic_context(self, builder):
        """Prompt para contexto genérico deve mostrar múltiplas criptos"""
        generic_analysis = ContextualAnalysisResult(
            story_summary="Mercado de altcoins em alta no trimestre",
            visual_concept="Diversidade de criptomoedas em valorização",
            key_visual_elements=["Multiple crypto symbols", "Market growth"],
            people=[],
            institutions=[],
            cryptocurrencies=["diverse cryptocurrencies"],
            specific_event=None,
            geographic_location=None,
            numeric_data=["15%"],
            tone=ContextualTone.POSITIVE,
            importance="standard",
            contextual_elements=[],
            is_generic_context=True,
            confidence_score=0.7,
            analyzer_version="contextual-v1.0-test"
        )

        prompt = builder.build_prompt(generic_analysis)
        prompt_lower = prompt.lower()

        # Para contexto genérico, deve ter múltiplas criptos
        assert "multiple" in prompt_lower or "diverse" in prompt_lower


class TestSmartPromptGeneratorContextual:
    """Testes para SmartPromptGenerator v4.0 com análise contextual"""

    @pytest.fixture
    def generator(self):
        return SmartPromptGenerator()

    # === Testes de Métodos Legacy (Sync) ===

    def test_legacy_generate_prompt_returns_string(self, generator):
        """Método legacy deve continuar funcionando"""
        prompt = generator.generate_prompt(
            title="Bitcoin atinge US$ 50.000",
            content="O preço do Bitcoin subiu 10% nas últimas 24 horas.",
            category="bitcoin"
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_legacy_generate_prompt_with_metadata(self, generator):
        """Método legacy com metadata deve continuar funcionando"""
        result = generator.generate_prompt_with_metadata(
            title="Ethereum lança atualização",
            content="A rede Ethereum recebeu nova atualização.",
            category="ethereum"
        )

        assert 'prompt' in result
        assert 'metadata' in result
        assert result['metadata']['entity_type'] == 'crypto'

    # === Testes de Métodos Contextuais (Async) ===

    @pytest.mark.asyncio
    async def test_contextual_generate_prompt_returns_string(self, generator):
        """Método contextual deve retornar string válida"""
        # Mock do analyzer para evitar chamada real ao Gemini
        mock_analysis = ContextualAnalysisResult(
            story_summary="Bitcoin atinge recorde histórico",
            visual_concept="Celebração do marco de preço",
            key_visual_elements=["Bitcoin golden coin", "Price chart"],
            people=[],
            institutions=[],
            cryptocurrencies=["Bitcoin"],
            specific_event="Novo recorde de preço",
            geographic_location=None,
            numeric_data=["$50.000"],
            tone=ContextualTone.POSITIVE,
            importance="major",
            contextual_elements=[],
            is_generic_context=False,
            confidence_score=0.8,
            analyzer_version="contextual-v1.0-test"
        )

        with patch.object(generator.contextual_analyzer, 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_analysis

            prompt = await generator.generate_prompt_contextual(
                title="Bitcoin atinge US$ 50.000",
                content="O Bitcoin atingiu a marca de $50.000 pela primeira vez.",
                category="bitcoin"
            )

            assert isinstance(prompt, str)
            assert len(prompt) > 100
            mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_contextual_generate_prompt_with_metadata(self, generator):
        """Método contextual com metadata deve retornar dict completo"""
        mock_analysis = ContextualAnalysisResult(
            story_summary="SEC aprova ETF de Bitcoin",
            visual_concept="Aprovação regulatória histórica",
            key_visual_elements=["SEC seal", "Bitcoin coin"],
            people=["Gary Gensler"],
            institutions=["SEC"],
            cryptocurrencies=["Bitcoin"],
            specific_event="ETF approval",
            geographic_location="Estados Unidos",
            numeric_data=[],
            tone=ContextualTone.POSITIVE_HISTORIC,
            importance="breaking",
            contextual_elements=[],
            is_generic_context=False,
            confidence_score=0.9,
            analyzer_version="contextual-v1.0-test"
        )

        with patch.object(generator.contextual_analyzer, 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_analysis

            result = await generator.generate_prompt_with_metadata_contextual(
                title="SEC aprova ETF de Bitcoin",
                content="A SEC aprovou oficialmente o primeiro ETF de Bitcoin à vista.",
                category="bitcoin"
            )

            assert 'prompt' in result
            assert 'metadata' in result
            assert result['metadata']['tone'] == 'positive-historic'
            assert 'Bitcoin' in result['metadata']['cryptocurrencies']

    @pytest.mark.asyncio
    async def test_contextual_fallback_to_legacy_on_error(self, generator):
        """Deve fazer fallback para legacy se análise contextual falhar"""
        with patch.object(generator.contextual_analyzer, 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = Exception("Gemini API error")

            # Não deve lançar exceção, deve fazer fallback
            prompt = await generator.generate_prompt_contextual(
                title="Bitcoin sobe 10%",
                content="O Bitcoin valorizou nas últimas horas.",
                category="bitcoin"
            )

            assert isinstance(prompt, str)
            assert len(prompt) > 100


class TestContextualAnalysisIntegration:
    """Testes de integração do sistema contextual"""

    @pytest.fixture
    def analyzer(self):
        return ContextualImageAnalyzer()

    @pytest.fixture
    def builder(self):
        return ContextualPromptBuilder()

    def test_full_pipeline_with_fallback(self, analyzer, builder):
        """Teste do pipeline completo usando fallback"""
        # Forçar fallback
        analyzer.use_gemini = False

        import asyncio

        async def run_test():
            # Analisar
            analysis = await analyzer.analyze(
                title="SEC aprova ETF de Bitcoin após BlackRock pressionar",
                content="""
                A SEC finalmente aprovou o primeiro ETF de Bitcoin à vista dos EUA.
                A decisão veio após intensa pressão da BlackRock e outras gestoras.
                Gary Gensler, presidente da SEC, anunciou a aprovação em comunicado oficial.
                O mercado reagiu positivamente, com o Bitcoin subindo 15% para $52.000.
                A NYSE começará a negociar o ETF na próxima semana.
                """,
                category="bitcoin"
            )

            # Verificar análise
            assert 'Bitcoin' in analysis.cryptocurrencies or 'diverse cryptocurrencies' in analysis.cryptocurrencies
            assert any('SEC' in i or 'BlackRock' in i for i in analysis.institutions)
            assert analysis.is_generic_context is False

            # Construir prompt
            prompt = builder.build_prompt(analysis)

            # Verificar prompt
            assert len(prompt) > 200
            assert "bitcoin" in prompt.lower()
            assert "no watermarks" in prompt.lower()

            return prompt

        prompt = asyncio.run(run_test())
        assert isinstance(prompt, str)

    def test_generic_context_detection_and_prompt(self, analyzer, builder):
        """Teste de detecção de contexto genérico"""
        # Forçar fallback
        analyzer.use_gemini = False

        import asyncio

        async def run_test():
            analysis = await analyzer.analyze(
                title="Altcoins: 2026 marca virada para mercados 24/7",
                content="O mercado de criptomoedas está mudando com novos horários de negociação.",
                category="altcoins"
            )

            # Deve ser detectado como genérico
            assert analysis.is_generic_context is True

            # Prompt deve ter múltiplas criptos
            prompt = builder.build_prompt(analysis)
            prompt_lower = prompt.lower()

            assert "multiple" in prompt_lower or "diverse" in prompt_lower

            return prompt

        prompt = asyncio.run(run_test())
        assert isinstance(prompt, str)


class TestRealWorldCases:
    """
    Testes com casos reais que causavam problemas no sistema antigo

    Estes testes verificam que o novo sistema contextual resolve
    os problemas identificados onde imagens não correspondiam ao título.
    """

    @pytest.fixture
    def generator(self):
        return SmartPromptGenerator()

    def test_altcoins_2026_case(self, generator):
        """
        CASO REAL: "Altcoins: 2026 marca virada para mercados 24/7"
        PROBLEMA ANTIGO: Gerava imagem de Cardano ADA
        ESPERADO: Múltiplas criptos ou conceito de mercado
        """
        result = generator.generate_prompt_with_metadata(
            title="Altcoins: 2026 marca virada para mercados 24/7",
            content="O mercado de criptomoedas muda com novos horários de negociação.",
            category=None
        )

        # Deve ser genérico
        assert result['metadata']['is_generic_context'] is True
        # Entity não deve ser uma cripto específica
        assert result['metadata']['primary_entity'] == 'altcoins' or result['metadata']['entity_type'] == 'theme'

    def test_sec_etf_approval_case(self, generator):
        """
        CASO: "SEC aprova ETF de Bitcoin"
        ESPERADO: Bitcoin como entidade principal, SEC como secundária
        """
        result = generator.generate_prompt_with_metadata(
            title="SEC aprova ETF de Bitcoin",
            content="A SEC aprovou o primeiro ETF de Bitcoin após anos de espera.",
            category="bitcoin"
        )

        # Bitcoin deve ser a entidade principal
        assert result['metadata']['primary_entity'] == 'bitcoin'
        # Não deve ser genérico
        assert result['metadata']['is_generic_context'] is False

    def test_criptomoedas_generic_case(self, generator):
        """
        CASO: "Criptomoedas ganham espaço na regulação europeia"
        ESPERADO: Contexto genérico, não uma cripto específica
        """
        result = generator.generate_prompt_with_metadata(
            title="Criptomoedas ganham espaço na regulação europeia",
            content="A União Europeia avança com framework MiCA para criptoativos.",
            category=None
        )

        # Deve ser genérico
        assert result['metadata']['is_generic_context'] is True
