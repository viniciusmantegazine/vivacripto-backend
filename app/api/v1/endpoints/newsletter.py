"""
Newsletter API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.db.models import NewsletterSubscriber
from app.schemas.newsletter import NewsletterSubscribe, NewsletterSubscriberRead

router = APIRouter()


@router.post("/subscribe", response_model=NewsletterSubscriberRead, status_code=status.HTTP_201_CREATED)
async def subscribe_newsletter(
    subscriber_in: NewsletterSubscribe,
    db: AsyncSession = Depends(get_db),
):
    """
    Subscribe to newsletter
    """
    # Check if email already exists
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == subscriber_in.email)
    )
    existing_subscriber = result.scalar_one_or_none()
    
    if existing_subscriber:
        if existing_subscriber.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already subscribed"
            )
        else:
            # Reactivate subscription
            existing_subscriber.is_active = True
            existing_subscriber.unsubscribed_at = None
            await db.commit()
            await db.refresh(existing_subscriber)
            return existing_subscriber
    
    # Create new subscriber
    db_subscriber = NewsletterSubscriber(email=subscriber_in.email)
    db.add(db_subscriber)
    await db.commit()
    await db.refresh(db_subscriber)
    
    return db_subscriber
