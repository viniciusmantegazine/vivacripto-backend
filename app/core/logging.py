"""
Structured Logging Configuration
Configura loguru com contexto estruturado para melhor observabilidade.
"""
import json
import sys
import traceback as traceback_mod
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Dict, Optional

from loguru import logger

from app.core.config import settings

# Context variables for request tracking
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return request_id_ctx.get()


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_ctx.get()


def set_request_context(request_id: Optional[str] = None, correlation_id: Optional[str] = None):
    """Set request context for logging."""
    if request_id:
        request_id_ctx.set(request_id)
    if correlation_id:
        correlation_id_ctx.set(correlation_id)


def clear_request_context():
    """Clear request context."""
    request_id_ctx.set(None)
    correlation_id_ctx.set(None)


def context_filter(record: Dict[str, Any]) -> bool:
    """Add context variables to log records."""
    record["extra"].setdefault("request_id", get_request_id() or "-")
    record["extra"].setdefault("correlation_id", get_correlation_id() or "-")
    return True


def _json_sink(message) -> None:
    """
    Escreve o record como UMA linha de JSON válido em stderr.

    Substitui a format-string que montava o JSON por interpolação. Aquela
    versão colocava `{message}` cru dentro de aspas, então qualquer mensagem
    com `"`, `\\` ou quebra de linha produzia linha que o agregador não
    parseava — e título de notícia vai para o log. `logger.exception` era pior:
    emitia o traceback em linhas soltas FORA do objeto JSON.

    Os nomes de campo são o contrato com o agregador e não podem mudar.
    Cuidado com dois detalhes:

    - `timestamp` usa `isoformat(timespec="milliseconds")` porque ele reproduz
      byte a byte o formato antigo `{time:YYYY-MM-DDTHH:mm:ss.SSSZ}`, que emite
      o offset COM dois-pontos (-03:00). `strftime("%z")` daria -0300.
    - `line` é número, não string. O formato antigo emitia `"line":{line}`.
    """
    record = message.record
    try:
        payload = {
            "timestamp": record["time"].isoformat(timespec="milliseconds"),
            "level": record["level"].name,
            "request_id": record["extra"].get("request_id", "-"),
            "correlation_id": record["extra"].get("correlation_id", "-"),
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        }

        exception = record["exception"]
        if exception is not None:
            payload["exception"] = "".join(
                traceback_mod.format_exception(
                    exception.type, exception.value, exception.traceback
                )
            ).rstrip()

        linha = json.dumps(payload, ensure_ascii=False, default=str)

    except Exception as e:
        # Deixar a exceção escapar faz o loguru escrever um bloco
        # `--- Logging error in Loguru Handler ---` multi-linha em stderr, que é
        # justamente a saída não parseável que este sink existe para eliminar.
        # Perder a estrutura de uma linha é aceitável; perder a linha não é.
        linha = json.dumps(
            {
                "timestamp": "-",
                "level": "ERROR",
                "request_id": "-",
                "correlation_id": "-",
                "logger": "app.core.logging",
                "function": "_json_sink",
                "line": 0,
                "message": "falha ao serializar registro de log",
                "sink_error": repr(e),
            }
        )

    sys.stderr.write(linha + "\n")


def setup_logging():
    """
    Configure structured logging with loguru.

    Sets up:
    - JSON format for production
    - Pretty format for development
    - Request/correlation ID context
    - Performance timing context
    """
    # Remove default handler
    logger.remove()

    # Define format based on environment
    if settings.DEBUG:
        # Development: pretty, readable format
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[request_id]}</cyan> | "
            "<magenta>{name}</magenta>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stderr,
            format=log_format,
            level="DEBUG",
            filter=context_filter,
            colorize=True,
        )
    else:
        # Production: JSON format for log aggregation
        log_format = (
            '{{"timestamp":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
            '"level":"{level}",'
            '"request_id":"{extra[request_id]}",'
            '"correlation_id":"{extra[correlation_id]}",'
            '"logger":"{name}",'
            '"function":"{function}",'
            '"line":{line},'
            '"message":"{message}"}}'
        )
        logger.add(
            sys.stderr,
            format=log_format,
            level="INFO",
            filter=context_filter,
            serialize=False,
        )

    # Add file handler for errors
    logger.add(
        "logs/error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="7 days",
        compression="gz",
    )

    return logger


class LogContext:
    """
    Context manager for adding structured context to logs.

    Usage:
        with LogContext(operation="fetch_news", source="cryptopanic"):
            logger.info("Fetching news")
            # ... operations ...
    """

    def __init__(self, **kwargs: Any):
        self.context = kwargs
        self._token = None

    def __enter__(self):
        self._token = logger.contextualize(**self.context)
        self._token.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            self._token.__exit__(exc_type, exc_val, exc_tb)


def log_operation(
    operation: str,
    include_args: bool = False,
    include_result: bool = False,
) -> Callable:
    """
    Decorator to log function entry/exit with context.

    Args:
        operation: Name of the operation for logging
        include_args: Whether to log function arguments
        include_result: Whether to log function result

    Usage:
        @log_operation("create_post", include_args=True)
        async def create_post(post_data: PostCreate):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            log_data = {"operation": operation}

            if include_args:
                safe_kwargs = {
                    k: v for k, v in kwargs.items()
                    if k not in ("password", "token", "secret", "api_key")
                }
                log_data["args"] = safe_kwargs

            with logger.contextualize(**log_data):
                logger.debug(f"Starting {operation}")
                try:
                    result = await func(*args, **kwargs)
                    if include_result:
                        logger.debug(f"Completed {operation}", result=str(result)[:100])
                    else:
                        logger.debug(f"Completed {operation}")
                    return result
                except Exception as e:
                    logger.exception(f"Failed {operation}: {e}")
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            log_data = {"operation": operation}

            if include_args:
                safe_kwargs = {
                    k: v for k, v in kwargs.items()
                    if k not in ("password", "token", "secret", "api_key")
                }
                log_data["args"] = safe_kwargs

            with logger.contextualize(**log_data):
                logger.debug(f"Starting {operation}")
                try:
                    result = func(*args, **kwargs)
                    if include_result:
                        logger.debug(f"Completed {operation}", result=str(result)[:100])
                    else:
                        logger.debug(f"Completed {operation}")
                    return result
                except Exception as e:
                    logger.exception(f"Failed {operation}: {e}")
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
