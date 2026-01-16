"""Database seeding functions."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import Ruleset
from datetime import datetime


async def seed_initial_rulesets(db: AsyncSession):
    """Seed the database with initial rulesets."""
    # Check if rulesets already exist
    result = await db.execute(select(Ruleset))
    existing_rulesets = result.scalars().all()
    
    if existing_rulesets:
        # Rulesets already seeded
        return
    
    initial_rulesets = [
        {
            "name": "throwback",
            "keywords": ["throwback", "retro", "oldies", "classic", "nostalgic"],
            "description": "Songs from before 2010 - perfect for nostalgic vibes",
            "criteria": {
                "max_year": 2010
            },
            "is_active": True
        },
        {
            "name": "fresh",
            "keywords": ["fresh", "new", "recent", "latest", "current"],
            "description": "Recent songs from the last 5 years",
            "criteria": {
                "years_back": 5
            },
            "is_active": True
        },
        {
            "name": "covers",
            "keywords": ["covers", "cover songs", "tacno"],
            "description": "Songs from the Covers playlist",
            "criteria": {},
            "source_playlist_names": ["Covers"],
            "source_mode": "replace",
            "is_active": True
        }
    ]
    
    for ruleset_data in initial_rulesets:
        ruleset = Ruleset(**ruleset_data)
        db.add(ruleset)
    
    await db.commit()
    print("Seeded initial rulesets: throwback, fresh")
