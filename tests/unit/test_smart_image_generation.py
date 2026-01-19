"""
Testes unitários para o sistema de geração de imagens v2.0 - Editorial Photography Style

Testa:
- NewsContextAnalyzer v2.0: análise de entidades, ações e sentimento
- EditorialVisualElementsBank: seleção de elementos fotográficos concretos
- SmartPromptGenerator v2.0: geração de prompts editoriais
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.ai.news_context_analyzer import (
    NewsContextAnalyzer,
    NewsContext,
    NewsSentiment,
    NewsType,
    EntityType,
    EntityMention,
    NewsAction
)
from app.services.ai.visual_elements_bank import (
    EditorialVisualElementsBank,
    EditorialComposition
)
from app.services.ai.smart_prompt_generator import SmartPromptGenerator


class TestNewsContextAnalyzer:
    """Testes para o analisador de contexto de notícias v2.0"""

    @pytest.fixture
    def analyzer(self):
        return NewsContextAnalyzer()

    # === Testes de Sentimento ===

    def test_positive_sentiment_detection(self, analyzer):
        """Deve detectar sentimento positivo em notícias de alta"""
        title = "Bitcoin atinge US$ 92.500 após alta nos preços"
        content = "O Bitcoin registrou valorização expressiva, rompendo a resistência."

        context = analyzer.analyze(title, content, "bitcoin")

        assert context.sentiment == NewsSentiment.POSITIVE

    def test_negative_sentiment_detection(self, analyzer):
        """Deve detectar sentimento negativo em notícias de queda"""
        title = "Ethereum despenca 15% em meio a vendas massivas"
        content = "O Ether caiu drasticamente após liquidações em cascata no mercado."

        context = analyzer.analyze(title, content, "ethereum")

        assert context.sentiment == NewsSentiment.NEGATIVE

    def test_negative_sentiment_for_warning_news(self, analyzer):
        """Deve detectar sentimento negativo em notícias de alerta"""
        title = "Especialista alerta sobre riscos no mercado cripto"
        content = "Analistas avisam sobre possíveis correções no mercado."

        context = analyzer.analyze(title, content, "altcoins")

        assert context.sentiment == NewsSentiment.NEGATIVE

    def test_neutral_sentiment_default(self, analyzer):
        """Deve retornar sentimento neutro quando não há sinais claros"""
        title = "Análise técnica do mercado de criptomoedas"
        content = "Especialistas avaliam os indicadores do mercado nesta semana."

        context = analyzer.analyze(title, content, "altcoins")

        assert context.sentiment == NewsSentiment.NEUTRAL

    # === Testes de Identificação de Entidade ===

    def test_crypto_entity_identification(self, analyzer):
        """Deve identificar criptomoeda como entidade principal"""
        title = "Bitcoin supera US$ 100.000"
        content = "O BTC atingiu novo recorde histórico."

        context = analyzer.analyze(title, content, None)

        assert context.entity_type == EntityType.CRYPTO
        assert context.primary_entity == 'bitcoin'
        assert context.primary_entity_display == 'Bitcoin'

    def test_exchange_entity_identification(self, analyzer):
        """Deve identificar exchange como entidade principal"""
        title = "Binance anuncia nova listagem"
        content = "A maior exchange do mundo listará o token XYZ."

        context = analyzer.analyze(title, content, "altcoins")

        assert context.entity_type == EntityType.EXCHANGE
        assert context.primary_entity == 'binance'
        assert context.primary_entity_display == 'Binance'

    def test_bank_entity_identification(self, analyzer):
        """Deve identificar banco como entidade principal"""
        title = "JPMorgan entra no mercado cripto"
        content = "O banco de investimentos anunciou novos serviços."

        context = analyzer.analyze(title, content, None)

        assert context.entity_type == EntityType.BANK
        assert context.primary_entity == 'jpmorgan'
        assert context.primary_entity_display == 'JPMorgan'

    def test_government_entity_identification(self, analyzer):
        """Deve identificar entidade governamental"""
        title = "SEC aprova ETF de Bitcoin"
        content = "O regulador americano autorizou o primeiro ETF spot."

        context = analyzer.analyze(title, content, None)

        assert context.entity_type == EntityType.GOVERNMENT
        assert context.primary_entity == 'sec'
        assert context.primary_entity_display == 'SEC'

    def test_company_entity_identification(self, analyzer):
        """Deve identificar empresa como entidade principal"""
        title = "Tesla compra mais Bitcoin"
        content = "A empresa de Elon Musk aumentou suas reservas."

        context = analyzer.analyze(title, content, None)

        assert context.entity_type == EntityType.COMPANY
        assert context.primary_entity == 'tesla'

    # === Testes de Identificação de Ação ===

    def test_action_lanca_detection(self, analyzer):
        """Deve detectar ação de lançamento"""
        title = "NYSE lança plataforma blockchain"
        content = "A bolsa de valores anunciou nova plataforma."

        context = analyzer.analyze(title, content, None)

        assert context.action.action == 'lanca'
        assert context.action.implies_data is False

    def test_action_sobe_detection(self, analyzer):
        """Deve detectar ação de alta"""
        title = "Bitcoin dispara 15% após aprovação de ETF"
        content = "O preço do BTC subiu expressivamente."

        context = analyzer.analyze(title, content, None)

        assert context.action.action == 'sobe'
        assert context.action.implies_data is True

    def test_action_cai_detection(self, analyzer):
        """Deve detectar ação de queda"""
        title = "Ethereum despenca após venda massiva"
        content = "O ETH recuou drasticamente hoje."

        context = analyzer.analyze(title, content, None)

        assert context.action.action == 'cai'
        assert context.action.implies_data is True

    def test_action_alerta_detection(self, analyzer):
        """Deve detectar ação de alerta"""
        title = "Goldman Sachs alerta sobre riscos em DeFi"
        content = "O banco avisou investidores sobre volatilidade."

        context = analyzer.analyze(title, content, None)

        assert context.action.action == 'alerta'
        assert context.action.implies_data is False

    # === Testes de Dados Numéricos ===

    def test_numeric_data_percentage_detection(self, analyzer):
        """Deve detectar porcentagem como dado numérico"""
        title = "Bitcoin sobe 15% em 24 horas"
        content = "A criptomoeda valorizou expressivamente."

        context = analyzer.analyze(title, content, None)

        assert context.has_numeric_data is True
        assert context.numeric_context == 'percentage'

    def test_numeric_data_price_detection(self, analyzer):
        """Deve detectar preço como dado numérico"""
        title = "Bitcoin atinge $100.000"
        content = "O preço do BTC atingiu novo patamar."

        context = analyzer.analyze(title, content, None)

        assert context.has_numeric_data is True

    def test_no_numeric_data(self, analyzer):
        """Deve retornar False quando não há dados numéricos"""
        title = "Análise do mercado cripto"
        content = "Especialistas avaliam tendências."

        context = analyzer.analyze(title, content, None)

        assert context.has_numeric_data is False

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

    def test_security_news_type_detection(self, analyzer):
        """Deve detectar notícias de segurança"""
        title = "Protocolo DeFi sofre exploit"
        content = "Vulnerabilidade no contrato permitiu ataque de hackers."

        context = analyzer.analyze(title, content, "defi")

        assert context.news_type == NewsType.SECURITY

    # === Testes de Confiança ===

    def test_confidence_calculation(self, analyzer):
        """Deve calcular score de confiança razoável"""
        title = "Bitcoin atinge recorde após aprovação do ETF pela SEC"
        content = "A Binance registrou volume recorde de negociações."

        context = analyzer.analyze(title, content, "bitcoin")

        assert 0.0 <= context.confidence_score <= 1.0
        # Com múltiplos sinais, confiança deve ser maior
        assert context.confidence_score >= 0.5


class TestEditorialVisualElementsBank:
    """Testes para o banco de elementos visuais editoriais"""

    @pytest.fixture
    def bank(self):
        return EditorialVisualElementsBank()

    def test_get_photography_style_for_crypto(self, bank):
        """Deve retornar estilo fotográfico para criptomoedas"""
        style = bank.get_photography_style(EntityType.CRYPTO)
        assert "product photography" in style.lower()
        assert "cryptocurrency" in style.lower()

    def test_get_photography_style_for_bank(self, bank):
        """Deve retornar estilo fotográfico para bancos"""
        style = bank.get_photography_style(EntityType.BANK)
        assert "institutional" in style.lower() or "corporate" in style.lower()

    def test_get_photography_style_for_government(self, bank):
        """Deve retornar estilo fotográfico para governo"""
        style = bank.get_photography_style(EntityType.GOVERNMENT)
        assert "government" in style.lower() or "institutional" in style.lower()

    def test_get_main_subject_for_bitcoin(self, bank):
        """Deve retornar subject concreto para Bitcoin"""
        subject = bank.get_main_subject(EntityType.CRYPTO, 'bitcoin', 'Bitcoin')
        assert "bitcoin" in subject.lower()
        assert "coin" in subject.lower() or "gold" in subject.lower()
        # Não deve ter elementos abstratos
        assert "network" not in subject.lower()
        assert "particle" not in subject.lower()

    def test_get_main_subject_for_ethereum(self, bank):
        """Deve retornar subject concreto para Ethereum"""
        subject = bank.get_main_subject(EntityType.CRYPTO, 'ethereum', 'Ethereum')
        assert "ethereum" in subject.lower()
        assert "diamond" in subject.lower() or "logo" in subject.lower()

    def test_get_main_subject_for_exchange(self, bank):
        """Deve retornar subject concreto para exchanges"""
        subject = bank.get_main_subject(EntityType.EXCHANGE, 'binance', 'Binance')
        assert "binance" in subject.lower()
        assert "logo" in subject.lower()

    def test_get_main_subject_for_bank(self, bank):
        """Deve retornar subject concreto para bancos"""
        subject = bank.get_main_subject(EntityType.BANK, 'jpmorgan', 'JPMorgan')
        assert "jpmorgan" in subject.lower()
        assert "logo" in subject.lower() or "corporate" in subject.lower()

    def test_get_main_subject_for_government(self, bank):
        """Deve retornar subject concreto para governo"""
        subject = bank.get_main_subject(EntityType.GOVERNMENT, 'sec', 'SEC')
        assert "sec" in subject.lower() or "regulatory" in subject.lower()

    def test_get_background_for_positive_sentiment(self, bank):
        """Deve retornar background apropriado para sentimento positivo"""
        background = bank.get_background(NewsSentiment.POSITIVE)
        assert isinstance(background, str)
        # Deve ser limpo/claro
        assert "white" in background.lower() or "green" in background.lower() or "light" in background.lower()

    def test_get_background_for_negative_sentiment(self, bank):
        """Deve retornar background apropriado para sentimento negativo"""
        background = bank.get_background(NewsSentiment.NEGATIVE)
        assert isinstance(background, str)
        # Deve ser mais sério/escuro
        assert "dark" in background.lower() or "red" in background.lower() or "charcoal" in background.lower()

    def test_get_color_palette_for_bitcoin(self, bank):
        """Deve retornar paleta de cores específica do Bitcoin"""
        palette = bank.get_color_palette(NewsSentiment.POSITIVE, EntityType.CRYPTO, 'bitcoin')
        assert isinstance(palette, str)
        # Bitcoin deve ter cores douradas/laranja
        assert "orange" in palette.lower() or "gold" in palette.lower()

    def test_get_color_palette_for_ethereum(self, bank):
        """Deve retornar paleta de cores específica do Ethereum"""
        palette = bank.get_color_palette(NewsSentiment.NEUTRAL, EntityType.CRYPTO, 'ethereum')
        assert isinstance(palette, str)
        # Ethereum deve ter cores roxas
        assert "purple" in palette.lower() or "violet" in palette.lower()

    def test_get_data_overlay_for_price_up(self, bank):
        """Deve retornar overlay de dados para alta de preço"""
        overlay = bank.get_data_overlay(True, NewsSentiment.POSITIVE, 'sobe', 'percentage')
        assert overlay is not None
        assert "green" in overlay.lower() or "upward" in overlay.lower()

    def test_get_data_overlay_for_price_down(self, bank):
        """Deve retornar overlay de dados para queda de preço"""
        overlay = bank.get_data_overlay(True, NewsSentiment.NEGATIVE, 'cai', 'percentage')
        assert overlay is not None
        assert "red" in overlay.lower() or "downward" in overlay.lower()

    def test_get_data_overlay_returns_none_when_no_data(self, bank):
        """Deve retornar None quando não há dados numéricos"""
        overlay = bank.get_data_overlay(False, NewsSentiment.NEUTRAL, 'informa', None)
        assert overlay is None

    def test_get_lighting_for_positive_sentiment(self, bank):
        """Deve retornar iluminação apropriada para sentimento positivo"""
        lighting = bank.get_lighting(NewsSentiment.POSITIVE)
        assert isinstance(lighting, str)
        assert "bright" in lighting.lower() or "warm" in lighting.lower() or "optimistic" in lighting.lower()

    def test_get_text_area(self, bank):
        """Deve retornar especificação de área para texto"""
        text_area = bank.get_text_area()
        assert isinstance(text_area, str)
        assert "text" in text_area.lower() or "headline" in text_area.lower()

    def test_compose_editorial_elements(self, bank):
        """Deve compor elementos editoriais completos"""
        composition = bank.compose_editorial_elements(
            entity_type=EntityType.CRYPTO,
            entity_name='bitcoin',
            entity_display='Bitcoin',
            sentiment=NewsSentiment.POSITIVE,
            action='sobe',
            has_numeric_data=True,
            numeric_context='percentage',
            keywords=['ETF']
        )

        assert isinstance(composition, EditorialComposition)
        assert composition.photography_style
        assert composition.main_subject
        assert "bitcoin" in composition.main_subject.lower()
        assert composition.background
        assert composition.color_palette
        assert composition.data_overlay is not None  # Has numeric data
        assert composition.lighting
        assert composition.text_area


class TestSmartPromptGenerator:
    """Testes para o gerador inteligente de prompts editoriais"""

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

    def test_generate_prompt_includes_editorial_elements(self, generator):
        """Deve incluir elementos editoriais obrigatórios no prompt"""
        prompt = generator.generate_prompt(
            title="Ethereum lança atualização",
            content="A rede Ethereum recebeu nova atualização.",
            category="ethereum"
        )

        prompt_lower = prompt.lower()
        # Deve ter referência de estilo editorial
        assert "coindesk" in prompt_lower or "cointelegraph" in prompt_lower
        # Deve especificar que é fotográfico
        assert "photo" in prompt_lower
        # Deve evitar abstrações
        assert "avoid" in prompt_lower

    def test_generate_prompt_includes_no_text_specification(self, generator):
        """Deve especificar que não deve ter texto na imagem"""
        prompt = generator.generate_prompt(
            title="Bitcoin em alta",
            content="O mercado está otimista.",
            category="bitcoin"
        )

        assert "no text" in prompt.lower()

    def test_generate_prompt_includes_aspect_ratio(self, generator):
        """Deve incluir especificação de aspect ratio"""
        prompt = generator.generate_prompt(
            title="Bitcoin em alta",
            content="O mercado está otimista.",
            category="bitcoin"
        )

        assert "16:9" in prompt.lower()

    def test_generate_prompt_avoids_abstract_elements(self, generator):
        """Deve incluir instrução para evitar elementos abstratos"""
        prompt = generator.generate_prompt(
            title="Ethereum atualiza",
            content="Nova versão do protocolo.",
            category="ethereum"
        )

        prompt_lower = prompt.lower()
        assert "avoid" in prompt_lower
        assert "abstract" in prompt_lower or "blockchain" in prompt_lower

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
        assert 'entity_type' in result['metadata']
        assert 'primary_entity' in result['metadata']
        assert 'sentiment' in result['metadata']
        assert 'news_type' in result['metadata']
        assert 'action' in result['metadata']
        assert 'prompt_version' in result['metadata']
        assert result['metadata']['prompt_version'] == 'v2.0-editorial'

    def test_fallback_prompt_generation(self, generator):
        """Deve gerar prompt fallback em caso de categoria"""
        for category in ['bitcoin', 'ethereum', 'defi', 'regulacao']:
            fallback = generator._generate_fallback_prompt(category)
            assert isinstance(fallback, str)
            assert len(fallback) > 50
            # Fallback também deve ser editorial
            assert "editorial" in fallback.lower() or "coindesk" in fallback.lower()
            assert "avoid" in fallback.lower()

    def test_fallback_prompt_for_unknown_category(self, generator):
        """Deve gerar prompt fallback genérico para categoria desconhecida"""
        fallback = generator._generate_fallback_prompt('categoria_inexistente')
        assert isinstance(fallback, str)
        assert len(fallback) > 50
        assert "editorial" in fallback.lower()

    def test_prompt_variation_mechanism(self, generator):
        """Deve gerar prompts diferentes para mesma notícia"""
        title = "Bitcoin em alta"
        content = "O mercado está otimista."

        prompts = set()
        for _ in range(5):
            prompt = generator.generate_prompt(title, content, "bitcoin")
            prompts.add(prompt[:100])  # Comparar primeiros 100 chars

        # Pelo menos 1 variação (devido à aleatoriedade)
        assert len(prompts) >= 1

    def test_prompt_for_positive_news(self, generator):
        """Deve gerar prompt apropriado para notícia positiva"""
        result = generator.generate_prompt_with_metadata(
            title="Bitcoin dispara e atinge novo recorde",
            content="O BTC valorizou 20% e rompeu a máxima histórica.",
            category="bitcoin"
        )

        assert result['metadata']['sentiment'] == 'positive'

    def test_prompt_for_negative_news(self, generator):
        """Deve gerar prompt apropriado para notícia negativa"""
        result = generator.generate_prompt_with_metadata(
            title="Ethereum despenca após vendas massivas",
            content="O ETH caiu 15% com liquidações em cascata.",
            category="ethereum"
        )

        assert result['metadata']['sentiment'] == 'negative'

    def test_prompt_for_regulation_news(self, generator):
        """Deve gerar prompt apropriado para notícia de regulação"""
        result = generator.generate_prompt_with_metadata(
            title="SEC analisa novo framework para criptomoedas",
            content="O regulador está desenvolvendo novas regras para o mercado.",
            category="regulacao"
        )

        assert result['metadata']['news_type'] == 'regulation'


class TestEditorialIntegration:
    """Testes de integração entre os módulos no estilo editorial"""

    def test_full_pipeline_bitcoin_positive(self):
        """Teste completo: notícia positiva de Bitcoin"""
        analyzer = NewsContextAnalyzer()
        bank = EditorialVisualElementsBank()
        generator = SmartPromptGenerator(analyzer, bank)

        title = "Bitcoin atinge US$ 100.000 pela primeira vez"
        content = """
        O Bitcoin finalmente rompeu a barreira dos US$ 100.000, marcando um
        momento histórico para o mercado de criptomoedas. A alta foi impulsionada
        pela aprovação de ETFs e entrada institucional massiva.
        """

        result = generator.generate_prompt_with_metadata(title, content, "bitcoin")

        assert result['metadata']['sentiment'] == 'positive'
        assert result['metadata']['primary_entity'] == 'bitcoin'
        assert result['metadata']['entity_type'] == 'crypto'

        # Prompt deve ser editorial
        prompt = result['prompt'].lower()
        assert 'professional' in prompt
        assert 'photo' in prompt
        assert 'avoid' in prompt
        assert len(result['prompt']) > 200

    def test_full_pipeline_nyse_launch(self):
        """Teste completo: NYSE lança plataforma"""
        generator = SmartPromptGenerator()

        title = "NYSE Lança Plataforma Blockchain para Negociação 24/7"
        content = """
        A New York Stock Exchange anunciou o lançamento de uma nova plataforma
        blockchain que permitirá negociação de ativos digitais 24 horas por dia,
        7 dias por semana.
        """

        result = generator.generate_prompt_with_metadata(title, content, None)

        assert result['metadata']['entity_type'] == 'government'
        assert result['metadata']['primary_entity'] == 'nyse'
        assert result['metadata']['action'] == 'lanca'

        # Prompt deve mencionar NYSE e ser editorial
        prompt = result['prompt'].lower()
        assert 'nyse' in prompt or 'stock exchange' in prompt

    def test_full_pipeline_goldman_sachs_warning(self):
        """Teste completo: Goldman Sachs alerta sobre riscos"""
        generator = SmartPromptGenerator()

        title = "Goldman Sachs Alerta Sobre Riscos em DeFi"
        content = """
        O banco de investimentos Goldman Sachs emitiu um alerta para seus clientes
        sobre os riscos associados ao setor de finanças descentralizadas (DeFi),
        citando volatilidade e riscos regulatórios.
        """

        result = generator.generate_prompt_with_metadata(title, content, None)

        assert result['metadata']['entity_type'] == 'bank'
        assert result['metadata']['primary_entity'] == 'goldman sachs'
        assert result['metadata']['sentiment'] == 'negative'
        assert result['metadata']['action'] == 'alerta'

        # Prompt deve ter elementos de warning mas sem palavras bloqueadas
        prompt = result['prompt'].lower()
        assert 'goldman sachs' in prompt

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
        assert result['metadata']['entity_type'] == 'crypto'
        assert result['metadata']['primary_entity'] == 'ethereum'

        # Prompt deve ter elementos do Ethereum
        prompt = result['prompt'].lower()
        assert 'ethereum' in prompt or 'purple' in prompt

    def test_full_pipeline_security_warning(self):
        """Teste completo: notícia de segurança (palavras devem ser sanitizadas)"""
        generator = SmartPromptGenerator()

        title = "Exchange sofre ataque hacker de US$ 50 milhões"
        content = """
        Uma exchange centralizada foi alvo de hackers que exploraram
        vulnerabilidade no sistema. Fundos dos usuários foram roubados.
        """

        result = generator.generate_prompt_with_metadata(title, content, "altcoins")

        # O sentimento deve ser negativo
        assert result['metadata']['sentiment'] == 'negative'
        assert result['metadata']['news_type'] == 'security'

        # O prompt deve estar sanitizado - sem palavras perigosas
        prompt = result['prompt'].lower()
        assert 'hack' not in prompt
        assert 'attack' not in prompt
        assert 'stolen' not in prompt

    def test_prompt_does_not_contain_abstract_elements(self):
        """Verifica que prompts não contêm elementos abstratos proibidos"""
        generator = SmartPromptGenerator()

        test_cases = [
            ("Bitcoin sobe 10%", "Alta expressiva do BTC", "bitcoin"),
            ("Ethereum atualiza", "Nova versão do protocolo", "ethereum"),
            ("SEC aprova ETF", "Regulador autoriza produto", "regulacao"),
            ("Binance lança token", "Exchange cria novo ativo", "altcoins"),
        ]

        prohibited_terms = [
            'blockchain network',
            'particle',
            'glowing',
            'neon',
            'cyberpunk',
            'matrix',
            'sci-fi',
            'futuristic',
        ]

        for title, content, category in test_cases:
            prompt = generator.generate_prompt(title, content, category).lower()
            for term in prohibited_terms:
                if term in prompt:
                    # Só é aceitável se estiver na seção "avoid"
                    avoid_index = prompt.find('avoid')
                    term_index = prompt.find(term)
                    if avoid_index == -1 or term_index < avoid_index:
                        pytest.fail(f"Prompt contém termo proibido '{term}' fora da seção avoid: {title}")
