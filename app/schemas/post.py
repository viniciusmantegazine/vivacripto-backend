"""
Pydantic schemas for Post model
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, validator


class TagBase(BaseModel):
    """Base tag schema"""
    name: str
    slug: str


class TagRead(TagBase):
    """Tag read schema"""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    """Base category schema"""
    name: str
    slug: str


class CategoryRead(CategoryBase):
    """Category read schema"""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuthorBase(BaseModel):
    """Base author schema"""
    name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class AuthorRead(AuthorBase):
    """Author read schema"""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


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
    tag_ids: Optional[List[UUID]] = []
    status: str = "draft"
    published_at: Optional[datetime] = None
    
    @validator("status")
    def validate_status(cls, v):
        if v not in ["draft", "published", "archived"]:
            raise ValueError("Status must be draft, published, or archived")
        return v


class PostUpdate(BaseModel):
    """Post update schema"""
    title: Optional[str] = Field(None, max_length=255)
    content_markdown: Optional[str] = None
    content_html: Optional[str] = None
    excerpt: Optional[str] = Field(None, max_length=300)
    featured_image_url: Optional[str] = None
    status: Optional[str] = None
    category_id: Optional[UUID] = None
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=160)
    
    @validator("status")
    def validate_status(cls, v):
        if v and v not in ["draft", "published", "archived"]:
            raise ValueError("Status must be draft, published, or archived")
        return v


class PostRead(PostBase):
    """Post read schema"""
    id: UUID
    status: str
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    author: Optional[AuthorRead] = None
    category: Optional[CategoryRead] = None
    tags: List[TagRead] = []
    
    class Config:
        from_attributes = True


class PostList(BaseModel):
    """Post list response schema"""
    items: List[PostRead]
    total: int
    page: int
    page_size: int
    total_pages: int
