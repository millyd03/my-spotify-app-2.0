"""Ruleset management routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database import get_db
from models import (
    RulesetCreate,
    RulesetUpdate,
    RulesetResponse,
    RulesetMatchRequest,
    RulesetMatchResponse,
    RulesetInfo
)
from rulesets.service import (
    get_all_rulesets,
    get_ruleset_by_id,
    create_ruleset,
    update_ruleset,
    delete_ruleset
)
from rulesets.matcher import match_rulesets

router = APIRouter()


@router.get("", response_model=List[RulesetResponse])
async def list_rulesets(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """List all rulesets."""
    rulesets = await get_all_rulesets(db, active_only=active_only)
    return [
        RulesetResponse(
            id=r.id,
            name=r.name,
            keywords=r.keywords,
            description=r.description,
            criteria=r.criteria,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in rulesets
    ]


@router.post("", response_model=RulesetResponse, status_code=201)
async def create_ruleset_endpoint(
    ruleset_data: RulesetCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new ruleset."""
    ruleset = await create_ruleset(db, ruleset_data)
    return RulesetResponse(
        id=ruleset.id,
        name=ruleset.name,
        keywords=ruleset.keywords,
        description=ruleset.description,
        criteria=ruleset.criteria,
        is_active=ruleset.is_active,
        created_at=ruleset.created_at,
        updated_at=ruleset.updated_at
    )


@router.get("/{ruleset_id}", response_model=RulesetResponse)
async def get_ruleset(
    ruleset_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get ruleset details."""
    ruleset = await get_ruleset_by_id(db, ruleset_id)
    if not ruleset:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    
    return RulesetResponse(
        id=ruleset.id,
        name=ruleset.name,
        keywords=ruleset.keywords,
        description=ruleset.description,
        criteria=ruleset.criteria,
        is_active=ruleset.is_active,
        created_at=ruleset.created_at,
        updated_at=ruleset.updated_at
    )


@router.put("/{ruleset_id}", response_model=RulesetResponse)
async def update_ruleset_endpoint(
    ruleset_id: int,
    ruleset_data: RulesetUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a ruleset."""
    ruleset = await update_ruleset(db, ruleset_id, ruleset_data)
    if not ruleset:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    
    return RulesetResponse(
        id=ruleset.id,
        name=ruleset.name,
        keywords=ruleset.keywords,
        description=ruleset.description,
        criteria=ruleset.criteria,
        is_active=ruleset.is_active,
        created_at=ruleset.created_at,
        updated_at=ruleset.updated_at
    )


@router.delete("/{ruleset_id}")
async def delete_ruleset_endpoint(
    ruleset_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a ruleset."""
    success = await delete_ruleset(db, ruleset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    
    return {"message": "Ruleset deleted successfully"}


@router.post("/match", response_model=RulesetMatchResponse)
async def match_rulesets_endpoint(
    match_request: RulesetMatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Test ruleset matching on guidelines text."""
    matched_rulesets = await match_rulesets(db, match_request.guidelines)
    
    # Extract keywords found
    all_keywords = []
    for ruleset in matched_rulesets:
        all_keywords.extend(ruleset.keywords)
    
    # Remove duplicates and keep only those found in guidelines (case-insensitive)
    guidelines_lower = match_request.guidelines.lower()
    keywords_found = list(set(
        kw for kw in all_keywords
        if kw.lower() in guidelines_lower
    ))
    
    return RulesetMatchResponse(
        matched_rulesets=[
            RulesetInfo(
                name=ruleset.name,
                description=ruleset.description,
                criteria=ruleset.criteria
            )
            for ruleset in matched_rulesets
        ],
        keywords_found=keywords_found
    )
