"""
Application configuration settings
"""
import warnings
from typing import Any, ClassVar, List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # Project
    PROJECT_NAME: str = "VivaCripto API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://vivacripto.com.br",
        "https://www.vivacripto.com.br",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/vivacripto"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: Any) -> str:
        """Ensure DATABASE_URL uses asyncpg driver"""
        if isinstance(v, str):
            # Convert postgres:// to postgresql://
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql://", 1)

            # Add +asyncpg if not present
            if "postgresql://" in v and "+asyncpg" not in v:
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Service Tokens
    AUTOMATION_TOKEN: str = ""
    REVALIDATE_SECRET: str = ""

    # Lista de valores inseguros que não devem ser usados em produção
    _INSECURE_DEFAULTS: ClassVar[List[str]] = [
        "your-secret-key-change-in-production",
        "automation-service-token-change-in-production",
        "revalidation-secret-change-in-production",
        "secret",
        "changeme",
        "password",
        "",
    ]

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Valida que tokens de segurança não usam valores inseguros"""
        # Validar SECRET_KEY
        if self.SECRET_KEY in self._INSECURE_DEFAULTS:
            if self.DEBUG:
                warnings.warn(
                    "SECRET_KEY usando valor inseguro! Configure uma chave segura para produção.",
                    UserWarning,
                    stacklevel=2
                )
                self.SECRET_KEY = self.SECRET_KEY or "dev-secret-key-not-for-production-use-only"
            else:
                raise ValueError(
                    "SECRET_KEY inválida! Configure uma chave secreta segura no arquivo .env. "
                    'Gere uma com: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
        elif len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY deve ter pelo menos 32 caracteres")

        # Validar AUTOMATION_TOKEN
        if self.AUTOMATION_TOKEN in self._INSECURE_DEFAULTS:
            if self.DEBUG:
                warnings.warn(
                    "AUTOMATION_TOKEN usando valor inseguro! Configure um token seguro para produção.",
                    UserWarning,
                    stacklevel=2
                )
                self.AUTOMATION_TOKEN = self.AUTOMATION_TOKEN or "dev-automation-token-not-for-production"
            else:
                raise ValueError(
                    "AUTOMATION_TOKEN inválido! Configure um token seguro no arquivo .env. "
                    'Gere um com: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )
        elif len(self.AUTOMATION_TOKEN) < 32:
            raise ValueError("AUTOMATION_TOKEN deve ter pelo menos 32 caracteres")

        # Validar REVALIDATE_SECRET
        if self.REVALIDATE_SECRET in self._INSECURE_DEFAULTS:
            if self.DEBUG:
                warnings.warn(
                    "REVALIDATE_SECRET usando valor inseguro! Configure um secret seguro para produção.",
                    UserWarning,
                    stacklevel=2
                )
                self.REVALIDATE_SECRET = self.REVALIDATE_SECRET or "dev-revalidate-secret-not-for-production"
            else:
                raise ValueError(
                    "REVALIDATE_SECRET inválido! Configure um secret seguro no arquivo .env. "
                    'Gere um com: python -c "import secrets; print(secrets.token_urlsafe(32))"'
                )

        return self

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Database Pool Settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # Recycle connections after 30 minutes

    # Automation
    DAILY_POST_LIMIT: int = 10
    AUTOMATION_INTERVAL_MINUTES: int = 30
    POSTS_PER_EXECUTION: int = 1

    # Deduplication
    DEDUPLICATION_THRESHOLD: float = 0.80
    DEDUPLICATION_ENGINE: str = "embedding"  # Options: levenshtein, tfidf, embedding, hybrid

    # External APIs
    CRYPTOPANIC_API_KEY: str = ""

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # Sentry
    SENTRY_DSN: str = ""


settings = Settings()
