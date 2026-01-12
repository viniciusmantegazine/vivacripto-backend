"""
Unit tests for Quality Validator service.
"""
import pytest

from app.services.automation.quality_validator import QualityValidator


class TestQualityValidator:
    """Test suite for QualityValidator."""

    @pytest.fixture
    def validator(self) -> QualityValidator:
        """Create a QualityValidator instance."""
        return QualityValidator()

    @pytest.fixture
    def valid_article(self) -> dict:
        """Create a valid article with all required fields."""
        return {
            "title": "Bitcoin Atinge Nova Máxima Histórica em 2024",
            "content_markdown": """## Bitcoin em Alta

O Bitcoin atingiu uma nova máxima histórica nesta semana, superando a marca de $100.000 pela primeira vez na história. A criptomoeda mais valiosa do mundo continua sua trajetória de valorização.

Analistas apontam que a entrada de investidores institucionais, especialmente através dos ETFs aprovados nos Estados Unidos, foi o principal catalisador dessa alta histórica.

O mercado de criptomoedas como um todo reagiu positivamente, com Ethereum e outras altcoins também registrando ganhos expressivos. A dominância do BTC permanece acima de 50%.

Especialistas recomendam cautela apesar do otimismo, lembrando que o mercado crypto é conhecido por sua volatilidade extrema.""",
            "excerpt": "Bitcoin supera $100.000 pela primeira vez na história, impulsionado por ETFs e investidores institucionais. Mercado crypto celebra marco histórico.",
            "meta_description": "Bitcoin atinge nova máxima histórica de $100.000 em 2024. Entenda os fatores por trás da alta e o que esperar do mercado de criptomoedas.",
            "meta_title": "Bitcoin Bate Recorde: $100k pela Primeira Vez",
        }

    def test_validate_article_success(self, validator: QualityValidator, valid_article: dict):
        """Test validation of a valid article."""
        is_valid, errors = validator.validate_article(valid_article)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_article_missing_title(self, validator: QualityValidator, valid_article: dict):
        """Test validation fails when title is missing."""
        valid_article["title"] = ""

        is_valid, errors = validator.validate_article(valid_article)

        assert is_valid is False
        assert any("Título ausente" in e for e in errors)

    def test_validate_article_title_too_short(self, validator: QualityValidator, valid_article: dict):
        """Test validation fails when title is too short."""
        valid_article["title"] = "Bitcoin Sobe"

        is_valid, errors = validator.validate_article(valid_article)

        assert is_valid is False
        assert any("muito curto" in e.lower() for e in errors)

    def test_validate_article_title_truncation(self, validator: QualityValidator, valid_article: dict):
        """Test that long titles are automatically truncated."""
        original_title = "Bitcoin " * 20  # Very long title
        valid_article["title"] = original_title

        validator.validate_article(valid_article)

        assert len(valid_article["title"]) <= validator.MAX_TITLE_LENGTH + 3  # +3 for "..."

    def test_validate_article_missing_keywords(self, validator: QualityValidator, valid_article: dict):
        """Test validation fails when no crypto keywords are present."""
        valid_article["title"] = "Mercado Financeiro em Alta Nesta Semana"
        valid_article["content_markdown"] = """## Mercado em Alta

O mercado financeiro registrou ganhos expressivos nesta semana. Os investidores estão otimistas.

Analistas apontam que a economia está se recuperando bem. Os indicadores são positivos.

A bolsa de valores teve uma semana muito boa. Os resultados foram excelentes."""

        is_valid, errors = validator.validate_article(valid_article)

        assert is_valid is False
        assert any("palavra-chave" in e.lower() for e in errors)

    def test_validate_article_content_too_short(self, validator: QualityValidator, valid_article: dict):
        """Test validation fails when content is too short."""
        valid_article["content_markdown"] = "## Teste\n\nBitcoin subiu. Mercado otimista."

        is_valid, errors = validator.validate_article(valid_article)

        assert is_valid is False
        assert any("muito curto" in e.lower() for e in errors)

    def test_validate_article_content_too_long(self, validator: QualityValidator, valid_article: dict):
        """Test validation fails when content is too long."""
        # Create content with more than 450 words
        valid_article["content_markdown"] = "## Bitcoin\n\n" + ("Bitcoin crypto blockchain defi token " * 100)

        is_valid, errors = validator.validate_article(valid_article)

        assert is_valid is False
        assert any("muito longo" in e.lower() for e in errors)

    def test_validate_article_missing_excerpt(self, validator: QualityValidator, valid_article: dict):
        """Test validation fails when excerpt is missing."""
        valid_article["excerpt"] = ""

        is_valid, errors = validator.validate_article(valid_article)

        assert is_valid is False
        assert any("Excerpt ausente" in e for e in errors)

    def test_validate_article_excerpt_truncation(self, validator: QualityValidator, valid_article: dict):
        """Test that long excerpts are automatically truncated."""
        valid_article["excerpt"] = "Bitcoin " * 50  # Very long excerpt

        validator.validate_article(valid_article)

        assert len(valid_article["excerpt"]) <= validator.MAX_EXCERPT_LENGTH + 3

    def test_validate_article_missing_meta_description(self, validator: QualityValidator, valid_article: dict):
        """Test validation fails when meta_description is missing."""
        valid_article["meta_description"] = ""

        is_valid, errors = validator.validate_article(valid_article)

        assert is_valid is False
        assert any("Meta description ausente" in e for e in errors)

    def test_validate_article_meta_title_truncation(self, validator: QualityValidator, valid_article: dict):
        """Test that long meta_titles are automatically truncated."""
        valid_article["meta_title"] = "Bitcoin " * 20  # Very long meta title

        validator.validate_article(valid_article)

        assert len(valid_article["meta_title"]) <= validator.MAX_META_TITLE_LENGTH

    def test_validate_article_meta_title_generated_from_title(self, validator: QualityValidator, valid_article: dict):
        """Test that meta_title is generated from title if missing."""
        del valid_article["meta_title"]

        validator.validate_article(valid_article)

        assert "meta_title" in valid_article
        assert len(valid_article["meta_title"]) <= validator.MAX_META_TITLE_LENGTH

    def test_validate_content_structure_no_h2(self, validator: QualityValidator, valid_article: dict):
        """Test validation fails when content doesn't start with H2."""
        valid_article["content_markdown"] = """Bitcoin atingiu nova máxima histórica.

O mercado de criptomoedas está em alta. A dominância do BTC permanece forte.

Especialistas recomendam cautela. A volatilidade continua presente no mercado crypto."""

        is_valid, errors = validator.validate_article(valid_article)

        assert is_valid is False
        assert any("manchete interna" in e.lower() or "H2" in e for e in errors)

    def test_validate_content_structure_insufficient_paragraphs(self, validator: QualityValidator, valid_article: dict):
        """Test validation fails when content has too few paragraphs."""
        valid_article["content_markdown"] = """## Bitcoin em Alta

O Bitcoin atingiu nova máxima histórica. A criptomoeda mais valiosa continua em alta."""

        is_valid, errors = validator.validate_article(valid_article)

        assert is_valid is False
        # Should fail due to word count or paragraph count

    def test_validate_content_mostly_lists_fails(self, validator: QualityValidator, valid_article: dict):
        """Test validation fails when content is mostly bullet lists."""
        valid_article["content_markdown"] = """## Lista de Cryptos

- Bitcoin subiu 10%
- Ethereum subiu 15%
- Solana subiu 20%
- Cardano subiu 5%
- Polkadot subiu 8%
- Avalanche subiu 12%
- Chainlink subiu 7%
- Polygon subiu 9%"""

        is_valid, errors = validator.validate_article(valid_article)

        assert is_valid is False


