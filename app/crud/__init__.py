"""
CRUD operations
"""
from app.crud.crud_post import crud_post, CRUDPost
from app.crud.crud_social_post import crud_social_post, CRUDSocialPost

__all__ = [
    "crud_post",
    "CRUDPost",
    "crud_social_post",
    "CRUDSocialPost",
]
