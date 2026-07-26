"""
Pydantic schemas for Post model
"""
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Status permitidos para posts
PostStatus = Literal["draft", "published", "archived"]


class TagBase(BaseModel):
    """Base tag schema"""
    name: str
    slug: str


class TagRead(TagBase):
    """Tag read schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class CategoryBase(BaseModel):
    """Base category schema"""
    name: str
    slug: str


class CategoryRead(CategoryBase):
    """Category read schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class AuthorBase(BaseModel):
    """Base author schema"""
    name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class AuthorRead(AuthorBase):
    """Author read schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class PostBase(BaseModel):
    """Base post schema"""
    title: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    content_markdown: str
    content_html: str
    excerpt: str = Field(..., max_length=300)
    featured_image_url: Optional[str] = None
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=160)
    canonical_url: Optional[str] = None


class PostCreate(PostBase):
    """Post creation schema"""
    category_id: Optional[UUID] = None
    author_id: Optional[UUID] = None
    tag_ids: List[UUID] = Field(default_factory=list)
    status: PostStatus = "draft"
    published_at: Optional[datetime] = None
    # URL da notícia original (não exposta em PostBase/PostRead de propósito)
    source_url: Optional[str] = None


class PostUpdate(BaseModel):
    """Post update schema"""
    title: Optional[str] = Field(None, max_length=255)
    content_markdown: Optional[str] = None
    content_html: Optional[str] = None
    excerpt: Optional[str] = Field(None, max_length=300)
    featured_image_url: Optional[str] = None
    status: Optional[PostStatus] = None
    category_id: Optional[UUID] = None
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=160)
    # A URL da fonte precisa poder ser atualizada: quando o dedup decide
    # UPDATE_EXISTING, é a URL da SEGUNDA fonte que passa a valer. Sem gravá-la,
    # o pré-filtro anti-reprocessamento (que busca por Post.source_url) nunca a
    # vê e deixa a mesma notícia ser regerada em todo run seguinte.
    source_url: Optional[str] = None


class PostRead(PostBase):
    """Post read schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    reading_time: int = 0
    author: Optional[AuthorRead] = None
    category: Optional[CategoryRead] = None
    tags: List[TagRead] = []


class PostListItem(BaseModel):
    """
    Item enxuto para listagem de posts.

    Omite content_markdown e content_html (que somam ~120KB por página) já que
    a listagem do frontend usa apenas o excerpt. Use PostRead para detalhe.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    excerpt: str
    featured_image_url: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    status: str
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    reading_time: int = 0
    author: Optional[AuthorRead] = None
    category: Optional[CategoryRead] = None
    tags: List[TagRead] = []


class PostList(BaseModel):
    """Post list response schema"""
    items: List[PostListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
