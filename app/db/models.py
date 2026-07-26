"""
SQLAlchemy database models
"""
import uuid
from math import ceil
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Table, CheckConstraint
from app.db.types import GUID, PortableJSONB
from sqlalchemy.orm import relationship, backref
from app.db.base_class import Base


def utc_now() -> datetime:
    """Retorna datetime UTC naive para compatibilidade com TIMESTAMP WITHOUT TIME ZONE."""
    return datetime.utcnow()


# Association table for many-to-many relationship between posts and tags
post_tags = Table(
    'post_tags',
    Base.metadata,
    Column('post_id', GUID(), ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', GUID(), ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
)


class Author(Base):
    """Author model"""
    __tablename__ = 'authors'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    bio = Column(Text)
    avatar_url = Column(Text)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    
    # Relationships
    posts = relationship("Post", back_populates="author")


class Category(Base):
    """Category model"""
    __tablename__ = 'categories'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    # Relationships
    posts = relationship("Post", back_populates="category")


class Tag(Base):
    """Tag model"""
    __tablename__ = 'tags'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    # Relationships
    posts = relationship("Post", secondary=post_tags, back_populates="tags")


class Post(Base):
    """Post model"""
    __tablename__ = 'posts'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    content_markdown = Column(Text, nullable=False)
    content_html = Column(Text, nullable=False)
    excerpt = Column(String(300), nullable=False)
    featured_image_url = Column(Text)
    status = Column(
        String(20),
        nullable=False,
        default='draft',
        server_default='draft'
    )
    published_at = Column(DateTime)
    
    # Foreign Keys
    author_id = Column(GUID(), ForeignKey('authors.id', ondelete='SET NULL'))
    category_id = Column(GUID(), ForeignKey('categories.id', ondelete='SET NULL'))
    
    # SEO fields
    meta_title = Column(String(70))
    meta_description = Column(String(160))
    canonical_url = Column(String(255))

    # URL da notícia original nas fontes (pré-filtro anti-reprocessamento
    # do pipeline — ver crud_post.get_existing_source_urls)
    source_url = Column(Text, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    
    # Deduplication tracking
    deduplication_history = Column(PortableJSONB, nullable=True, server_default='[]')
    
    # Relationships
    author = relationship("Author", back_populates="posts")
    category = relationship("Category", back_populates="posts")
    tags = relationship("Tag", secondary=post_tags, back_populates="posts")

    @property
    def reading_time(self) -> int:
        """Tempo de leitura estimado em minutos (~200 palavras/min).

        Calculado a partir do conteúdo (que o ORM já carrega), mas exposto
        também no PostListItem — que NÃO serializa o conteúdo — para o frontend
        exibir o tempo de leitura sem baixar o texto inteiro na listagem.
        """
        content = self.content_markdown or ""
        words = len(content.split())
        return max(1, ceil(words / 200)) if words else 0

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'archived')", name='check_status'),
    )


class NewsletterSubscriber(Base):
    """Newsletter subscriber model"""
    __tablename__ = 'newsletter_subscribers'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    subscribed_at = Column(DateTime, default=utc_now, nullable=False)
    unsubscribed_at = Column(DateTime)


class AutomationLog(Base):
    """Automation log model"""
    __tablename__ = 'automation_logs'

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    run_id = Column(GUID(), nullable=False)
    level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    log_metadata = Column(PortableJSONB)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class SocialPost(Base):
    """Social media post tracking model"""
    __tablename__ = 'social_posts'

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    post_id = Column(GUID(), ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    platform = Column(String(50), nullable=False)  # "twitter", "instagram"
    platform_post_id = Column(String(255), nullable=True)  # ID do post na plataforma
    platform_url = Column(Text, nullable=True)  # URL do post na plataforma
    status = Column(String(20), nullable=False, default='pending')  # "pending", "success", "failed"
    error_message = Column(Text, nullable=True)
    published_at = Column(DateTime, default=utc_now, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    # passive_deletes=True: confia no ON DELETE CASCADE da FK (migration 004) ao
    # deletar o Post. Sem isso, o ORM tenta anular social_posts.post_id (NOT NULL)
    # antes do cascade do banco, causando IntegrityError (500) ao deletar um post
    # que teve tentativa de publicação social.
    post = relationship(
        "Post",
        backref=backref("social_posts", passive_deletes=True),
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("platform IN ('twitter', 'instagram', 'linkedin')", name='check_social_platform'),
        CheckConstraint("status IN ('pending', 'success', 'failed')", name='check_social_status'),
    )
