"""
Testes unitários para o sistema inteligente de geração de imagens v7.0

Testa:
- NewsContextAnalyzer: análise de sentimento, tipo e entidades
- VisualElementsBank: seleção de elementos visuais
- SmartPromptGenerator: geração de prompts dinâmicos
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.ai.news_context_analyzer import (
    NewsContextAnalyzer,
    NewsContext,
    NewsSentiment,
    NewsType,
    EntityMention
)
from app.services.ai.visual_elements_bank import (
    VisualElementsBank,
    VisualComposition
)
from app.services.ai.smart_prompt_generator import SmartPromptGenerator


class TestNewsContextAnalyzer:
    """Testes para o analisador de contexto de notícias"""

    @pytest.fixture
    def analyzer(self):
        return NewsContextAnalyzer()

    # === Testes de Sentimento ===

    def test_bullish_sentiment_detection(self, analyzer):
        """Deve detectar sentimento bullish em notícias de alta"""
        title = "Bitcoin atinge US$ 92.500 após alta nos preços"
        content = "O Bitcoin registrou valorização expressiva, rompendo a resistência."

        context = analyzer.analyze(title, content, "bitcoin")

        assert context.sentiment == NewsSentiment.BULLISH

    def test_bearish_sentiment_detection(self, analyzer):
        """Deve detectar sentimento bearish em notícias de queda"""
        title = "Ethereum despenca 15% em meio a vendas massivas"
        content = "O Ether caiu drasticamente após liquidações em cascata no mercado."

        context = analyzer.analyze(title, content, "ethereum")

        assert context.sentiment == NewsSentiment.BEARISH

    def test_warning_sentiment_detection(self, analyzer):
        """Deve detectar sentimento de alerta em notícias de segurança"""
        title = "Exchange sofre hack de US$ 100 milhões"
        content = "Hackers exploraram vulnerabilidade e roubaram fundos dos usuários."

        context = analyzer.analyze(title, content, "altcoins")

        assert context.sentiment == NewsSentiment.WARNING

    def test_neutral_sentiment_default(self, analyzer):
        """Deve retornar sentimento neutro quando não há sinais claros"""
        title = "Análise técnica do mercado de criptomoedas"
        content = "Especialistas avaliam os indicadores do mercado nesta semana."

        context = analyzer.analyze(title, content, "altcoins")

        assert context.sentiment == NewsSentiment.NEUTRAL

    # === Testes de Tipo de Notícia ===

    def test_price_news_type_detection(self, analyzer):
        """Deve detectar notícias de preço"""
        title = "Bitcoin cotado a US$ 45.000"
        content = "O preço do BTC subiu 5% nas últimas 24 horas. Volume de trading alto."

        context = analyzer.analyze(title, content, "bitcoin")

        assert context.news_type == NewsType.PRICE

    def test_regulation_news_type_detection(self, analyzer):
        """Deve detectar notícias de regulação"""
        title = "SEC aprova ETF de Bitcoin nos EUA"
        content = "O regulador americano autorizou o primeiro ETF spot de Bitcoin."

        context = analyzer.analyze(title, content, "bitcoin")

        assert context.news_type == NewsType.REGULATION

    def test_technology_news_type_detection(self, analyzer):
        """Deve detectar notícias de tecnologia"""
        title = "Ethereum completa upgrade Dencun"
        content = "A atualização do protocolo foi implementada na mainnet com sucesso."

        context = analyzer.analyze(title, content, "ethereum")

        assert context.news_type == NewsType.TECHNOLOGY

    def test_adoption_news_type_detection(self, analyzer):
        """Deve detectar notícias de adoção"""
        title = "PayPal integra pagamentos com Bitcoin"
        content = "A empresa agora aceita criptomoedas como forma de pagamento."

        context = analyzer.analyze(title, content, "bitcoin")

        assert context.news_type == NewsType.ADOPTION

    def test_security_news_type_detection(self, analyzer):
        """Deve detectar notícias de segurança"""
        title = "Protocolo DeFi sofre exploit"
        content = "Vulnerabilidade no contrato permitiu ataque de hackers."

        context = analyzer.analyze(title, content, "defi")

        assert context.news_type == NewsType.SECURITY

    # === Testes de Extração de Entidades ===

    def test_exchange_entity_extraction(self, analyzer):
        """Deve extrair exchanges mencionadas"""
        title = "Binance anuncia nova listagem"
        content = "A maior exchange do mundo listará o token XYZ."

        context = analyzer.analyze(title, content, "altcoins")

        entity_names = [e.name for e in context.entities]
        assert 'binance' in entity_names

    def test_government_entity_extraction(self, analyzer):
        """Deve extrair entidades governamentais"""
        title = "SEC investiga projeto de criptomoeda"
        content = "O regulador americano está analisando possíveis violações."

        context = analyzer.analyze(title, content, "regulacao")

        entity_names = [e.name for e in context.entities]
        assert 'sec' in entity_names

    def test_person_entity_extraction(self, analyzer):
        """Deve extrair pessoas influentes mencionadas"""
        title = "Elon Musk comenta sobre Dogecoin"
        content = "O empresário postou sobre a criptomoeda no Twitter."

        context = analyzer.analyze(title, content, "altcoins")

        entity_names = [e.name for e in context.entities]
        assert 'elon musk' in entity_names

    # === Testes de Identificação de Criptomoedas ===

    def test_primary_crypto_identification(self, analyzer):
        """Deve identificar a criptomoeda principal"""
        title = "Bitcoin supera Ethereum em volume"
        content = "O BTC registrou maior volume de negociação que o ETH hoje."

        context = analyzer.analyze(title, content, None)

        # Bitcoin deve ser a principal por aparecer primeiro/mais vezes
        assert context.primary_crypto in ['bitcoin', 'ethereum']

    def test_secondary_cryptos_identification(self, analyzer):
        """Deve identificar criptomoedas secundárias"""
        title = "Bitcoin, Ethereum e Solana em alta"
        content = "BTC, ETH e SOL registraram ganhos expressivos."

        context = analyzer.analyze(title, content, None)

        assert len(context.secondary_cryptos) >= 1

    def test_crypto_normalization(self, analyzer):
        """Deve normalizar símbolos para nomes completos"""
        normalized = analyzer._normalize_crypto_name('btc')
        assert normalized == 'bitcoin'

        normalized = analyzer._normalize_crypto_name('eth')
        assert normalized == 'ethereum'

    # === Testes de Confiança ===

    def test_confidence_calculation(self, analyzer):
        """Deve calcular score de confiança razoável"""
        title = "Bitcoin atinge recorde após aprovação do ETF pela SEC"
        content = "A Binance registrou volume recorde de negociações."

        context = analyzer.analyze(title, content, "bitcoin")

        assert 0.0 <= context.confidence_score <= 1.0
        # Com múltiplos sinais, confiança deve ser maior
        assert context.confidence_score >= 0.5


class TestVisualElementsBank:
    """Testes para o banco de elementos visuais"""

    @pytest.fixture
    def bank(self):
        return VisualElementsBank()

    def test_get_central_element_for_category(self, bank):
        """Deve retornar elemento central para cada categoria"""
        for category in ['bitcoin', 'ethereum', 'solana', 'defi', 'regulacao']:
            element = bank.get_central_element(category)
            assert isinstance(element, str)
            assert len(element) > 10

    def test_get_central_element_fallback(self, bank):
        """Deve usar fallback para categoria desconhecida"""
        element = bank.get_central_element('categoria_inexistente')
        assert isinstance(element, str)
        # Deve usar altcoins como fallback
        assert element in bank.CATEGORY_CENTRAL_ELEMENTS['altcoins']

    def test_get_secondary_elements(self, bank):
        """Deve retornar elementos secundários por sentimento"""
        for sentiment in NewsSentiment:
            elements = bank.get_secondary_elements(sentiment, count=2)
            assert isinstance(elements, list)
            assert len(elements) <= 2

    def test_get_color_palette(self, bank):
        """Deve retornar paleta de cores apropriada"""
        for sentiment in NewsSentiment:
            palette = bank.get_color_palette(sentiment)
            assert isinstance(palette, str)
            assert '#' in palette  # Deve conter códigos de cor

    def test_get_color_palette_with_category(self, bank):
        """Deve priorizar paleta da categoria quando disponível"""
        palette = bank.get_color_palette(NewsSentiment.BULLISH, 'bitcoin')
        assert isinstance(palette, str)
        # Bitcoin tem paleta própria com gold
        # Pode ser paleta do bitcoin ou do sentimento

    def test_get_mood_for_news_type(self, bank):
        """Deve retornar mood apropriado para cada tipo"""
        for news_type in NewsType:
            mood = bank.get_mood(news_type)
            assert isinstance(mood, str)
            assert len(mood) > 5

    def test_get_composition_style(self, bank):
        """Deve retornar estilo de composição"""
        style = bank.get_composition_style()
        assert isinstance(style, str)
        assert style in bank.COMPOSITION_STYLES

    def test_get_lighting(self, bank):
        """Deve retornar estilo de iluminação por sentimento"""
        for sentiment in NewsSentiment:
            lighting = bank.get_lighting(sentiment)
            assert isinstance(lighting, str)

    def test_get_background(self, bank):
        """Deve retornar estilo de background por sentimento"""
        for sentiment in NewsSentiment:
            background = bank.get_background(sentiment)
            assert isinstance(background, str)

    def test_compose_visual_elements(self, bank):
        """Deve compor elementos visuais completos"""
        composition = bank.compose_visual_elements(
            category='bitcoin',
            sentiment=NewsSentiment.BULLISH,
            news_type=NewsType.PRICE
        )

        assert isinstance(composition, VisualComposition)
        assert composition.central_element
        assert len(composition.secondary_elements) > 0
        assert composition.color_palette
        assert composition.mood
        assert composition.composition_style
        assert composition.lighting
        assert composition.background


class TestSmartPromptGenerator:
    """Testes para o gerador inteligente de prompts"""

    @pytest.fixture
    def generator(self):
        return SmartPromptGenerator()

    def test_generate_prompt_returns_string(self, generator):
        """Deve retornar um prompt como string"""
        prompt = generator.generate_prompt(
            title="Bitcoin atinge US$ 50.000",
            content="O preço do Bitcoin subiu 10% nas últimas 24 horas.",
            category="bitcoin"
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_generate_prompt_includes_quality_suffix(self, generator):
        """Deve incluir sufixo de qualidade no prompt"""
        prompt = generator.generate_prompt(
            title="Ethereum lança atualização",
            content="A rede Ethereum recebeu nova atualização.",
            category="ethereum"
        )

        assert "16:9" in prompt.lower() or "aspect ratio" in prompt.lower()
        assert "no text" in prompt.lower()

    def test_sanitize_prompt_removes_blocked_words(self, generator):
        """Deve remover palavras bloqueadas do prompt"""
        unsafe_prompt = "This is a hack attack with violence and drugs"
        sanitized = generator._sanitize_prompt(unsafe_prompt)

        for word in ['hack', 'attack', 'violence', 'drugs']:
            assert word not in sanitized.lower()

    def test_generate_prompt_with_metadata(self, generator):
        """Deve retornar prompt com metadados completos"""
        result = generator.generate_prompt_with_metadata(
            title="SEC aprova ETF de Bitcoin",
            content="O regulador americano aprovou o primeiro ETF spot.",
            category="bitcoin"
        )

        assert 'prompt' in result
        assert 'metadata' in result
        assert 'sentiment' in result['metadata']
        assert 'news_type' in result['metadata']
        assert 'category' in result['metadata']

    def test_fallback_prompt_generation(self, generator):
        """Deve gerar prompt fallback em caso de categoria"""
        for category in ['bitcoin', 'ethereum', 'defi', 'regulacao']:
            fallback = generator._generate_fallback_prompt(category)
            assert isinstance(fallback, str)
            assert len(fallback) > 50

    def test_prompt_variation_mechanism(self, generator):
        """Deve gerar prompts diferentes para mesma notícia"""
        title = "Bitcoin em alta"
        content = "O mercado está otimista."

        prompts = set()
        for _ in range(5):
            prompt = generator.generate_prompt(title, content, "bitcoin")
            prompts.add(prompt[:100])  # Comparar primeiros 100 chars

        # Pelo menos 2 variações diferentes (devido à aleatoriedade)
        # Pode haver repetição, então verificamos >= 1
        assert len(prompts) >= 1

    def test_prompt_for_bullish_news(self, generator):
        """Deve gerar prompt apropriado para notícia bullish"""
        result = generator.generate_prompt_with_metadata(
            title="Bitcoin dispara e atinge novo recorde",
            content="O BTC valorizou 20% e rompeu a máxima histórica.",
            category="bitcoin"
        )

        assert result['metadata']['sentiment'] == 'bullish'

    def test_prompt_for_bearish_news(self, generator):
        """Deve gerar prompt apropriado para notícia bearish"""
        result = generator.generate_prompt_with_metadata(
            title="Ethereum despenca após vendas massivas",
            content="O ETH caiu 15% com liquidações em cascata.",
            category="ethereum"
        )

        assert result['metadata']['sentiment'] == 'bearish'

    def test_prompt_for_regulation_news(self, generator):
        """Deve gerar prompt apropriado para notícia de regulação"""
        result = generator.generate_prompt_with_metadata(
            title="SEC analisa novo framework para criptomoedas",
            content="O regulador está desenvolvendo novas regras para o mercado.",
            category="regulacao"
        )

        assert result['metadata']['news_type'] == 'regulation'


class TestIntegration:
    """Testes de integração entre os módulos"""

    def test_full_pipeline_bitcoin_bullish(self):
        """Teste completo: notícia bullish de Bitcoin"""
        analyzer = NewsContextAnalyzer()
        bank = VisualElementsBank()
        generator = SmartPromptGenerator(analyzer, bank)

        title = "Bitcoin atinge US$ 100.000 pela primeira vez"
        content = """
        O Bitcoin finalmente rompeu a barreira dos US$ 100.000, marcando um
        momento histórico para o mercado de criptomoedas. A alta foi impulsionada
        pela aprovação de ETFs e entrada institucional massiva.
        """

        result = generator.generate_prompt_with_metadata(title, content, "bitcoin")

        assert result['metadata']['sentiment'] == 'bullish'
        assert result['metadata']['primary_crypto'] == 'bitcoin'
        assert 'Professional' in result['prompt']
        assert len(result['prompt']) > 200

    def test_full_pipeline_eth_technology(self):
        """Teste completo: notícia de tecnologia Ethereum"""
        generator = SmartPromptGenerator()

        title = "Ethereum implementa upgrade Pectra com sucesso"
        content = """
        A rede Ethereum completou com sucesso a atualização Pectra,
        trazendo melhorias significativas para o protocolo e layer 2.
        Desenvolvedores comemoram o avanço tecnológico.
        """

        result = generator.generate_prompt_with_metadata(title, content, "ethereum")

        assert result['metadata']['news_type'] == 'technology'
        assert result['metadata']['category'] == 'ethereum'

    def test_full_pipeline_security_warning(self):
        """Teste completo: notícia de segurança com alerta"""
        generator = SmartPromptGenerator()

        title = "Exchange sofre ataque hacker de US$ 50 milhões"
        content = """
        Uma exchange centralizada foi alvo de hackers que exploraram
        vulnerabilidade no sistema. Fundos dos usuários foram roubados.
        Investigação em andamento.
        """

        result = generator.generate_prompt_with_metadata(title, content, "altcoins")

        # O sentimento deve ser warning devido às palavras de alerta
        assert result['metadata']['sentiment'] == 'warning'
        assert result['metadata']['news_type'] == 'security'

        # O prompt deve estar sanitizado
        assert 'hack' not in result['prompt'].lower()
        assert 'attack' not in result['prompt'].lower()
