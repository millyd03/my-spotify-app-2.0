"""Ruleset management service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime

from database import Ruleset
from models import RulesetCreate, RulesetUpdate


async def get_all_rulesets(
    db: AsyncSession,
    active_only: bool = False
) -> List[Ruleset]:
    """Get all rulesets, optionally filtering by active status."""
    query = select(Ruleset)
    if active_only:
        query = query.where(Ruleset.is_active == True)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_ruleset_by_id(db: AsyncSession, ruleset_id: int) -> Optional[Ruleset]:
    """Get ruleset by ID."""
    result = await db.execute(select(Ruleset).where(Ruleset.id == ruleset_id))
    return result.scalar_one_or_none()


async def get_ruleset_by_name(db: AsyncSession, name: str) -> Optional[Ruleset]:
    """Get ruleset by name."""
    result = await db.execute(select(Ruleset).where(Ruleset.name == name))
    return result.scalar_one_or_none()


async def create_ruleset(
    db: AsyncSession,
    ruleset_data: RulesetCreate
) -> Ruleset:
    """Create a new ruleset."""
    # Check if name already exists
    existing = await get_ruleset_by_name(db, ruleset_data.name)
    if existing:
        raise ValueError(f"Ruleset with name '{ruleset_data.name}' already exists")
    
    ruleset = Ruleset(
        name=ruleset_data.name,
        keywords=ruleset_data.keywords,
        description=ruleset_data.description,
        criteria=ruleset_data.criteria,
        source_playlist_names=ruleset_data.source_playlist_names,
        source_mode=ruleset_data.source_mode,
        is_active=ruleset_data.is_active
    )
    db.add(ruleset)
    await db.commit()
    await db.refresh(ruleset)
    return ruleset


async def update_ruleset(
    db: AsyncSession,
    ruleset_id: int,
    ruleset_data: RulesetUpdate
) -> Optional[Ruleset]:
    """Update an existing ruleset."""
    ruleset = await get_ruleset_by_id(db, ruleset_id)
    if not ruleset:
        return None
    
    if ruleset_data.name is not None:
        # Check if new name conflicts with another ruleset
        existing = await get_ruleset_by_name(db, ruleset_data.name)
        if existing and existing.id != ruleset_id:
            raise ValueError(f"Ruleset with name '{ruleset_data.name}' already exists")
        ruleset.name = ruleset_data.name
    
    if ruleset_data.keywords is not None:
        ruleset.keywords = ruleset_data.keywords
    
    if ruleset_data.description is not None:
        ruleset.description = ruleset_data.description
    
    if ruleset_data.criteria is not None:
        ruleset.criteria = ruleset_data.criteria
    
    if ruleset_data.source_playlist_names is not None:
        ruleset.source_playlist_names = ruleset_data.source_playlist_names
    
    if ruleset_data.source_mode is not None:
        ruleset.source_mode = ruleset_data.source_mode
    
    if ruleset_data.is_active is not None:
        ruleset.is_active = ruleset_data.is_active
    
    ruleset.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ruleset)
    return ruleset


async def delete_ruleset(db: AsyncSession, ruleset_id: int) -> bool:
    """Delete a ruleset."""
    ruleset = await get_ruleset_by_id(db, ruleset_id)
    if not ruleset:
        return False
    
    await db.delete(ruleset)
    await db.commit()
    return True
