"""
SQLAlchemy database models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Table, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import Base


# Association table for many-to-many relationship between posts and tags
post_tags = Table(
    'post_tags',
    Base.metadata,
    Column('post_id', UUID(as_uuid=True), ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
)


class Author(Base):
    """Author model"""
    __tablename__ = 'authors'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    bio = Column(Text)
    avatar_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    posts = relationship("Post", back_populates="author")


class Category(Base):
    """Category model"""
    __tablename__ = 'categories'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    posts = relationship("Post", back_populates="category")


class Tag(Base):
    """Tag model"""
    __tablename__ = 'tags'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    posts = relationship("Post", secondary=post_tags, back_populates="tags")


class Post(Base):
    """Post model"""
    __tablename__ = 'posts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    author_id = Column(UUID(as_uuid=True), ForeignKey('authors.id', ondelete='SET NULL'))
    category_id = Column(UUID(as_uuid=True), ForeignKey('categories.id', ondelete='SET NULL'))
    
    # SEO fields
    meta_title = Column(String(70))
    meta_description = Column(String(160))
    canonical_url = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Deduplication tracking
    deduplication_history = Column(JSONB, nullable=True, server_default='[]')
    
    # Relationships
    author = relationship("Author", back_populates="posts")
    category = relationship("Category", back_populates="posts")
    tags = relationship("Tag", secondary=post_tags, back_populates="posts")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'archived')", name='check_status'),
    )


class NewsletterSubscriber(Base):
    """Newsletter subscriber model"""
    __tablename__ = 'newsletter_subscribers'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    subscribed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    unsubscribed_at = Column(DateTime)


class AutomationLog(Base):
    """Automation log model"""
    __tablename__ = 'automation_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), nullable=False)
    level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    log_metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
