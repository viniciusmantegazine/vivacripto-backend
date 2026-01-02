"""
Application configuration settings
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Project
    PROJECT_NAME: str = "VivaCripto API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://vivacripto.com.br",
        "https://www.vivacripto.com.br",
    ]
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/vivacripto"
    
    @validator("DATABASE_URL", pre=True)
    def assemble_database_url(cls, v):
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
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Service Tokens
    AUTOMATION_TOKEN: str = "automation-service-token-change-in-production"
    REVALIDATE_SECRET: str = "revalidation-secret-change-in-production"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Automation
    DAILY_POST_LIMIT: int = 10
    AUTOMATION_INTERVAL_MINUTES: int = 30
    
    # External APIs
    CRYPTOPANIC_API_KEY: str = ""
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Sentry
    SENTRY_DSN: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
