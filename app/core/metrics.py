"""
Performance Metrics Module
Coleta e reporta métricas de performance do pipeline de automação.
"""
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class TimingMetric:
    """Single timing measurement."""
    name: str
    duration_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineMetrics:
    """Aggregated metrics for a pipeline run."""
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_ms: float = 0.0

    # Collection phase
    news_collected: int = 0
    collection_duration_ms: float = 0.0
    sources_queried: int = 0

    # Processing phase
    articles_processed: int = 0
    articles_published: int = 0
    articles_updated: int = 0
    articles_skipped: int = 0
    articles_failed: int = 0
    processing_duration_ms: float = 0.0

    # AI operations
    content_generation_count: int = 0
    content_generation_duration_ms: float = 0.0
    image_generation_count: int = 0
    image_generation_duration_ms: float = 0.0

    # Deduplication
    dedup_checks: int = 0
    dedup_duration_ms: float = 0.0
    duplicates_found: int = 0

    # Quality validation
    validation_count: int = 0
    validation_passed: int = 0
    validation_failed: int = 0

    # Errors
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/reporting."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms,
            "collection": {
                "news_collected": self.news_collected,
                "duration_ms": self.collection_duration_ms,
                "sources_queried": self.sources_queried,
            },
            "processing": {
                "articles_processed": self.articles_processed,
                "articles_published": self.articles_published,
                "articles_updated": self.articles_updated,
                "articles_skipped": self.articles_skipped,
                "articles_failed": self.articles_failed,
                "duration_ms": self.processing_duration_ms,
            },
            "ai_operations": {
                "content_generation_count": self.content_generation_count,
                "content_generation_duration_ms": self.content_generation_duration_ms,
                "image_generation_count": self.image_generation_count,
                "image_generation_duration_ms": self.image_generation_duration_ms,
            },
            "deduplication": {
                "checks": self.dedup_checks,
                "duration_ms": self.dedup_duration_ms,
                "duplicates_found": self.duplicates_found,
            },
            "validation": {
                "count": self.validation_count,
                "passed": self.validation_passed,
                "failed": self.validation_failed,
            },
            "errors": self.errors,
        }


class MetricsCollector:
    """
    Collects and reports performance metrics for pipeline operations.

    Usage:
        collector = MetricsCollector("pipeline-run-123")

        with collector.measure("collection"):
            news = await aggregator.collect_news()
        collector.metrics.news_collected = len(news)

        collector.finalize()
        collector.log_summary()
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.metrics = PipelineMetrics(
            run_id=run_id,
            started_at=datetime.now(timezone.utc),
        )
        self._timings: List[TimingMetric] = []

    @contextmanager
    def measure(self, operation: str, **metadata):
        """
        Context manager to measure operation duration.

        Usage:
            with collector.measure("content_generation", article_title="..."):
                article = await generate_content(...)
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            timing = TimingMetric(
                name=operation,
                duration_ms=duration_ms,
                metadata=metadata,
            )
            self._timings.append(timing)

            # Update aggregate metrics
            self._update_aggregate(operation, duration_ms)

    def _update_aggregate(self, operation: str, duration_ms: float):
        """Update aggregate metrics based on operation."""
        if operation == "collection":
            self.metrics.collection_duration_ms += duration_ms
        elif operation == "processing":
            self.metrics.processing_duration_ms += duration_ms
        elif operation == "content_generation":
            self.metrics.content_generation_count += 1
            self.metrics.content_generation_duration_ms += duration_ms
        elif operation == "image_generation":
            self.metrics.image_generation_count += 1
            self.metrics.image_generation_duration_ms += duration_ms
        elif operation == "deduplication":
            self.metrics.dedup_checks += 1
            self.metrics.dedup_duration_ms += duration_ms

    def record_error(self, error: str):
        """Record an error during pipeline execution."""
        self.metrics.errors.append(error)

    def record_validation(self, passed: bool):
        """Record a validation result."""
        self.metrics.validation_count += 1
        if passed:
            self.metrics.validation_passed += 1
        else:
            self.metrics.validation_failed += 1

    def record_publish(self):
        """Record a successful publish."""
        self.metrics.articles_published += 1
        self.metrics.articles_processed += 1

    def record_update(self):
        """Record a successful update."""
        self.metrics.articles_updated += 1
        self.metrics.articles_processed += 1

    def record_skip(self):
        """Record a skipped article."""
        self.metrics.articles_skipped += 1

    def record_failure(self):
        """Record a failed article."""
        self.metrics.articles_failed += 1
        self.metrics.articles_processed += 1

    def finalize(self):
        """Finalize metrics collection."""
        self.metrics.completed_at = datetime.now(timezone.utc)
        self.metrics.total_duration_ms = (
            self.metrics.completed_at - self.metrics.started_at
        ).total_seconds() * 1000

    def log_summary(self):
        """Log a summary of collected metrics."""
        m = self.metrics

        logger.info("=" * 60)
        logger.info("PIPELINE METRICS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Run ID: {m.run_id}")
        logger.info(f"Total Duration: {m.total_duration_ms:.1f}ms ({m.total_duration_ms/1000:.1f}s)")
        logger.info("")
        logger.info("Collection Phase:")
        logger.info(f"  - News collected: {m.news_collected}")
        logger.info(f"  - Sources queried: {m.sources_queried}")
        logger.info(f"  - Duration: {m.collection_duration_ms:.1f}ms")
        logger.info("")
        logger.info("Processing Phase:")
        logger.info(f"  - Articles processed: {m.articles_processed}")
        logger.info(f"  - Published: {m.articles_published}")
        logger.info(f"  - Updated: {m.articles_updated}")
        logger.info(f"  - Skipped: {m.articles_skipped}")
        logger.info(f"  - Failed: {m.articles_failed}")
        logger.info(f"  - Duration: {m.processing_duration_ms:.1f}ms")
        logger.info("")
        logger.info("AI Operations:")
        logger.info(f"  - Content generations: {m.content_generation_count}")
        logger.info(f"  - Avg content gen time: {self._avg_duration('content_generation'):.1f}ms")
        logger.info(f"  - Image generations: {m.image_generation_count}")
        logger.info(f"  - Avg image gen time: {self._avg_duration('image_generation'):.1f}ms")
        logger.info("")
        logger.info("Deduplication:")
        logger.info(f"  - Checks: {m.dedup_checks}")
        logger.info(f"  - Duplicates found: {m.duplicates_found}")
        logger.info(f"  - Avg check time: {self._avg_duration('deduplication'):.1f}ms")
        logger.info("")
        logger.info("Validation:")
        logger.info(f"  - Total: {m.validation_count}")
        logger.info(f"  - Passed: {m.validation_passed}")
        logger.info(f"  - Failed: {m.validation_failed}")

        if m.errors:
            logger.info("")
            logger.warning(f"Errors ({len(m.errors)}):")
            for error in m.errors[:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")
            if len(m.errors) > 5:
                logger.warning(f"  ... and {len(m.errors) - 5} more")

        logger.info("=" * 60)

    def _avg_duration(self, operation: str) -> float:
        """Calculate average duration for an operation."""
        timings = [t for t in self._timings if t.name == operation]
        if not timings:
            return 0.0
        return sum(t.duration_ms for t in timings) / len(timings)

    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as dictionary for external reporting."""
        return self.metrics.to_dict()
