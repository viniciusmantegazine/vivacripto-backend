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
    Extrai o IP do cliente para o rate limiter, resistente a spoofing.

    O X-Forwarded-For tem a forma "client, proxy1, proxy2". A PRIMEIRA entrada é
    controlada pelo cliente (spoofável: bastaria mandar um XFF falso para burlar
    o limite). A ÚLTIMA entrada é a que foi acrescentada pelo proxy de borda do
    Railway (confiável), correspondendo ao peer real. Por isso usamos a última.

    Se não houver XFF, cai no IP direto da conexão (get_remote_address).
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        parts = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
        if parts:
            return parts[-1]

    # Fallback para o IP direto da conexão (peer real)
    return get_remote_address(request)


# Criar instância do limiter
# Usar Redis como storage se configurado, caso contrário usar memória.
def _get_storage_uri() -> str:
    """Retorna a URI de storage para o rate limiter."""
    redis_url = settings.REDIS_URL
    # Usar Redis apenas se URL estiver configurada e for válida
    if redis_url and redis_url.startswith(("redis://", "rediss://")):
        return redis_url
    return "memory://"


limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["200/minute"],  # Limite global padrão
    storage_uri=_get_storage_uri(),
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
