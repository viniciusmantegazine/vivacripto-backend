"""
Rate Limiting configuration using SlowAPI
Protege a API contra abusos e ataques de força bruta
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """
    Extrai o IP real do cliente, considerando proxies reversos.
    Verifica headers comuns de proxies antes de usar o IP direto.
    """
    # Verifica headers de proxy (em ordem de preferência)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For pode conter múltiplos IPs: "client, proxy1, proxy2"
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback para o IP direto da conexão
    return get_remote_address(request)


# Criar instância do limiter
# Em produção, usar Redis como storage. Em desenvolvimento, usar memória.
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["200/minute"],  # Limite global padrão
    storage_uri=settings.REDIS_URL if not settings.DEBUG else "memory://",
    strategy="fixed-window",
)


def setup_rate_limiting(app: FastAPI) -> None:
    """
    Configura rate limiting na aplicação FastAPI.
    Deve ser chamado após a criação da instância do app.
    """
    # Adicionar state do limiter à aplicação
    app.state.limiter = limiter

    # Adicionar middleware
    app.add_middleware(SlowAPIMiddleware)

    # Handler de exceção para rate limit excedido
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
        """Handler customizado para quando o rate limit é excedido"""
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": "Muitas requisições. Por favor, aguarde antes de tentar novamente.",
                "detail": str(exc.detail),
                "retry_after": getattr(exc, "retry_after", 60),
            },
            headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
        )


# Limites específicos para diferentes tipos de endpoints
RATE_LIMITS = {
    # Endpoints públicos de leitura - mais permissivos
    "public_read": "100/minute",

    # Endpoints de busca - moderado (para evitar scraping)
    "search": "30/minute",

    # Endpoints de escrita autenticados
    "authenticated_write": "20/minute",

    # Endpoint de automação - restrito (operações custosas)
    "automation": "5/minute",

    # Endpoints de newsletter - anti-spam
    "newsletter": "10/minute",

    # Health check - sem limite (monitoramento)
    "health": "1000/minute",
}