class TestQualityValidatorKeywords:
    """Test keyword validation specifically."""

    @pytest.fixture
    def validator(self) -> QualityValidator:
        return QualityValidator()

    @pytest.mark.parametrize("keyword", [
        "bitcoin", "btc", "ethereum", "eth", "crypto",
        "criptomoeda", "blockchain", "defi", "nft", "token"
    ])
    def test_each_keyword_is_valid(self, validator: QualityValidator, keyword: str):
        """Test that each required keyword is recognized."""
        article = {
            "content_markdown": f"## Teste\n\nEste artigo fala sobre {keyword}.",
            "title": f"Notícia sobre {keyword} hoje no mercado"
        }

        is_valid, _ = validator._validate_keywords(article)

        assert is_valid is True

    def test_keyword_in_title_only(self, validator: QualityValidator):
        """Test that keyword in title is sufficient."""
        article = {
            "content_markdown": "## Teste\n\nConteúdo sem palavras especiais.",
            "title": "Bitcoin atinge nova alta"
        }

        is_valid, _ = validator._validate_keywords(article)

        assert is_valid is True

    def test_keyword_case_insensitive(self, validator: QualityValidator):
        """Test that keyword matching is case insensitive."""
        article = {
            "content_markdown": "## Teste\n\nBITCOIN está em alta.",
            "title": "ETHEREUM sobe"
        }

        is_valid, _ = validator._validate_keywords(article)

        assert is_valid is True
