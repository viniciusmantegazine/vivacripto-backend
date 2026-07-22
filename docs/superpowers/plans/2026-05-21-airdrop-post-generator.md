# Airdrop Post Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a manual `POST /api/v1/airdrops/generate-post` endpoint that researches a crypto project on the web, generates a neutral 500-750 word educational article about its airdrop, embeds the operator's referral link with required disclosure, and either previews or publishes it under the "Airdrop" category.

**Architecture:** New service module `app/services/airdrop/` with `WebResearcher` (DDG search + URL fetch + HTML extraction) and `AirdropPostGenerator` (orchestrates research → Claude with Gemini fallback → article dict). New router `app/api/v1/endpoints/airdrops.py`. Reuses `QualityValidator` (parametrized for 500-750 words), `ArticlePublisher` (with forced category override), `ImageGenerator`, `verify_automation_token`, and rate limiter.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy async / Pydantic v2 / Anthropic SDK (Claude Sonnet 4.6) / google-genai (fallback) / ddgs (DuckDuckGo) / httpx / beautifulsoup4 (new) / pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-05-21-airdrop-post-generator-design.md`

---

## Conventions

- All Python source code uses 4-space indent, Portuguese comments (matches existing codebase).
- All commits follow `feat:`, `test:`, `refactor:`, `chore:`, `docs:` prefix style (matches `git log`).
- All commands run from repo root `/Users/viniciusmantegazine/git/verticecripto-backend/`.
- Run tests with: `pytest tests/path/to/test_file.py::test_name -v`
- For tests needing the full DB schema: SQLite in-memory is configured in `tests/conftest.py` via `async_db_engine` fixture.

---

### Task 1: Add `beautifulsoup4` dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add the dependency**

Edit `requirements.txt`. Find the "Utils" section and add `beautifulsoup4>=4.12.0` below `markdown==3.5.1`:

```
# Utils
python-slugify==8.0.1
markdown==3.5.1
beautifulsoup4>=4.12.0
```

- [ ] **Step 2: Install locally**

Run: `pip install beautifulsoup4>=4.12.0`
Expected: `Successfully installed beautifulsoup4-4.x.x soupsieve-2.x.x`

- [ ] **Step 3: Verify import works**

Run: `python -c "from bs4 import BeautifulSoup; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add beautifulsoup4 dependency for HTML extraction"
```

---

### Task 2: Parametrize `QualityValidator` for custom word ranges

The current `QualityValidator` hardcodes `MIN_WORD_COUNT=250` / `MAX_WORD_COUNT=500` as class constants. We need to accept constructor overrides for the airdrop post (500-750 words) while preserving current behavior for the daily pipeline.

**Files:**
- Modify: `app/services/automation/quality_validator.py`
- Create: `tests/unit/test_quality_validator_airdrop.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_quality_validator_airdrop.py`:

```python
"""
Testes para parametrização do QualityValidator com word range customizado
"""
import pytest

from app.services.automation.quality_validator import QualityValidator


def _article_with_word_count(words: int) -> dict:
    """Cria um artigo de teste com a contagem de palavras desejada"""
    content = "## Manchete\n\n" + "palavra " * words
    return {
        "title": "Bitcoin e o futuro do mercado cripto em 2026 aqui",
        "slug": "bitcoin-futuro-mercado-cripto-2026",
        "excerpt": "Um excerpt de teste sobre bitcoin que tem mais de oitenta caracteres aqui ok.",
        "meta_title": "Bitcoin e o futuro do mercado em 2026",
        "meta_description": (
            "Bitcoin segue como o principal ativo cripto e segue gerando "
            "discussoes sobre o futuro do mercado em 2026."
        ),
        "content_markdown": content,
    }


def test_accepts_custom_word_range_within_bounds():
    validator = QualityValidator(min_words=500, max_words=750)
    article = _article_with_word_count(600)
    is_valid, errors = validator.validate_article(article)
    assert is_valid, f"Expected valid, got errors: {errors}"


def test_rejects_below_custom_min_words():
    validator = QualityValidator(min_words=500, max_words=750)
    article = _article_with_word_count(400)
    is_valid, errors = validator.validate_article(article)
    assert not is_valid
    assert any("400 palavras" in e and "mínimo 500" in e for e in errors)


def test_rejects_above_custom_max_words():
    validator = QualityValidator(min_words=500, max_words=750)
    article = _article_with_word_count(800)
    is_valid, errors = validator.validate_article(article)
    assert not is_valid
    assert any("800 palavras" in e and "máximo 750" in e for e in errors)


