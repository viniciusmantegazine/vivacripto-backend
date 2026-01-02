"""
Base class for SQLAlchemy models
Separated from engine creation to avoid issues with Alembic
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
