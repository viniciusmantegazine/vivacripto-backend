"""
Posts API endpoints
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.crud import crud_post
from app.schemas.post import PostCreate, PostUpdate, PostRead, PostList
from app.core.security import verify_automation_token
from math import ceil

router = APIRouter()


@router.get("", response_model=PostList)
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    category_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    List posts with pagination and filters
    """
    skip = (page - 1) * page_size
    posts, total = await crud_post.get_posts(
        db=db,
        skip=skip,
        limit=page_size,
        status=status,
        category_id=category_id,
    )
    
    total_pages = ceil(total / page_size) if total > 0 else 0
    
    return PostList(
        items=posts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/search")
async def search_posts(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Search posts by title or content
    """
    posts = await crud_post.search_posts(db=db, query=q, limit=limit)
    return {"results": posts}


@router.get("/{post_id}", response_model=PostRead)
async def get_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific post by ID
    """
    post = await crud_post.get_post_by_id(db=db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    return post


@router.get("/slug/{slug}", response_model=PostRead)
async def get_post_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific post by slug
    """
    post = await crud_post.get_post_by_slug(db=db, slug=slug)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    return post


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_in: PostCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_automation_token),
):
    """
    Create a new post (requires automation token)
    """
    # Check if slug already exists
    existing_post = await crud_post.get_post_by_slug(db=db, slug=post_in.slug)
    if existing_post:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post with this slug already exists"
        )
    
    post = await crud_post.create_post(db=db, post_in=post_in)
    return post


@router.put("/{post_id}", response_model=PostRead)
async def update_post(
    post_id: UUID,
    post_in: PostUpdate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_automation_token),
):
    """
    Update a post (requires automation token)
    """
    post = await crud_post.update_post(db=db, post_id=post_id, post_in=post_in)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_automation_token),
):
    """
    Delete a post (requires automation token)
    """
    success = await crud_post.delete_post(db=db, post_id=post_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    return None
