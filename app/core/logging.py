"""
Logging configuration
"""
import sys
from loguru import logger
from app.core.config import settings


def setup_logging():
    """Configure application logging"""
    
    # Remove default handler
    logger.remove()
    
    # Add custom handler with JSON format for production
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )
    
    # Add file handler for errors
    logger.add(
        "logs/error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
    )
    
    return logger
