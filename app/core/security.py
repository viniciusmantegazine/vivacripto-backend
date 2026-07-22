"""
Security utilities for authentication and authorization
"""
import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

# HTTP Bearer token
security = HTTPBearer()


def secure_compare(provided_token: str, expected_token: str) -> bool:
    """
    Compara dois tokens de forma segura contra timing attacks.
    Usa comparação em tempo constante para evitar vazamento de informações.
    """
    if not provided_token or not expected_token:
        return False
    return secrets.compare_digest(provided_token.encode(), expected_token.encode())


async def verify_automation_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verifica o token de automação de forma segura.
    Usa comparação em tempo constante para prevenir timing attacks.
    """
    token = credentials.credentials
    if not secure_compare(token, settings.AUTOMATION_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid automation token",
        )
    return True


def verify_revalidate_secret(provided_secret: str) -> bool:
    """
    Verifica o secret de revalidação de forma segura.
    Usa comparação em tempo constante para prevenir timing attacks.
    """
    return secure_compare(provided_secret, settings.REVALIDATE_SECRET)
