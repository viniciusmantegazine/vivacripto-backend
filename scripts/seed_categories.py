"""
Seed categories in the database
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import SessionLocal
from app.db.models import Category
from app.core.logging import logger


def seed_categories():
    """Create default categories if they don't exist"""
    db = SessionLocal()
    
    categories = [
        {'name': 'Bitcoin', 'slug': 'bitcoin'},
        {'name': 'Ethereum', 'slug': 'ethereum'},
        {'name': 'Altcoins', 'slug': 'altcoins'},
        {'name': 'DeFi', 'slug': 'defi'},
        {'name': 'Regulação', 'slug': 'regulacao'},
        {'name': 'Airdrop', 'slug': 'airdrop'},
    ]
    
    try:
        for cat_data in categories:
            # Check if category already exists
            existing = db.query(Category).filter(Category.slug == cat_data['slug']).first()
            
            if not existing:
                category = Category(**cat_data)
                db.add(category)
                logger.info(f"✓ Created category: {cat_data['name']}")
            else:
                logger.info(f"→ Category already exists: {cat_data['name']}")
        
        db.commit()
        logger.info("✓ Categories seeded successfully!")
        
    except Exception as e:
        logger.error(f"Error seeding categories: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_categories()
