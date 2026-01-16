"""Ruleset management routes."""
from fastapi import APIRouter, Request, Depends, HTTPException
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
from utils.session import get_active_user_id
from spotify.api_client import SpotifyAPIClient

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
            source_playlist_names=r.source_playlist_names,
            source_mode=r.source_mode,
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
        source_playlist_names=ruleset.source_playlist_names,
        source_mode=ruleset.source_mode,
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
        source_playlist_names=ruleset.source_playlist_names,
        source_mode=ruleset.source_mode,
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
        source_playlist_names=ruleset.source_playlist_names,
        source_mode=ruleset.source_mode,
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


@router.post("/{ruleset_id}/validate-playlists")
async def validate_source_playlists(
    request: Request,
    ruleset_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Validate that source playlists exist and are accessible."""
    # Get active user
    user_id = get_active_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get ruleset
    ruleset = await get_ruleset_by_id(db, ruleset_id)
    if not ruleset:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    
    if not ruleset.source_playlist_names:
        return {"valid": True, "playlists": []}
    
    # Get Spotify client
    spotify_client = SpotifyAPIClient(user_id, db)
    
    # Get user's playlists
    user_playlists = await spotify_client.get_user_playlists()
    playlist_name_to_info = {p['name']: p for p in user_playlists}
    
    valid_playlists = []
    invalid_names = []
    
    for name in ruleset.source_playlist_names:
        if name in playlist_name_to_info:
            info = playlist_name_to_info[name]
            valid_playlists.append({
                "name": name,
                "id": info["id"],
                "tracks_total": info["tracks_total"],
                "owner": info["owner"]
            })
        else:
            invalid_names.append(name)
    
    return {
        "valid": len(invalid_names) == 0,
        "valid_playlists": valid_playlists,
        "invalid_playlist_names": invalid_names
    }
