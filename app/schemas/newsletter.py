"""
Pydantic schemas for Newsletter
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


class NewsletterSubscribe(BaseModel):
    """Newsletter subscription schema"""
    email: EmailStr


class NewsletterSubscriberRead(BaseModel):
    """Newsletter subscriber read schema"""
    id: UUID
    email: str
    is_active: bool
    subscribed_at: datetime
    unsubscribed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
