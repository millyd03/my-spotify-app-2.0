"""Playlist creation routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from database import get_db
from models import PlaylistCreateRequest, PlaylistCreateResponse
from utils.session import get_active_user_id
from users.service import get_user_by_id
from spotify.api_client import SpotifyAPIClient
from gemini.playlist_generator import generate_playlist
from rulesets.matcher import match_rulesets

router = APIRouter()


@router.post("/create", response_model=PlaylistCreateResponse)
async def create_playlist(
    request: Request,
    playlist_request: PlaylistCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a playlist based on guidelines."""
    # Get active user
    user_id = get_active_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Match rulesets from guidelines
    matched_rulesets = await match_rulesets(db, playlist_request.guidelines)
    
    # Get Spotify API client for this user
    spotify_client = SpotifyAPIClient(user_id, db)
    
    # Generate playlist using Gemini
    playlist_result = await generate_playlist(
        db=db,
        user_id=user_id,
        num_songs=20,  # Default number of songs
        is_daily_drive=False,
        allow_explicit=True,  # Default to allow explicit
        ruleset=matched_rulesets[0] if matched_rulesets else None,
        guidelines=playlist_request.guidelines,
        music_only=playlist_request.music_only,
        spotify_client=spotify_client
    )
    
    return playlist_result