def test_default_constructor_preserves_original_behavior():
    """Sem argumentos, validator deve manter 250-500 (compatibilidade)"""
    validator = QualityValidator()
    article = _article_with_word_count(400)
    is_valid, _ = validator.validate_article(article)
    assert is_valid

    article_too_long = _article_with_word_count(600)
    is_valid, errors = validator.validate_article(article_too_long)
    assert not is_valid
    assert any("máximo 500" in e for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_quality_validator_airdrop.py -v`
Expected: All 4 tests FAIL (`TypeError: QualityValidator() takes no arguments`)

- [ ] **Step 3: Implement parametrization in `QualityValidator`**

In `app/services/automation/quality_validator.py`, replace the class-level word count constants and add `__init__`. Find this block (around lines 19-21):

```python
    # Limites de qualidade v2.0 - Estrutura flexível
    MIN_WORD_COUNT = 250  # Mínimo para garantir substância
    MAX_WORD_COUNT = 500  # Máximo para manter artigos concisos
```

Replace with:

```python
    # Limites de qualidade v2.0 - Estrutura flexível (defaults; pode ser override no __init__)
    MIN_WORD_COUNT = 250  # Default mínimo
    MAX_WORD_COUNT = 500  # Default máximo

    def __init__(self, min_words: int = None, max_words: int = None):
        """
        Args:
            min_words: Override do limite mínimo de palavras (default 250)
            max_words: Override do limite máximo de palavras (default 500)
        """
        self.min_word_count = min_words if min_words is not None else self.MIN_WORD_COUNT
        self.max_word_count = max_words if max_words is not None else self.MAX_WORD_COUNT
```

Then update `_validate_word_count` to use the instance attributes. Find this block (around lines 84-95):

```python
    def _validate_word_count(self, article: Dict) -> Tuple[bool, str]:
        """Valida a contagem de palavras do conteúdo"""
        content = article.get("content_markdown", "")
        word_count = len(content.split())
        
        if word_count < self.MIN_WORD_COUNT:
            return False, f"Conteúdo muito curto ({word_count} palavras, mínimo {self.MIN_WORD_COUNT})"
        
        if word_count > self.MAX_WORD_COUNT:
            return False, f"Conteúdo muito longo ({word_count} palavras, máximo {self.MAX_WORD_COUNT})"
        
        return True, ""
```

Replace with:

```python
    def _validate_word_count(self, article: Dict) -> Tuple[bool, str]:
        """Valida a contagem de palavras do conteúdo"""
        content = article.get("content_markdown", "")
        word_count = len(content.split())

        if word_count < self.min_word_count:
            return False, f"Conteúdo muito curto ({word_count} palavras, mínimo {self.min_word_count})"

        if word_count > self.max_word_count:
            return False, f"Conteúdo muito longo ({word_count} palavras, máximo {self.max_word_count})"

        return True, ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_quality_validator_airdrop.py -v`
Expected: All 4 PASS.

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `pytest tests/ -q`
Expected: All previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add app/services/automation/quality_validator.py tests/unit/test_quality_validator_airdrop.py
git commit -m "feat: parametrize QualityValidator word count for airdrop posts"
```

---

### Task 3: Add forced category override to `ArticlePublisher`

`ArticlePublisher._get_or_create_category` always calls `category_classifier.classify()`. For airdrop posts we need to force `"airdrop"` regardless of content. Adds an optional `force_category_slug` param to `publish_article`.

**Files:**
- Modify: `app/services/automation/article_publisher.py`
- Create: `tests/unit/test_article_publisher_force_category.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_article_publisher_force_category.py`:

```python
"""
Testa o override de categoria no ArticlePublisher para uso em airdrops.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.db.models import Category
from app.services.automation.article_publisher import ArticlePublisher


@pytest_asyncio.fixture
async def airdrop_category(db_session) -> Category:
    cat = Category(id=uuid4(), name="Airdrop", slug="airdrop")
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)
    return cat


@pytest.mark.asyncio
async def test_publish_uses_forced_category_slug(db_session, airdrop_category):
    """Quando force_category_slug é passado, classifier não é usado."""
    article = {
        "title": "LayerZero: o que e o protocolo e como participar do airdrop",
        "slug": "layerzero-protocolo-airdrop",
        "content_markdown": "## Sobre\n\nLayerZero is a protocol.\n\nDetails here.",
        "excerpt": "Conheca o LayerZero, protocolo de interoperabilidade entre blockchains.",
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "Conheca o LayerZero, protocolo de interoperabilidade. Veja como "
            "participar do airdrop pelo site oficial."
        ),
    }

    mock_image_gen = MagicMock()
    mock_image_gen.generate_and_upload_image = AsyncMock(return_value="https://img/test.jpg")
    publisher = ArticlePublisher(image_generator=mock_image_gen)

    with patch(
        "app.services.automation.article_publisher.category_classifier"
    ) as mock_classifier:
        result = await publisher.publish_article(
            article, db_session, force_category_slug="airdrop"
        )

    assert result is True, "Article should publish successfully"
    mock_classifier.classify.assert_not_called()


@pytest.mark.asyncio
async def test_publish_falls_back_to_classifier_when_no_force(db_session, airdrop_category):
    """Sem force_category_slug, classifier ainda é chamado (comportamento atual)."""
    article = {
        "title": "Bitcoin atinge nova maxima historica em 2026",
        "slug": "bitcoin-maxima-2026",
        "content_markdown": "## Maxima\n\nBitcoin reached.\n\nDetails.",
        "excerpt": "Bitcoin atingiu nova maxima historica acima de US$ 150 mil dolares.",
        "meta_title": "Bitcoin maxima",
        "meta_description": (
            "Bitcoin atinge nova maxima historica acima de US$ 150 mil em 2026, "
            "marcando milestone significativo."
        ),
    }

    mock_image_gen = MagicMock()
    mock_image_gen.generate_and_upload_image = AsyncMock(return_value="https://img/test.jpg")
    publisher = ArticlePublisher(image_generator=mock_image_gen)

    with patch(
        "app.services.automation.article_publisher.category_classifier"
    ) as mock_classifier:
        mock_classifier.classify.return_value = "airdrop"
        mock_classifier.get_category_name.return_value = "Airdrop"
        await publisher.publish_article(article, db_session)

    mock_classifier.classify.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_article_publisher_force_category.py -v`
Expected: `test_publish_uses_forced_category_slug` FAILS with `TypeError: publish_article() got an unexpected keyword argument 'force_category_slug'`. The second test should pass.

- [ ] **Step 3: Add `force_category_slug` parameter**

In `app/services/automation/article_publisher.py`:

Modify `publish_article` signature (around line 37):

```python
    async def publish_article(
        self,
        article: Dict,
        db: AsyncSession,
        force_category_slug: Optional[str] = None,
    ) -> bool:
```

In its body, change the `_get_or_create_category` call (around line 53):

```python
            # Classificar categoria automaticamente (ou usar override)
            category = await self._get_or_create_category(
                article, db, force_category_slug=force_category_slug
            )
```

Then modify `_get_or_create_category` (around line 123):

```python
    async def _get_or_create_category(
        self,
        article: Dict,
        db: AsyncSession,
        force_category_slug: Optional[str] = None,
    ) -> Category:
        """
        Busca ou cria a categoria para o artigo.

        Args:
            article: Dados do artigo para classificação
            db: Sessão do banco de dados
            force_category_slug: Se fornecido, pula o classifier e usa este slug

        Returns:
            Instância da categoria
        """
        if force_category_slug:
            category_slug = force_category_slug
        else:
            category_slug = category_classifier.classify(
                title=article["title"],
                content=article["content_markdown"],
                excerpt=article.get("excerpt", ""),
            )

        result = await db.execute(
            select(Category).where(Category.slug == category_slug)
        )
        category = result.scalar_one_or_none()

        if not category:
            logger.warning(f"Category '{category_slug}' not found, creating...")
            category = Category(
                name=category_classifier.get_category_name(category_slug) or category_slug.capitalize(),
                slug=category_slug,
            )
            db.add(category)
            await db.flush()

        return category
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_article_publisher_force_category.py -v`
Expected: Both tests PASS.

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -q`
Expected: No regressions.

- [ ] **Step 6: Commit**

```bash
git add app/services/automation/article_publisher.py tests/unit/test_article_publisher_force_category.py
git commit -m "feat: allow forcing category slug in ArticlePublisher"
```

---

### Task 4: Create airdrop request/response schemas

**Files:**
- Create: `app/schemas/airdrop.py`
- Create: `tests/unit/test_airdrop_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_airdrop_schemas.py`:

```python
"""
Testes para os schemas Pydantic de airdrop.
"""
import pytest
from pydantic import ValidationError

from app.schemas.airdrop import AirdropPostRequest, AirdropPostResponse


def test_request_accepts_valid_data():
    req = AirdropPostRequest(
        project_name="LayerZero",
        official_url="https://layerzero.network",
        referral_url="https://app.layerzero.foundation/ref/abc",
        publish=False,
    )
    assert req.project_name == "LayerZero"
    assert str(req.official_url).startswith("https://layerzero.network")


def test_request_publish_defaults_to_false():
    req = AirdropPostRequest(
        project_name="X",
        official_url="https://x.com",
        referral_url="https://x.com/ref/1",
    )
    # `publish` é opcional e default deve ser False
    assert req.publish is False


def test_request_rejects_empty_project_name():
    with pytest.raises(ValidationError):
        AirdropPostRequest(
            project_name="",
            official_url="https://x.com",
            referral_url="https://x.com/ref/1",
        )


def test_request_rejects_invalid_url():
    with pytest.raises(ValidationError):
        AirdropPostRequest(
            project_name="X",
            official_url="not-a-url",
            referral_url="https://x.com/ref/1",
        )


def test_response_serializes_with_all_fields():
    resp = AirdropPostResponse(
        success=True,
        post_id="abc-123",
        title="Title",
        slug="title",
        excerpt="Excerpt",
        image_url="https://img/x.jpg",
        word_count=600,
        sources_used=["https://x.com"],
        preview_content="# x",
        errors=[],
    )
    payload = resp.model_dump()
    assert payload["success"] is True
    assert payload["post_id"] == "abc-123"
    assert payload["sources_used"] == ["https://x.com"]


def test_response_optional_fields_default():
    resp = AirdropPostResponse(success=False, title="", slug="", excerpt="")
    assert resp.post_id is None
    assert resp.image_url is None
    assert resp.word_count == 0
    assert resp.sources_used == []
    assert resp.preview_content is None
    assert resp.errors == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_airdrop_schemas.py -v`
Expected: All FAIL (`ModuleNotFoundError: No module named 'app.schemas.airdrop'`).

- [ ] **Step 3: Create the schema module**

Create `app/schemas/airdrop.py`:

```python
"""
Schemas Pydantic para o endpoint de geração de posts sobre airdrops.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class AirdropPostRequest(BaseModel):
    """Request para POST /api/v1/airdrops/generate-post"""

    project_name: str = Field(..., min_length=2, max_length=100)
    official_url: HttpUrl
    referral_url: HttpUrl
    publish: bool = False  # default: gera preview sem publicar


class AirdropPostResponse(BaseModel):
    """Response do endpoint de airdrop (preview ou publicação)"""

    success: bool
    post_id: Optional[str] = None
    title: str
    slug: str
    excerpt: str
    image_url: Optional[str] = None
    word_count: int = 0
    sources_used: List[str] = []
    preview_content: Optional[str] = None
    errors: List[str] = []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_airdrop_schemas.py -v`
Expected: All 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/airdrop.py tests/unit/test_airdrop_schemas.py
git commit -m "feat: add Pydantic schemas for airdrop post endpoint"
```

---

### Task 5: Create `WebResearcher` — URL filtering & ranking

This task covers the **pure logic** part of the researcher: dedup, blocklist, whitelist boost, top-N selection. No I/O.

**Files:**
- Create: `app/services/airdrop/__init__.py`
- Create: `app/services/airdrop/web_researcher.py`
- Create: `tests/unit/test_airdrop_web_researcher_filtering.py`

- [ ] **Step 1: Create empty `__init__.py`**

Create `app/services/airdrop/__init__.py`:

```python
"""Serviços para geração de posts sobre airdrops."""
```

- [ ] **Step 2: Write the failing tests**

Create `tests/unit/test_airdrop_web_researcher_filtering.py`:

```python
"""
Testes da lógica de filtragem/ranking de URLs do WebResearcher.
"""
from app.services.airdrop.web_researcher import (
    WebResearcher,
    BLOCKED_DOMAINS,
    PREFERRED_DOMAINS,
)


def test_deduplicates_urls_by_domain_keeping_top():
    researcher = WebResearcher()
    candidates = [
        ("https://coindesk.com/post-a", 1),
        ("https://coindesk.com/post-b", 2),
        ("https://cointelegraph.com/post-c", 3),
    ]
    result = researcher._dedup_by_domain(candidates)
    # mantém só o primeiro (rank menor) de cada domínio
    domains = {r[0].split("/")[2] for r in result}
    assert "coindesk.com" in domains
    assert "cointelegraph.com" in domains
    assert len(result) == 2


def test_blocklist_drops_social_and_video_domains():
    researcher = WebResearcher()
    candidates = [
        ("https://reddit.com/r/crypto/post", 1),
        ("https://x.com/someone/status/1", 2),
        ("https://youtube.com/watch?v=x", 3),
        ("https://coindesk.com/article", 4),
    ]
    result = researcher._apply_blocklist(candidates)
    domains = {r[0].split("/")[2] for r in result}
    assert "reddit.com" not in domains
    assert "x.com" not in domains
    assert "youtube.com" not in domains
    assert "coindesk.com" in domains


def test_whitelist_boost_prefers_known_sources():
    researcher = WebResearcher()
    candidates = [
        ("https://random-blog.example/post", 1),
        ("https://coindesk.com/article", 5),
        ("https://obscure.io/post", 2),
        ("https://coingecko.com/coin/x", 6),
    ]
    result = researcher._apply_whitelist_boost(candidates)
    # ranks dos preferred devem diminuir (boost = subtraem N de rank)
    coindesk_rank = next(r for url, r in result if "coindesk.com" in url)
    blog_rank = next(r for url, r in result if "random-blog" in url)
    assert coindesk_rank < blog_rank, "Whitelisted domain should outrank random blog after boost"


def test_select_top_n_includes_official_url_always():
    researcher = WebResearcher()
    ranked = [
        ("https://coindesk.com/a", 1),
        ("https://cointelegraph.com/b", 2),
        ("https://decrypt.co/c", 3),
        ("https://theblock.co/d", 4),
        ("https://other.com/e", 5),
        ("https://other2.com/f", 6),
    ]
    selected = researcher._select_top(ranked, "https://layerzero.network", top_n=5)
    assert "https://layerzero.network" in selected
    assert len(selected) == 5


def test_select_top_n_does_not_duplicate_official_url():
    """Se a official_url já está no ranking, não duplica."""
    researcher = WebResearcher()
    ranked = [
        ("https://layerzero.network", 1),
        ("https://coindesk.com/a", 2),
        ("https://cointelegraph.com/b", 3),
    ]
    selected = researcher._select_top(ranked, "https://layerzero.network", top_n=5)
    assert selected.count("https://layerzero.network") == 1


def test_blocked_and_preferred_domains_sets_exist():
    assert "reddit.com" in BLOCKED_DOMAINS
    assert "x.com" in BLOCKED_DOMAINS
    assert "youtube.com" in BLOCKED_DOMAINS
    assert "coindesk.com" in PREFERRED_DOMAINS
    assert "coingecko.com" in PREFERRED_DOMAINS
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/test_airdrop_web_researcher_filtering.py -v`
Expected: All FAIL (`ModuleNotFoundError`).

- [ ] **Step 4: Implement filtering/ranking in `web_researcher.py`**

Create `app/services/airdrop/web_researcher.py`:

```python
"""
Web Researcher para Airdrop Post Generator.

Coleta contexto público sobre um projeto cripto a partir de:
- 3 buscas no DuckDuckGo (via ddgs)
- Fetch HTTP das URLs ranqueadas
- Página oficial fornecida no request (sempre incluída)

Aplica blocklist (social/vídeo), whitelist boost (fontes cripto conhecidas)
e trunca conteúdo extraído por fonte.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple
from urllib.parse import urlparse

from loguru import logger


BLOCKED_DOMAINS = {
    "reddit.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com",
    "telegram.org", "discord.com",
}

PREFERRED_DOMAINS = {
    "coinmarketcap.com", "coingecko.com", "cryptorank.io",
    "coindesk.com", "cointelegraph.com", "decrypt.co",
    "theblock.co", "cryptoslate.com", "messari.io",
    "airdrops.io", "coinlist.co",
}

# Quanto subtraímos do rank pra cada domínio whitelisted (ranks menores = melhores)
WHITELIST_BOOST = 100

# Limite de caracteres extraídos por URL
SOURCE_TRUNCATE_CHARS = 3000

# Top-N URLs efetivamente consultadas (DDG + oficial)
TOP_N_URLS = 5


class ResearchFailedError(Exception):
    """Levantada quando não há nenhuma fonte primária disponível."""


@dataclass
class ResearchResult:
    sources_text: str
    sources_used: List[str] = field(default_factory=list)


class WebResearcher:
    """Coleta contexto web sobre um projeto cripto."""

    def _domain_of(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower().lstrip("www.")
        except Exception:
            return ""

    def _dedup_by_domain(
        self, candidates: List[Tuple[str, int]]
    ) -> List[Tuple[str, int]]:
        """
        Recebe lista de (url, rank). Mantém apenas a melhor URL (menor rank)
        por domínio. Preserva a ordem original (estável).
        """
        seen: dict[str, Tuple[str, int]] = {}
        for url, rank in candidates:
            domain = self._domain_of(url)
            if not domain:
                continue
            if domain not in seen or rank < seen[domain][1]:
                seen[domain] = (url, rank)
        # ordena por rank ascendente
        return sorted(seen.values(), key=lambda t: t[1])

    def _apply_blocklist(
        self, candidates: List[Tuple[str, int]]
    ) -> List[Tuple[str, int]]:
        """Remove URLs cujo domínio (ou sufixo) esteja na BLOCKED_DOMAINS."""
        result = []
        for url, rank in candidates:
            domain = self._domain_of(url)
            blocked = any(
                domain == bd or domain.endswith("." + bd) for bd in BLOCKED_DOMAINS
            )
            if not blocked:
                result.append((url, rank))
        return result

    def _apply_whitelist_boost(
        self, candidates: List[Tuple[str, int]]
    ) -> List[Tuple[str, int]]:
        """
        Para cada URL cujo domínio está em PREFERRED_DOMAINS, subtrai WHITELIST_BOOST
        do rank (ranks menores ganham prioridade na ordenação).
        """
        result = []
        for url, rank in candidates:
            domain = self._domain_of(url)
            is_preferred = any(
                domain == pd or domain.endswith("." + pd) for pd in PREFERRED_DOMAINS
            )
            new_rank = rank - WHITELIST_BOOST if is_preferred else rank
            result.append((url, new_rank))
        return sorted(result, key=lambda t: t[1])

    def _select_top(
        self,
        ranked: List[Tuple[str, int]],
        official_url: str,
        top_n: int = TOP_N_URLS,
    ) -> List[str]:
        """
        Seleciona as top-N URLs. Sempre inclui a official_url (sem duplicar).
        """
        urls = [u for u, _ in ranked]
        # Garante que official_url está incluída como primeira (mas sem duplicar)
        if official_url in urls:
            urls.remove(official_url)
        selected = [official_url] + urls[: max(0, top_n - 1)]
        return selected[:top_n]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_airdrop_web_researcher_filtering.py -v`
Expected: All 6 PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/airdrop/__init__.py app/services/airdrop/web_researcher.py tests/unit/test_airdrop_web_researcher_filtering.py
git commit -m "feat: add WebResearcher URL filtering and ranking logic"
```

---

### Task 6: `WebResearcher` — HTML fetch & text extraction

This task adds the I/O methods: fetch + parse HTML.

**Files:**
- Modify: `app/services/airdrop/web_researcher.py`
- Create: `tests/unit/test_airdrop_web_researcher_extraction.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_airdrop_web_researcher_extraction.py`:

```python
"""
Testes de extração de HTML do WebResearcher.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.airdrop.web_researcher import (
    SOURCE_TRUNCATE_CHARS,
    WebResearcher,
)


@pytest.fixture
def html_with_noise():
    return """
    <html>
      <head><title>LayerZero</title></head>
      <body>
        <nav>Menu home about</nav>
        <script>console.log('x')</script>
        <style>.x{color:red}</style>
        <main>
          <h1>LayerZero</h1>
          <p>O LayerZero é um protocolo de mensagens entre blockchains.</p>
          <p>Possui um token chamado ZRO.</p>
        </main>
        <footer>Footer text</footer>
      </body>
    </html>
    """


def test_extract_text_strips_scripts_styles_nav_footer(html_with_noise):
    researcher = WebResearcher()
    text = researcher._extract_text(html_with_noise)
    assert "console.log" not in text
    assert ".x{color:red}" not in text
    assert "Menu home about" not in text
    assert "Footer text" not in text
    assert "protocolo de mensagens" in text
    assert "ZRO" in text


def test_extract_text_truncates_to_max_chars():
    researcher = WebResearcher()
    long_html = "<html><body><p>" + ("palavra " * 5000) + "</p></body></html>"
    text = researcher._extract_text(long_html)
    assert len(text) <= SOURCE_TRUNCATE_CHARS


@pytest.mark.asyncio
async def test_fetch_url_returns_text_on_200(html_with_noise):
    researcher = WebResearcher()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mock_response.text = html_with_noise

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    text = await researcher._fetch_url(mock_client, "https://example.com")
    assert text is not None
    assert "protocolo de mensagens" in text


@pytest.mark.asyncio
async def test_fetch_url_returns_none_on_non_html_content_type():
    researcher = WebResearcher()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/pdf"}
    mock_response.text = "%PDF-1.4..."

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    text = await researcher._fetch_url(mock_client, "https://example.com/doc.pdf")
    assert text is None


@pytest.mark.asyncio
async def test_fetch_url_returns_none_on_http_error():
    researcher = WebResearcher()
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
    text = await researcher._fetch_url(mock_client, "https://example.com")
    assert text is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_airdrop_web_researcher_extraction.py -v`
Expected: All FAIL with `AttributeError: 'WebResearcher' object has no attribute '_extract_text'`.

- [ ] **Step 3: Add extraction + fetch methods**

In `app/services/airdrop/web_researcher.py`, add the following imports at the top (next to existing imports):

```python
import httpx
from bs4 import BeautifulSoup
```

Then add inside the `WebResearcher` class (after `_select_top`):

```python
    def _extract_text(self, html: str) -> str:
        """
        Extrai texto limpo do HTML.
        - Remove <script>, <style>, <nav>, <footer>, <header>, <aside>
        - Normaliza whitespace
        - Trunca a SOURCE_TRUNCATE_CHARS
        """
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Normaliza múltiplos espaços
        text = " ".join(text.split())
        return text[:SOURCE_TRUNCATE_CHARS]

    async def _fetch_url(
        self, client: httpx.AsyncClient, url: str
    ) -> str | None:
        """
        Fetch HTTP de uma URL. Retorna texto extraído ou None se:
        - Erro HTTP (timeout, 4xx, 5xx, conexão)
        - Content-Type não é HTML
        """
        try:
            response = await client.get(url, timeout=10.0, follow_redirects=True)
            if response.status_code != 200:
                logger.warning(f"WebResearcher: status {response.status_code} para {url}")
                return None
            content_type = response.headers.get("content-type", "").lower()
            if "html" not in content_type:
                logger.debug(f"WebResearcher: pulando {url} (content-type={content_type})")
                return None
            return self._extract_text(response.text)
        except Exception as e:
            logger.warning(f"WebResearcher: falha ao fetch {url}: {e}")
            return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_airdrop_web_researcher_extraction.py -v`
Expected: All 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/airdrop/web_researcher.py tests/unit/test_airdrop_web_researcher_extraction.py
git commit -m "feat: add HTML fetch and text extraction to WebResearcher"
```

---

### Task 7: `WebResearcher` — DDG search and full orchestration

Adds the public `gather_context()` method that ties together DDG search → filtering → fetch → consolidated text block.

**Files:**
- Modify: `app/services/airdrop/web_researcher.py`
- Create: `tests/unit/test_airdrop_web_researcher_orchestration.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_airdrop_web_researcher_orchestration.py`:

```python
"""
Testes de orquestração completa do WebResearcher.gather_context().
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.airdrop.web_researcher import (
    ResearchFailedError,
    WebResearcher,
)


@pytest.fixture
def mock_ddg_results():
    return [
        {"href": "https://coindesk.com/layerzero-airdrop", "title": "x", "body": "x"},
        {"href": "https://coingecko.com/layerzero", "title": "x", "body": "x"},
        {"href": "https://reddit.com/r/layerzero", "title": "x", "body": "x"},
        {"href": "https://random-blog.com/post", "title": "x", "body": "x"},
    ]


@pytest.fixture
def mock_html_response():
    return """
    <html><body><main>
      <p>LayerZero é um protocolo de interoperabilidade entre blockchains.</p>
      <p>Permite mensagens cross-chain de forma segura.</p>
    </main></body></html>
    """


@pytest.mark.asyncio
async def test_gather_context_returns_consolidated_text(
    mock_ddg_results, mock_html_response
):
    researcher = WebResearcher()

    # Mock DDGS to return results per query
    mock_ddgs_instance = MagicMock()
    mock_ddgs_instance.text = MagicMock(return_value=iter(mock_ddg_results))
    mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
    mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = mock_html_response

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.airdrop.web_researcher.DDGS", return_value=mock_ddgs_instance):
        with patch("app.services.airdrop.web_researcher.httpx.AsyncClient", return_value=mock_client):
            result = await researcher.gather_context(
                project_name="LayerZero",
                official_url="https://layerzero.network",
            )

    assert "LayerZero" in result.sources_text
    assert "[FONTE 1 - OFICIAL]" in result.sources_text
    assert "https://layerzero.network" in result.sources_used
    # reddit não deve aparecer (blocklist)
    assert "reddit.com" not in result.sources_text


@pytest.mark.asyncio
async def test_gather_context_raises_when_official_url_fails():
    """Se a página oficial falha e DDG não retorna nada, levanta erro."""
    researcher = WebResearcher()

    mock_ddgs_instance = MagicMock()
    mock_ddgs_instance.text = MagicMock(return_value=iter([]))
    mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
    mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("network down"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.airdrop.web_researcher.DDGS", return_value=mock_ddgs_instance):
        with patch("app.services.airdrop.web_researcher.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ResearchFailedError):
                await researcher.gather_context(
                    project_name="Bogus",
                    official_url="https://bogus.example",
                )


@pytest.mark.asyncio
async def test_gather_context_continues_when_secondary_url_fails(
    mock_ddg_results, mock_html_response
):
    """Se algumas URLs secundárias falham, processo continua."""
    researcher = WebResearcher()

    mock_ddgs_instance = MagicMock()
    mock_ddgs_instance.text = MagicMock(return_value=iter(mock_ddg_results))
    mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
    mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

    mock_success_response = MagicMock()
    mock_success_response.status_code = 200
    mock_success_response.headers = {"content-type": "text/html"}
    mock_success_response.text = mock_html_response

    call_count = {"n": 0}

    async def flaky_get(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise Exception("flake")
        return mock_success_response

    mock_client = MagicMock()
    mock_client.get = flaky_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.airdrop.web_researcher.DDGS", return_value=mock_ddgs_instance):
        with patch("app.services.airdrop.web_researcher.httpx.AsyncClient", return_value=mock_client):
            result = await researcher.gather_context(
                project_name="LayerZero",
                official_url="https://layerzero.network",
            )

    # Pelo menos a oficial entrou
    assert "[FONTE 1 - OFICIAL]" in result.sources_text
    assert len(result.sources_used) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_airdrop_web_researcher_orchestration.py -v`
Expected: All FAIL with `AttributeError: 'WebResearcher' object has no attribute 'gather_context'`.

- [ ] **Step 3: Add DDG search + orchestration**

In `app/services/airdrop/web_researcher.py`, add the import at the top:

```python
import asyncio

try:
    from ddgs import DDGS  # ddgs >= 7.0
except ImportError:  # pragma: no cover
    from duckduckgo_search import DDGS  # legacy fallback
```

Then add the `gather_context` method to the `WebResearcher` class:

```python
    DDG_RESULTS_PER_QUERY = 4

    def _build_queries(self, project_name: str) -> List[str]:
        return [
            f"{project_name} airdrop",
            f"{project_name} como participar",
            f"{project_name} token tokenomics",
        ]

    def _search_ddg(self, project_name: str) -> List[Tuple[str, int]]:
        """
        Executa as 3 buscas no DDG (síncrono via ddgs). Retorna lista de
        (url, rank) onde rank é a posição global (menor = melhor).
        """
        candidates: List[Tuple[str, int]] = []
        global_rank = 0
        try:
            with DDGS() as ddgs:
                for query in self._build_queries(project_name):
                    try:
                        results = list(
                            ddgs.text(query, max_results=self.DDG_RESULTS_PER_QUERY)
                        )
                    except Exception as e:
                        logger.warning(f"WebResearcher: DDG falhou para '{query}': {e}")
                        continue
                    for item in results:
                        url = item.get("href") or item.get("url") or ""
                        if url:
                            global_rank += 1
                            candidates.append((url, global_rank))
        except Exception as e:
            logger.warning(f"WebResearcher: erro ao iniciar DDGS: {e}")
        return candidates

    async def gather_context(
        self,
        project_name: str,
        official_url: str,
    ) -> ResearchResult:
        """
        Pesquisa, fetch e consolida texto sobre o projeto.

        Raises:
            ResearchFailedError: se a página oficial não pôde ser baixada
                e nenhuma fonte secundária foi obtida.
        """
        # 1) busca DDG (síncrono — rodar em thread pra não bloquear loop)
        raw_candidates = await asyncio.to_thread(self._search_ddg, project_name)

        # 2) filtragem
        candidates = self._apply_blocklist(raw_candidates)
        candidates = self._dedup_by_domain(candidates)
        candidates = self._apply_whitelist_boost(candidates)

        # 3) seleção (oficial sempre incluída como FONTE 1)
        selected_urls = self._select_top(candidates, official_url, top_n=TOP_N_URLS)
        logger.info(f"WebResearcher: vai fetch {len(selected_urls)} URLs para '{project_name}'")

        # 4) fetch paralelo
        async with httpx.AsyncClient() as client:
            fetch_tasks = [self._fetch_url(client, url) for url in selected_urls]
            texts = await asyncio.gather(*fetch_tasks, return_exceptions=False)

        # 5) emparelhar urls x textos, descartar falhas
        official_text: str | None = None
        secondary_blocks: List[Tuple[str, str]] = []
        for url, text in zip(selected_urls, texts):
            if not text:
                continue
            if url == official_url:
                official_text = text
            else:
                secondary_blocks.append((url, text))

        # 6) regra dura: precisa de pelo menos a oficial OU 1 secundária
        if official_text is None and not secondary_blocks:
            raise ResearchFailedError(
                f"Não foi possível baixar nenhuma fonte para '{project_name}'"
            )

        # 7) montar bloco consolidado
        parts = [f'=== FONTES PESQUISADAS PARA "{project_name}" ===\n']
        sources_used: List[str] = []
        index = 1

        if official_text is not None:
            parts.append(f"[FONTE {index} - OFICIAL] {official_url}\n{official_text}\n")
            sources_used.append(official_url)
            index += 1
        else:
            logger.warning(
                f"WebResearcher: página oficial {official_url} indisponível, "
                "seguindo só com secundárias"
            )

        for url, text in secondary_blocks:
            parts.append(f"[FONTE {index}] {url}\n{text}\n")
            sources_used.append(url)
            index += 1

        parts.append("=== FIM DAS FONTES ===")
        return ResearchResult(
            sources_text="\n".join(parts),
            sources_used=sources_used,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_airdrop_web_researcher_orchestration.py -v`
Expected: All 3 PASS.

- [ ] **Step 5: Run all WebResearcher tests together**

Run: `pytest tests/unit/test_airdrop_web_researcher_*.py -v`
Expected: All ~14 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/airdrop/web_researcher.py tests/unit/test_airdrop_web_researcher_orchestration.py
git commit -m "feat: add DDG search and gather_context orchestration to WebResearcher"
```

---

### Task 8: Create airdrop prompts module

**Files:**
- Create: `app/services/ai/prompts/airdrop_prompts.py`
- Create: `tests/unit/test_airdrop_prompts.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_airdrop_prompts.py`:

```python
"""
Testes do módulo de prompts de airdrop.
"""
from app.services.ai.prompts.airdrop_prompts import (
    AIRDROP_SYSTEM_PROMPT,
    build_airdrop_user_prompt,
)


def test_system_prompt_contains_critical_rules():
    p = AIRDROP_SYSTEM_PROMPT.lower()
    assert "neutro" in p
    assert "não constitui recomendação" in p or "nao constitui recomendacao" in p
    assert "fontes" in p


def test_system_prompt_forbids_investment_language():
    p = AIRDROP_SYSTEM_PROMPT.lower()
    # Frases proibidas devem aparecer como exemplos do que NÃO usar
    assert "lucro" in p or "garantia" in p or "investir" in p


def test_user_prompt_injects_all_variables():
    result = build_airdrop_user_prompt(
        project_name="LayerZero",
        official_url="https://layerzero.network",
        referral_url="https://ref.example/abc",
        sources_text="=== FONTES ===\n[FONTE 1] ...",
        current_date="2026-05-21",
    )
    assert "LayerZero" in result
    assert "https://layerzero.network" in result
    assert "https://ref.example/abc" in result
    assert "=== FONTES ===" in result
    assert "2026-05-21" in result


def test_user_prompt_specifies_word_range():
    result = build_airdrop_user_prompt(
        project_name="X",
        official_url="https://x.com",
        referral_url="https://x.com/r",
        sources_text="",
        current_date="2026-01-01",
    )
    assert "500" in result and "750" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_airdrop_prompts.py -v`
Expected: All FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Create prompts module**

Create `app/services/ai/prompts/airdrop_prompts.py`:

```python
"""
Prompts para geração de posts sobre airdrops de projetos cripto.

Tom obrigatório: neutro, educacional, jornalístico.
Compliance: NFA (Not Financial Advice) — não recomendar investimento.
"""

AIRDROP_SYSTEM_PROMPT = """
Você é um redator do portal VerticeCripto especializado em conteúdo educacional
sobre criptomoedas. Sua tarefa é escrever um artigo informativo sobre um
projeto cripto e seu programa de airdrop.

TOM OBRIGATÓRIO:
- Neutro, jornalístico, educativo
- NUNCA recomende investimentos ou afirme retorno financeiro
- NUNCA crie expectativa de valor monetário do airdrop
- NUNCA use frases como: "oportunidade imperdível", "garantia de retorno",
  "lucro certo", "vale a pena investir", "momento ideal para investir"
- Use linguagem como: "o projeto afirma", "segundo o site oficial",
  "de acordo com a documentação", "analistas apontam"

REGRAS DE FATO (CRÍTICO):
- Use APENAS informações presentes nas FONTES fornecidas pelo usuário
- Se a fonte não traz uma informação (ex: data do airdrop, valor do token),
  NÃO invente — escreva "não há data confirmada" ou omita
- NUNCA cite números, preços, datas ou estatísticas que não estejam nas fontes
- Atribua afirmações específicas: "segundo a CoinDesk", "conforme o site oficial"

ESTRUTURA OBRIGATÓRIA (500-750 palavras, em português brasileiro):

1. Introdução (1 parágrafo curto, antes de qualquer heading)
   - O que é o projeto em 2-3 frases, de forma neutra

2. ## Sobre o projeto <nome>
   - O que faz, qual problema resolve, quem está por trás (se nas fontes)
   - Foco educacional

3. ## O programa de airdrop
   - O que se sabe publicamente sobre a campanha
   - Se não houver detalhes confirmados: deixar claro que ainda não há
     informações oficiais e que potenciais usuários podem se cadastrar
     antecipadamente

4. ## Como participar
   - Passo-a-passo prático baseado no que as fontes descrevem
   - Incluir LINK INLINE de referência no momento "para se cadastrar,
     acesse [aqui]({REFERRAL_URL})"
   - Se não houver instruções claras nas fontes, descreva o caminho geral
     (criar conta no site oficial, conectar carteira, etc.)

5. ## Informações importantes
   - Bloco fixo no final com o seguinte texto, exatamente:
     "O link de cadastro neste artigo é um link de referência. Você também
     pode acessar o projeto diretamente pelo site oficial:
     [<OFFICIAL_URL>](<OFFICIAL_URL>).
     Este conteúdo é meramente informativo e não constitui recomendação
     de investimento. Airdrops podem ter requisitos, restrições geográficas
     e datas que mudam — sempre verifique as condições atualizadas no
     site oficial antes de participar."
   - Substitua <OFFICIAL_URL> pelo link oficial real.

FORMATO DE SAÍDA (responda APENAS com este JSON, sem ```json):
{
  "title": "...",
  "slug": "...",
  "excerpt": "...",
  "content_markdown": "...",
  "meta_title": "...",
  "meta_description": "..."
}

REGRAS DOS CAMPOS:
- title: 30-100 caracteres, sem clickbait, neutro
- slug: lowercase, hyphens, sem acentos
- excerpt: 80-200 caracteres, neutro
- content_markdown: 500-750 palavras, com a estrutura acima
- meta_title: máximo 70 caracteres
- meta_description: 120-180 caracteres
""".strip()


def build_airdrop_user_prompt(
    project_name: str,
    official_url: str,
    referral_url: str,
    sources_text: str,
    current_date: str,
) -> str:
    """
    Monta o prompt de usuário injetando dados do projeto e contexto pesquisado.
    """
    return f"""
DATA ATUAL: {current_date}

PROJETO: {project_name}
LINK OFICIAL: {official_url}
LINK DE REFERÊNCIA (operador do portal — usar no inline da seção "Como participar"):
{referral_url}

OBRIGATÓRIO:
- O artigo final precisa ter entre 500 e 750 palavras.
- O LINK DE REFERÊNCIA acima deve aparecer pelo menos uma vez como link
  markdown inline na seção "## Como participar".
- O LINK OFICIAL acima deve aparecer como link markdown no bloco final
  "## Informações importantes".

CONTEXTO PESQUISADO NA WEB (use APENAS estas fontes — não invente nada):

{sources_text}

Agora gere o artigo no formato JSON especificado no system prompt.
""".strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_airdrop_prompts.py -v`
Expected: All 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/ai/prompts/airdrop_prompts.py tests/unit/test_airdrop_prompts.py
git commit -m "feat: add airdrop post prompts module"
```

---

### Task 9: `AirdropPostGenerator` — Claude call + JSON parsing

This task creates the generator with only the Claude path (no fallback, no post-validation regeneration yet). Those come in tasks 10 and 11.

**Files:**
- Create: `app/services/airdrop/airdrop_post_generator.py`
- Create: `tests/unit/test_airdrop_post_generator_claude.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_airdrop_post_generator_claude.py`:

```python
"""
Testa o caminho feliz do AirdropPostGenerator usando Claude.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator
from app.services.airdrop.web_researcher import ResearchResult


def _fake_claude_response(payload: dict):
    """Simula a estrutura de retorno do anthropic SDK."""
    response = MagicMock()
    block = MagicMock()
    block.text = json.dumps(payload)
    response.content = [block]
    return response


@pytest.mark.asyncio
async def test_generate_returns_article_dict_on_success():
    generator = AirdropPostGenerator()
    # força Claude disponível com client mockado
    generator.claude_available = True
    generator.claude_client = MagicMock()

    article_payload = {
        "title": "LayerZero: o protocolo cross-chain e seu programa de airdrop",
        "slug": "layerzero-protocolo-cross-chain-airdrop",
        "excerpt": "Conheca o LayerZero, protocolo de interoperabilidade entre blockchains.",
        "content_markdown": (
            "Introducao curta sobre o projeto.\n\n"
            "## Sobre o projeto LayerZero\n\nTexto.\n\n"
            "## O programa de airdrop\n\nTexto.\n\n"
            "## Como participar\n\nAcesse [aqui](https://ref.example/abc) para se cadastrar.\n\n"
            "## Informações importantes\n\nSite oficial: [https://layerzero.network](https://layerzero.network). "
            "Este conteudo nao constitui recomendacao de investimento."
        ),
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "LayerZero e um protocolo de interoperabilidade. Saiba como participar "
            "do airdrop pelo site oficial."
        ),
    }

    generator.claude_client.messages = MagicMock()
    generator.claude_client.messages.create = AsyncMock(
        return_value=_fake_claude_response(article_payload)
    )

    research = ResearchResult(
        sources_text="=== FONTES ===\n[FONTE 1] x",
        sources_used=["https://layerzero.network"],
    )
    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_image", AsyncMock(return_value="https://img/x.jpg")):
            result = await generator.generate(
                project_name="LayerZero",
                official_url="https://layerzero.network",
                referral_url="https://ref.example/abc",
            )

    assert result is not None
    assert result["title"].startswith("LayerZero")
    assert "https://ref.example/abc" in result["content_markdown"]
    assert result["image_url"] == "https://img/x.jpg"
    assert result["sources_used"] == ["https://layerzero.network"]
    assert result["word_count"] >= 1


@pytest.mark.asyncio
async def test_generate_returns_none_when_claude_returns_invalid_json():
    generator = AirdropPostGenerator()
    generator.claude_available = True
    generator.claude_client = MagicMock()

    bad_response = MagicMock()
    block = MagicMock()
    block.text = "this is not json"
    bad_response.content = [block]

    generator.claude_client.messages = MagicMock()
    generator.claude_client.messages.create = AsyncMock(return_value=bad_response)
    # também desativa fallback Gemini pra isolar este teste
    generator.content_generator = None

    research = ResearchResult(sources_text="x", sources_used=["https://x.com"])
    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        result = await generator.generate(
            project_name="X",
            official_url="https://x.com",
            referral_url="https://x.com/r",
        )
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_airdrop_post_generator_claude.py -v`
Expected: All FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement the generator skeleton**

Create `app/services/airdrop/airdrop_post_generator.py`:

```python
"""
Airdrop Post Generator

Orquestra: WebResearcher → Claude Sonnet 4.6 (com fallback Gemini)
→ artigo dict pronto pra publicação.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Optional

from loguru import logger
from slugify import slugify

from app.core.config import settings
from app.services.ai.prompts.airdrop_prompts import (
    AIRDROP_SYSTEM_PROMPT,
    build_airdrop_user_prompt,
)
from app.services.airdrop.web_researcher import ResearchResult, WebResearcher

try:
    from anthropic import AsyncAnthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:  # pragma: no cover
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK não instalado. Airdrop generator vai depender só do Gemini.")


class AirdropPostGenerator:
    """Gera posts sobre airdrops a partir de pesquisa web + Claude."""

    CLAUDE_MODEL = "claude-sonnet-4-6"
    MAX_TOKENS = 3000
    TEMPERATURE = 0.5

    def __init__(self):
        self.web_researcher = WebResearcher()

        self.claude_client = None
        self.claude_available = False
        self._init_claude()

        # fallback (lazy)
        self._content_generator = None
        # lazy image generator
        self._image_generator = None

    def _init_claude(self) -> None:
        if not ANTHROPIC_AVAILABLE:
            return
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("AirdropPostGenerator: ANTHROPIC_API_KEY ausente")
            return
        try:
            self.claude_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.claude_available = True
            logger.info(f"AirdropPostGenerator: Claude pronto ({self.CLAUDE_MODEL})")
        except Exception as e:
            logger.error(f"AirdropPostGenerator: falha ao iniciar Claude: {e}")

    @property
    def content_generator(self):
        """Fallback Gemini (lazy)."""
        if self._content_generator is None:
            from app.services.ai.content_generator import ContentGenerator

            self._content_generator = ContentGenerator()
        return self._content_generator

    @content_generator.setter
    def content_generator(self, value):
        self._content_generator = value

    @property
    def image_generator(self):
        if self._image_generator is None:
            from app.services.ai.image_generator import ImageGenerator

            self._image_generator = ImageGenerator()
        return self._image_generator

    async def generate(
        self,
        project_name: str,
        official_url: str,
        referral_url: str,
    ) -> Optional[Dict]:
        """
        Roda o fluxo completo: pesquisa → IA → article dict.

        Returns:
            Dict no shape esperado por ArticlePublisher.publish_article, com
            campos extras `sources_used` e `word_count`, ou None em falha.
        """
        research = await self.web_researcher.gather_context(project_name, official_url)

        user_prompt = build_airdrop_user_prompt(
            project_name=project_name,
            official_url=official_url,
            referral_url=referral_url,
            sources_text=research.sources_text,
            current_date=datetime.utcnow().strftime("%Y-%m-%d"),
        )

        article = await self._generate_with_claude(user_prompt)

        if article is None:
            logger.error("AirdropPostGenerator: Claude não retornou artigo válido")
            return None

        # garante slug
        if not article.get("slug"):
            article["slug"] = slugify(article.get("title", project_name))

        # gera imagem (não-bloqueante)
        article["image_url"] = await self._generate_image(article)

        article["sources_used"] = research.sources_used
        article["word_count"] = len(article.get("content_markdown", "").split())
        return article

    async def _generate_with_claude(self, user_prompt: str) -> Optional[Dict]:
        """Chama Claude e parsa o JSON de saída. Retorna None em falha."""
        if not self.claude_available or self.claude_client is None:
            return None
        try:
            response = await self.claude_client.messages.create(
                model=self.CLAUDE_MODEL,
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
                system=AIRDROP_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text
            return self._parse_json(text)
        except Exception as e:
            logger.error(f"AirdropPostGenerator: Claude falhou: {e}")
            return None

    def _parse_json(self, text: str) -> Optional[Dict]:
        """Tenta parsear JSON, removendo cercas ``` se presentes."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # remove cercas estilo ```json ... ```
            cleaned = cleaned.split("```", 2)[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.rsplit("```", 1)[0]
        try:
            data = json.loads(cleaned.strip())
            required = {"title", "content_markdown"}
            if not required.issubset(data.keys()):
                logger.error(f"AirdropPostGenerator: JSON sem campos obrigatórios: {data.keys()}")
                return None
            return data
        except json.JSONDecodeError as e:
            logger.error(f"AirdropPostGenerator: JSON inválido: {e}")
            return None

    async def _generate_image(self, article: Dict) -> Optional[str]:
        """Gera imagem, retorna None em falha (não bloqueia)."""
        try:
            return await self.image_generator.generate_and_upload_image(
                article["title"],
                article["content_markdown"],
                category_name="airdrop",
            )
        except Exception as e:
            logger.warning(f"AirdropPostGenerator: imagem falhou: {e}")
            return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_airdrop_post_generator_claude.py -v`
Expected: Both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/airdrop/airdrop_post_generator.py tests/unit/test_airdrop_post_generator_claude.py
git commit -m "feat: add AirdropPostGenerator with Claude integration"
```

---

### Task 10: Add Gemini fallback to `AirdropPostGenerator`

When Claude fails or is unavailable, try Gemini via `ContentGenerator`. The existing `ContentGenerator` doesn't have a generic "given a prompt, return JSON" method, so we'll use its internal Gemini client directly via a small helper added to the generator.

**Files:**
- Modify: `app/services/airdrop/airdrop_post_generator.py`
- Create: `tests/unit/test_airdrop_post_generator_fallback.py`

- [ ] **Step 1: Look up Gemini client access**

Run: `grep -n "gemini_client\|self.gemini\|GenerativeModel\|generate_content" app/services/ai/content_generator.py | head -40`

You should see something like a `self.gemini_client` or model reference. We will reuse that path. If `ContentGenerator` exposes the client as `self.gemini_client` (or similar), our generator will reach in and call it. If the attribute name differs, adapt the next step.

(Note: `ContentGenerator` uses `google-genai >= 1.5.0` — the new SDK; the method signature varies. The fallback is a defensive path — if calling it raises, we just log and return None.)

- [ ] **Step 2: Write the failing test**

Create `tests/unit/test_airdrop_post_generator_fallback.py`:

```python
"""
Testes do fallback Gemini quando Claude falha.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator
from app.services.airdrop.web_researcher import ResearchResult


@pytest.mark.asyncio
async def test_falls_back_to_gemini_when_claude_unavailable():
    generator = AirdropPostGenerator()
    # simula Claude indisponível
    generator.claude_available = False
    generator.claude_client = None

    article_payload = {
        "title": "LayerZero airdrop: como participar pelo site oficial em 2026",
        "slug": "layerzero-airdrop-como-participar",
        "excerpt": "Conheca o LayerZero, protocolo de interoperabilidade entre blockchains, e como participar.",
        "content_markdown": (
            "Introducao.\n\n"
            "## Sobre\n\nTexto sobre crypto e blockchain.\n\n"
            "## O programa de airdrop\n\nTexto.\n\n"
            "## Como participar\n\nAcesse [aqui](https://ref.example/abc).\n\n"
            "## Informacoes importantes\n\n[https://layerzero.network](https://layerzero.network). "
            "Nao constitui recomendacao."
        ),
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "LayerZero, protocolo de interoperabilidade entre blockchains, abre cadastro "
            "antecipado para airdrop pelo site oficial."
        ),
    }

    # mock do método de fallback que vamos chamar
    mock_gemini = AsyncMock(return_value=article_payload)

    research = ResearchResult(sources_text="x", sources_used=["https://layerzero.network"])
    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_with_gemini", mock_gemini):
            with patch.object(generator, "_generate_image", AsyncMock(return_value=None)):
                result = await generator.generate(
                    project_name="LayerZero",
                    official_url="https://layerzero.network",
                    referral_url="https://ref.example/abc",
                )

    assert result is not None
    assert result["title"].startswith("LayerZero")
    mock_gemini.assert_called_once()


@pytest.mark.asyncio
async def test_returns_none_when_both_models_fail():
    generator = AirdropPostGenerator()
    generator.claude_available = False
    generator.claude_client = None

    research = ResearchResult(sources_text="x", sources_used=["https://x.com"])
    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_with_gemini", AsyncMock(return_value=None)):
            result = await generator.generate(
                project_name="X",
                official_url="https://x.com",
                referral_url="https://x.com/r",
            )
    assert result is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_airdrop_post_generator_fallback.py -v`
Expected: FAIL — `_generate_with_gemini` doesn't exist yet, and `generate()` returns None too early.

- [ ] **Step 4: Add the Gemini fallback method and wire it into `generate()`**

In `app/services/airdrop/airdrop_post_generator.py`:

A) Modify `generate()` — after the Claude attempt, add a fallback. Find this block:

```python
        article = await self._generate_with_claude(user_prompt)

        if article is None:
            logger.error("AirdropPostGenerator: Claude não retornou artigo válido")
            return None
```

Replace with:

```python
        article = await self._generate_with_claude(user_prompt)

        if article is None:
            logger.warning("AirdropPostGenerator: Claude falhou, tentando Gemini")
            article = await self._generate_with_gemini(user_prompt)

        if article is None:
            logger.error("AirdropPostGenerator: ambos os modelos falharam")
            return None
```

B) Add the `_generate_with_gemini` method to the class:

```python
    async def _generate_with_gemini(self, user_prompt: str) -> Optional[Dict]:
        """
        Fallback usando google-genai (Gemini Flash).

        Tenta reutilizar o client já configurado no ContentGenerator existente,
        para não duplicar configuração. Se algo der errado, retorna None.
        """
        try:
            cg = self.content_generator  # lazy import
            if cg is None:
                return None
            # Combina system + user num único prompt (Gemini usa um prompt só)
            combined = (
                AIRDROP_SYSTEM_PROMPT
                + "\n\n---\n\n"
                + user_prompt
            )

            # google-genai >= 1.5: cg.client.aio.models.generate_content
            client = getattr(cg, "gemini_client", None) or getattr(cg, "client", None)
            if client is None:
                logger.warning("AirdropPostGenerator: ContentGenerator sem client Gemini")
                return None

            response = await client.aio.models.generate_content(
                model=getattr(cg, "GEMINI_MODEL", "gemini-2.5-flash"),
                contents=combined,
            )
            text = getattr(response, "text", None)
            if not text:
                return None
            return self._parse_json(text)
        except Exception as e:
            logger.error(f"AirdropPostGenerator: Gemini fallback falhou: {e}")
            return None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_airdrop_post_generator_fallback.py -v`
Expected: Both PASS.

- [ ] **Step 6: Run all generator tests**

Run: `pytest tests/unit/test_airdrop_post_generator_*.py -v`
Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add app/services/airdrop/airdrop_post_generator.py tests/unit/test_airdrop_post_generator_fallback.py
git commit -m "feat: add Gemini fallback to AirdropPostGenerator"
```

---

### Task 11: Post-generation validation with regenerate-once

Validate that the generated content includes the referral link inline and the official URL in the disclosure block. If missing, regenerate **once** with an explicit correction instruction.

**Files:**
- Modify: `app/services/airdrop/airdrop_post_generator.py`
- Create: `tests/unit/test_airdrop_post_generator_validation.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_airdrop_post_generator_validation.py`:

```python
"""
Testes da validação pós-geração (link de referência + link oficial + disclosure).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator
from app.services.airdrop.web_researcher import ResearchResult


def _article(content: str) -> dict:
    return {
        "title": "LayerZero airdrop: o que e e como participar do programa em 2026",
        "slug": "layerzero-airdrop-2026",
        "excerpt": "Conheca o LayerZero e como participar do programa de airdrop pelo site oficial.",
        "content_markdown": content,
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "LayerZero abre cadastro para airdrop. Saiba o que e o protocolo e como "
            "participar pelo site oficial."
        ),
    }


@pytest.mark.asyncio
async def test_regenerates_when_referral_url_missing():
    generator = AirdropPostGenerator()
    generator.claude_available = True
    generator.claude_client = MagicMock()

    bad = _article(
        "Intro.\n\n## Sobre\n\nTexto.\n\n"
        "## Como participar\n\nAcesse o site oficial.\n\n"
        "## Informações importantes\n\n[https://layerzero.network](https://layerzero.network). "
        "Nao constitui recomendacao."
    )
    good = _article(
        "Intro.\n\n## Sobre\n\nTexto.\n\n"
        "## Como participar\n\nAcesse [aqui](https://ref.example/abc).\n\n"
        "## Informações importantes\n\n[https://layerzero.network](https://layerzero.network). "
        "Nao constitui recomendacao."
    )

    call_count = {"n": 0}

    async def fake_with_claude(prompt: str):
        call_count["n"] += 1
        return bad if call_count["n"] == 1 else good

    research = ResearchResult(sources_text="x", sources_used=["https://layerzero.network"])

    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_with_claude", side_effect=fake_with_claude):
            with patch.object(generator, "_generate_image", AsyncMock(return_value=None)):
                result = await generator.generate(
                    project_name="LayerZero",
                    official_url="https://layerzero.network",
                    referral_url="https://ref.example/abc",
                )

    assert result is not None
    assert "https://ref.example/abc" in result["content_markdown"]
    assert call_count["n"] == 2, "Should regenerate exactly once when referral missing"


@pytest.mark.asyncio
async def test_returns_none_when_validation_fails_twice():
    generator = AirdropPostGenerator()
    generator.claude_available = True
    generator.claude_client = MagicMock()

    bad = _article(
        "Intro.\n\n## Como participar\n\nVeja o site.\n\n## Informações importantes\n\nx"
    )

    research = ResearchResult(sources_text="x", sources_used=["https://x.com"])

    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_with_claude", AsyncMock(return_value=bad)):
            with patch.object(generator, "_generate_with_gemini", AsyncMock(return_value=bad)):
                with patch.object(generator, "_generate_image", AsyncMock(return_value=None)):
                    result = await generator.generate(
                        project_name="X",
                        official_url="https://x.com",
                        referral_url="https://x.com/r",
                    )
    assert result is None


@pytest.mark.asyncio
async def test_accepts_article_with_referral_official_and_disclosure_string():
    generator = AirdropPostGenerator()
    generator.claude_available = True
    generator.claude_client = MagicMock()

    good = _article(
        "Intro.\n\n## Sobre\n\nTexto.\n\n## O programa de airdrop\n\nTexto.\n\n"
        "## Como participar\n\nAcesse [aqui](https://ref.example/abc).\n\n"
        "## Informações importantes\n\nSite oficial: [https://x.com](https://x.com). "
        "Este conteudo não constitui recomendação de investimento."
    )

    research = ResearchResult(sources_text="x", sources_used=["https://x.com"])
    with patch.object(generator.web_researcher, "gather_context", AsyncMock(return_value=research)):
        with patch.object(generator, "_generate_with_claude", AsyncMock(return_value=good)):
            with patch.object(generator, "_generate_image", AsyncMock(return_value=None)):
                result = await generator.generate(
                    project_name="X",
                    official_url="https://x.com",
                    referral_url="https://ref.example/abc",
                )
    assert result is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_airdrop_post_generator_validation.py -v`
Expected: `test_regenerates_when_referral_url_missing` FAILS (no regeneration happens — call_count stays at 1). The other two might pass or fail depending on placement.

- [ ] **Step 3: Add post-validation to `generate()`**

In `app/services/airdrop/airdrop_post_generator.py`, refactor `generate()`. Replace the current body with:

```python
    async def generate(
        self,
        project_name: str,
        official_url: str,
        referral_url: str,
    ) -> Optional[Dict]:
        """
        Roda o fluxo completo: pesquisa → IA → validação extra → article dict.
        """
        research = await self.web_researcher.gather_context(project_name, official_url)

        article = await self._generate_validated(
            project_name=project_name,
            official_url=official_url,
            referral_url=referral_url,
            research=research,
        )
        if article is None:
            return None

        if not article.get("slug"):
            article["slug"] = slugify(article.get("title", project_name))

        article["image_url"] = await self._generate_image(article)
        article["sources_used"] = research.sources_used
        article["word_count"] = len(article.get("content_markdown", "").split())
        return article

    async def _generate_validated(
        self,
        project_name: str,
        official_url: str,
        referral_url: str,
        research: ResearchResult,
        correction_hint: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Gera com Claude (fallback Gemini), valida link de referência/oficial.
        Se falhar a validação, regenera UMA vez com hint de correção.
        Retorna None se ainda falhar.
        """
        user_prompt = build_airdrop_user_prompt(
            project_name=project_name,
            official_url=official_url,
            referral_url=referral_url,
            sources_text=research.sources_text,
            current_date=datetime.utcnow().strftime("%Y-%m-%d"),
        )
        if correction_hint:
            user_prompt += f"\n\nINSTRUÇÃO DE CORREÇÃO:\n{correction_hint}"

        article = await self._generate_with_claude(user_prompt)
        if article is None:
            logger.warning("AirdropPostGenerator: Claude falhou, tentando Gemini")
            article = await self._generate_with_gemini(user_prompt)
        if article is None:
            return None

        errors = self._post_validate(article, referral_url, official_url)
        if not errors:
            return article

        # Regenera UMA vez
        if correction_hint is not None:
            logger.error(f"AirdropPostGenerator: validação falhou após retry: {errors}")
            return None

        hint = (
            "A geração anterior tinha estes problemas: "
            + "; ".join(errors)
            + ". Corrija no novo JSON."
        )
        logger.warning(f"AirdropPostGenerator: regenerando uma vez ({errors})")
        return await self._generate_validated(
            project_name=project_name,
            official_url=official_url,
            referral_url=referral_url,
            research=research,
            correction_hint=hint,
        )

    def _post_validate(
        self,
        article: Dict,
        referral_url: str,
        official_url: str,
    ) -> list[str]:
        """
        Verifica:
        - referral_url está presente no markdown
        - official_url está presente no markdown
        - string-chave do disclosure presente
        Retorna lista de erros (vazia se ok).
        """
        errors: list[str] = []
        content = article.get("content_markdown", "")
        if referral_url not in content:
            errors.append(f"link de referência ({referral_url}) ausente no conteúdo")
        if official_url not in content:
            errors.append(f"link oficial ({official_url}) ausente no bloco de disclosure")
        normalized = content.lower().replace("ã", "a").replace("ç", "c")
        if "nao constitui recomendacao" not in normalized:
            errors.append("frase 'não constitui recomendação' ausente no disclosure")
        return errors
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_airdrop_post_generator_validation.py -v`
Expected: All 3 PASS.

- [ ] **Step 5: Run all generator tests**

Run: `pytest tests/unit/test_airdrop_post_generator_*.py -v`
Expected: All PASS (claude + fallback + validation tests).

- [ ] **Step 6: Commit**

```bash
git add app/services/airdrop/airdrop_post_generator.py tests/unit/test_airdrop_post_generator_validation.py
git commit -m "feat: add post-generation validation with regenerate-once to AirdropPostGenerator"
```

---

### Task 12: Create the `/airdrops/generate-post` endpoint (preview path)

**Files:**
- Create: `app/api/v1/endpoints/airdrops.py`
- Modify: `app/api/v1/api.py`
- Create: `tests/integration/test_api_airdrops_preview.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_api_airdrops_preview.py`:

```python
"""
Testes de integração do endpoint /api/v1/airdrops/generate-post — modo preview.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings


@pytest.mark.asyncio
async def test_endpoint_requires_auth(api_client):
    response = await api_client.post(
        "/api/v1/airdrops/generate-post",
        json={
            "project_name": "LayerZero",
            "official_url": "https://layerzero.network",
            "referral_url": "https://ref.example/abc",
            "publish": False,
        },
    )
    # 401 sem header, 403 também é aceitável dependendo de como o HTTPBearer reage
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_preview_returns_markdown_without_publishing(api_client):
    article = {
        "title": "LayerZero airdrop: o que e o protocolo e como participar em 2026",
        "slug": "layerzero-protocolo-airdrop-2026",
        "excerpt": "Conheca o LayerZero, protocolo de interoperabilidade entre blockchains agora.",
        "content_markdown": (
            "Intro.\n\n"
            + "## Sobre\n\nTexto sobre crypto e blockchain. " * 30
            + "\n\n## O programa de airdrop\n\nTexto. " * 30
            + "\n\n## Como participar\n\nAcesse [aqui](https://ref.example/abc). " * 5
            + "\n\n## Informações importantes\n\n"
            "[https://layerzero.network](https://layerzero.network). "
            "Este conteudo não constitui recomendação de investimento."
        ),
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "LayerZero, protocolo de interoperabilidade. Veja como participar do "
            "programa de airdrop pelo site oficial e cadastre-se."
        ),
        "image_url": "https://img/x.jpg",
        "sources_used": ["https://layerzero.network", "https://coindesk.com/x"],
        "word_count": 600,
    }

    with patch(
        "app.api.v1.endpoints.airdrops.AirdropPostGenerator"
    ) as MockGen:
        instance = MockGen.return_value
        instance.generate = AsyncMock(return_value=article)

        response = await api_client.post(
            "/api/v1/airdrops/generate-post",
            json={
                "project_name": "LayerZero",
                "official_url": "https://layerzero.network",
                "referral_url": "https://ref.example/abc",
                "publish": False,
            },
            headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True
    assert data["post_id"] is None
    assert "preview_content" in data and data["preview_content"]
    assert data["sources_used"] == [
        "https://layerzero.network",
        "https://coindesk.com/x",
    ]


@pytest.mark.asyncio
async def test_research_failure_returns_502(api_client):
    from app.services.airdrop.web_researcher import ResearchFailedError

    with patch(
        "app.api.v1.endpoints.airdrops.AirdropPostGenerator"
    ) as MockGen:
        instance = MockGen.return_value
        instance.generate = AsyncMock(side_effect=ResearchFailedError("no sources"))

        response = await api_client.post(
            "/api/v1/airdrops/generate-post",
            json={
                "project_name": "Bogus",
                "official_url": "https://bogus.example",
                "referral_url": "https://ref.example/abc",
                "publish": False,
            },
            headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
        )

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_generator_returns_none_returns_422(api_client):
    with patch(
        "app.api.v1.endpoints.airdrops.AirdropPostGenerator"
    ) as MockGen:
        instance = MockGen.return_value
        instance.generate = AsyncMock(return_value=None)

        response = await api_client.post(
            "/api/v1/airdrops/generate-post",
            json={
                "project_name": "X",
                "official_url": "https://x.com",
                "referral_url": "https://x.com/ref",
                "publish": False,
            },
            headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
        )
    assert response.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_api_airdrops_preview.py -v`
Expected: All FAIL with `404 Not Found` (endpoint doesn't exist yet).

- [ ] **Step 3: Create the endpoint module (preview-only first)**

Create `app/api/v1/endpoints/airdrops.py`:

```python
"""
Airdrops API Endpoint

Endpoint manual para gerar (e opcionalmente publicar) posts sobre airdrops
de projetos cripto. Combina pesquisa web + IA com guardrails NFA.
"""
import traceback

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.rate_limiter import RATE_LIMITS, limiter
from app.core.security import verify_automation_token
from app.db.base import get_db
from app.schemas.airdrop import AirdropPostRequest, AirdropPostResponse
from app.services.airdrop.airdrop_post_generator import AirdropPostGenerator
from app.services.airdrop.web_researcher import ResearchFailedError
from app.services.automation.quality_validator import QualityValidator

router = APIRouter()


@router.post("/generate-post", response_model=AirdropPostResponse)
@limiter.limit(RATE_LIMITS["automation"])
async def generate_airdrop_post(
    request: Request,
    body: AirdropPostRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_automation_token),
):
    """
    Gera um artigo educacional sobre um projeto cripto e seu airdrop.

    Se publish=False (default): retorna preview sem persistir.
    Se publish=True: persiste como post com categoria "Airdrop".
    """
    logger.info(
        f"Airdrop post solicitado: project={body.project_name} publish={body.publish}"
    )

    generator = AirdropPostGenerator()
    try:
        article = await generator.generate(
            project_name=body.project_name,
            official_url=str(body.official_url),
            referral_url=str(body.referral_url),
        )
    except ResearchFailedError as e:
        logger.error(f"Airdrop: pesquisa web falhou: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Não foi possível coletar fontes confiáveis sobre o projeto. "
                "Verifique o link oficial e tente novamente."
            ),
        )
    except Exception as e:
        logger.exception(f"Airdrop: erro inesperado na geração: {e}")
        detail = "Erro interno ao gerar artigo de airdrop"
        if settings.DEBUG:
            detail += f": {e}"
        raise HTTPException(status_code=500, detail=detail)

    if article is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Falha ao gerar conteúdo válido (modelo retornou nulo após retry)",
        )

    # Valida qualidade (palavras + estrutura + título + excerpt)
    validator = QualityValidator(min_words=500, max_words=750)
    is_valid, errors = validator.validate_article(article)
    if not is_valid:
        logger.warning(f"Airdrop: validação reprovou ({errors})")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Artigo não passou na validação de qualidade", "errors": errors},
        )

    # publish=True será tratado em task posterior; por enquanto, sempre preview
    return AirdropPostResponse(
        success=True,
        post_id=None,
        title=article["title"],
        slug=article["slug"],
        excerpt=article.get("excerpt", ""),
        image_url=article.get("image_url"),
        word_count=article.get("word_count", 0),
        sources_used=article.get("sources_used", []),
        preview_content=article["content_markdown"],
        errors=[],
    )
```

- [ ] **Step 4: Register the router in `api.py`**

Modify `app/api/v1/api.py`. Replace:

```python
from app.api.v1.endpoints import posts, newsletter, health, automation

api_router = APIRouter()

api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(newsletter.router, prefix="/newsletter", tags=["newsletter"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
```

With:

```python
from app.api.v1.endpoints import airdrops, automation, health, newsletter, posts

api_router = APIRouter()

api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(newsletter.router, prefix="/newsletter", tags=["newsletter"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(airdrops.router, prefix="/airdrops", tags=["airdrops"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/integration/test_api_airdrops_preview.py -v`
Expected: All 4 PASS.

- [ ] **Step 6: Commit**

```bash
git add app/api/v1/endpoints/airdrops.py app/api/v1/api.py tests/integration/test_api_airdrops_preview.py
git commit -m "feat: add /airdrops/generate-post endpoint with preview mode"
```

---

### Task 13: Add publish mode + daily-limit check + revalidation

Extend the endpoint to actually persist the article when `publish=True`, enforce `DAILY_POST_LIMIT`, and fire frontend revalidation.

**Files:**
- Modify: `app/api/v1/endpoints/airdrops.py`
- Create: `tests/integration/test_api_airdrops_publish.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_api_airdrops_publish.py`:

```python
"""
Testes de integração do modo publish do endpoint de airdrop.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.core.config import settings
from app.db.models import Category, Post


@pytest_asyncio.fixture
async def airdrop_category(db_session) -> Category:
    cat = Category(id=uuid4(), name="Airdrop", slug="airdrop")
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)
    return cat


def _make_article(referral: str, official: str) -> dict:
    body = (
        "Intro.\n\n"
        + "## Sobre\n\nTexto sobre crypto e blockchain. " * 30
        + "\n\n## O programa de airdrop\n\nTexto. " * 25
        + f"\n\n## Como participar\n\nAcesse [aqui]({referral}). " * 5
        + "\n\n## Informações importantes\n\n"
        + f"[{official}]({official}). "
        + "Este conteudo não constitui recomendação de investimento."
    )
    return {
        "title": "LayerZero airdrop: o que e o protocolo e como participar em 2026",
        "slug": "layerzero-protocolo-airdrop-2026",
        "excerpt": "Conheca o LayerZero, protocolo de interoperabilidade entre blockchains agora.",
        "content_markdown": body,
        "meta_title": "LayerZero airdrop",
        "meta_description": (
            "LayerZero, protocolo de interoperabilidade. Veja como participar do "
            "programa de airdrop pelo site oficial e cadastre-se."
        ),
        "image_url": "https://img/x.jpg",
        "sources_used": ["https://layerzero.network"],
        "word_count": 600,
    }


@pytest.mark.asyncio
async def test_publish_true_persists_post_with_airdrop_category(
    api_client, db_session, airdrop_category
):
    article = _make_article("https://ref.example/abc", "https://layerzero.network")

    with patch("app.api.v1.endpoints.airdrops.AirdropPostGenerator") as MockGen:
        instance = MockGen.return_value
        instance.generate = AsyncMock(return_value=article)

        # mock revalidação pra não chamar de verdade
        with patch("app.api.v1.endpoints.airdrops._revalidate_frontend", AsyncMock()):
            response = await api_client.post(
                "/api/v1/airdrops/generate-post",
                json={
                    "project_name": "LayerZero",
                    "official_url": "https://layerzero.network",
                    "referral_url": "https://ref.example/abc",
                    "publish": True,
                },
                headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
            )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True
    assert data["post_id"] is not None
    assert data.get("preview_content") in (None, "")

    # Confirma que post foi gravado com a categoria airdrop
    from sqlalchemy import select
    result = await db_session.execute(select(Post).where(Post.slug == article["slug"]))
    post = result.scalar_one_or_none()
    assert post is not None
    assert post.category_id == airdrop_category.id


@pytest.mark.asyncio
async def test_publish_blocked_when_daily_limit_reached(
    api_client, db_session, airdrop_category
):
    # Cria 10 posts hoje (limite default = 10)
    from app.services.automation.news_pipeline import NewsPipeline

    for i in range(NewsPipeline.MAX_POSTS_PER_DAY):
        db_session.add(
            Post(
                id=uuid4(),
                title=f"Post #{i} de teste sobre crypto e bitcoin hoje",
                slug=f"post-teste-{i}",
                content_markdown="## x\n\nx\n\nx",
                content_html="<h2>x</h2>",
                excerpt="x" * 80,
                status="published",
                published_at=datetime.utcnow(),
                category_id=airdrop_category.id,
            )
        )
    await db_session.commit()

    article = _make_article("https://ref.example/abc", "https://layerzero.network")
    with patch("app.api.v1.endpoints.airdrops.AirdropPostGenerator") as MockGen:
        instance = MockGen.return_value
        instance.generate = AsyncMock(return_value=article)

        response = await api_client.post(
            "/api/v1/airdrops/generate-post",
            json={
                "project_name": "LayerZero",
                "official_url": "https://layerzero.network",
                "referral_url": "https://ref.example/abc",
                "publish": True,
            },
            headers={"Authorization": f"Bearer {settings.AUTOMATION_TOKEN}"},
        )
    assert response.status_code == 429
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_api_airdrops_publish.py -v`
Expected: `test_publish_true_persists_post_with_airdrop_category` FAILS (post not persisted — current endpoint only previews). `test_publish_blocked_when_daily_limit_reached` also fails.

- [ ] **Step 3: Extend the endpoint with publish logic**

In `app/api/v1/endpoints/airdrops.py`, add the new imports near the top:

```python
from datetime import datetime

import httpx

from app.crud.crud_post import crud_post
from app.services.automation.article_publisher import ArticlePublisher
from app.services.automation.news_pipeline import NewsPipeline
```

Add a helper at module level:

```python
async def _revalidate_frontend() -> None:
    """Dispara revalidação ISR no frontend. Não-bloqueante."""
    try:
        if not settings.FRONTEND_URL:
            logger.warning("FRONTEND_URL ausente — pulando revalidação")
            return
        url = f"{settings.FRONTEND_URL}/api/revalidate"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"secret": settings.REVALIDATE_SECRET})
            if resp.status_code == 200:
                logger.info("Revalidação frontend OK")
            else:
                logger.warning(f"Revalidação retornou {resp.status_code}")
    except Exception as e:
        logger.warning(f"Revalidação falhou (ignorada): {e}")
```

Replace the **end** of `generate_airdrop_post` (after validation succeeds — currently the `return AirdropPostResponse(...)` block) with branching on `body.publish`:

```python
    # Preview
    if not body.publish:
        return AirdropPostResponse(
            success=True,
            post_id=None,
            title=article["title"],
            slug=article["slug"],
            excerpt=article.get("excerpt", ""),
            image_url=article.get("image_url"),
            word_count=article.get("word_count", 0),
            sources_used=article.get("sources_used", []),
            preview_content=article["content_markdown"],
            errors=[],
        )

    # Publish: verificar limite diário
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_posts = await crud_post.get_recent_posts(db, since=today_start)
    if len(today_posts) >= NewsPipeline.MAX_POSTS_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Limite diário de posts atingido "
                f"({len(today_posts)}/{NewsPipeline.MAX_POSTS_PER_DAY})"
            ),
        )

    publisher = ArticlePublisher()
    published = await publisher.publish_article(
        article, db, force_category_slug="airdrop"
    )
    if not published:
        raise HTTPException(
            status_code=500, detail="Falha ao gravar artigo no banco"
        )

    # Buscar post pra obter ID
    created = await crud_post.get_post_by_slug(db, article["slug"])
    post_id = str(created.id) if created else None

    # Revalidação ISR (não bloqueante)
    await _revalidate_frontend()

    logger.info(f"Airdrop post publicado: {article['title'][:50]}")
    return AirdropPostResponse(
        success=True,
        post_id=post_id,
        title=article["title"],
        slug=article["slug"],
        excerpt=article.get("excerpt", ""),
        image_url=article.get("image_url"),
        word_count=article.get("word_count", 0),
        sources_used=article.get("sources_used", []),
        preview_content=None,
        errors=[],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_api_airdrops_publish.py -v`
Expected: Both PASS.

- [ ] **Step 5: Run all airdrops tests**

Run: `pytest tests/integration/test_api_airdrops_*.py tests/unit/test_airdrop_*.py -v`
Expected: All PASS.

- [ ] **Step 6: Run full suite to confirm no regressions**

Run: `pytest tests/ -q`
Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add app/api/v1/endpoints/airdrops.py tests/integration/test_api_airdrops_publish.py
git commit -m "feat: support publish mode in /airdrops/generate-post with daily limit and ISR revalidation"
```

---

### Task 14: Manual smoke test via running server

Before declaring done, run the server locally and hit the endpoint with `curl` once to confirm wiring (OpenAPI/swagger renders, auth works).

**Files:** (no code changes)

- [ ] **Step 1: Start the dev server**

Run: `uvicorn app.main:app --reload --port 8000` (leave running in background or separate terminal)
Expected: Server boots, no import errors.

- [ ] **Step 2: Check OpenAPI shows the new endpoint**

Run: `curl -s http://localhost:8000/api/v1/openapi.json | python -c "import json,sys; d=json.load(sys.stdin); print([p for p in d['paths'] if 'airdrop' in p])"`
Expected: `['/api/v1/airdrops/generate-post']`

- [ ] **Step 3: Confirm auth is required**

Run: `curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/v1/airdrops/generate-post -H "Content-Type: application/json" -d '{"project_name":"test","official_url":"https://example.com","referral_url":"https://example.com/r"}'`
Expected: `401` or `403`

- [ ] **Step 4: Confirm validation error on bad input (with valid token)**

Run:
```bash
curl -s -X POST http://localhost:8000/api/v1/airdrops/generate-post \
  -H "Authorization: Bearer $AUTOMATION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_name":"", "official_url":"not-a-url", "referral_url":"also-not"}'
```
Expected: HTTP 422 with Pydantic validation errors.

- [ ] **Step 5: (Optional) Real end-to-end preview with a known project**

If you have a real `AUTOMATION_TOKEN` and `ANTHROPIC_API_KEY` set, run a preview:

```bash
curl -X POST http://localhost:8000/api/v1/airdrops/generate-post \
  -H "Authorization: Bearer $AUTOMATION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_name":"LayerZero","official_url":"https://layerzero.network","referral_url":"https://example.com/ref/abc","publish":false}'
```

Expected: 200 with `preview_content` containing the generated markdown. Manually inspect that:
- Word count is 500-750
- Referral link appears in `## Como participar`
- Official link appears in `## Informações importantes`
- Tone is neutral (no "invista", "garanta", "lucro")

Note: this step costs API tokens. Skip it if cost-sensitive.

- [ ] **Step 6: Stop the dev server**

Press Ctrl+C in the terminal running uvicorn.

- [ ] **Step 7: No commit (smoke test only)**

If anything failed in steps 2-4, go back and fix it (open a follow-up task).

---

## Self-Review Notes

- **Spec coverage:** All 6 spec sections are covered. Components in spec map directly to Tasks 5-13. Validators + ArticlePublisher overrides addressed in Tasks 2-3. Tests in spec map to Tasks 2-13.
- **`force_category_slug` deviation from spec:** The spec mentions reusing `ArticlePublisher` "without modification", but on closer inspection the publisher hardcodes the classifier. Added a small, backward-compatible override (Task 3). Default behavior preserved.
- **Gemini fallback caveat:** Task 10 assumes `ContentGenerator` exposes a `gemini_client` (or `client`) attribute and uses `google-genai`'s `client.aio.models.generate_content`. If the actual attribute name differs in the installed `ContentGenerator` (look up in Task 10 Step 1), adapt the lookup accordingly. The fallback is defensive — failing fallback just logs and returns `None`.
- **DDG SDK import:** ddgs >= 7 uses `from ddgs import DDGS`; the older `duckduckgo_search` is aliased as fallback for safety.
- **Slug uniqueness:** Not explicitly addressed. The existing `crud_post.create_post` likely raises on duplicate slugs (since the model has `unique=True`). If duplicates become a real problem, follow-up: append week/date suffix like `weekly_report_generator` does.
