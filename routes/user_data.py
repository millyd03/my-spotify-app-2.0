"""User data routes (artists, podcasts)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from database import get_db
from models import UserArtistsResponse, UserPodcastsResponse, UserPlaylistsResponse, ArtistInfo, PodcastInfo, PlaylistInfo
from utils.session import get_active_user_id
from users.service import get_user_by_id
from spotify.api_client import SpotifyAPIClient

router = APIRouter()


@router.get("/artists", response_model=UserArtistsResponse)
async def get_user_artists(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current user's top artists."""
    user_id = get_active_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    spotify_client = SpotifyAPIClient(user_id, db)
    artists = await spotify_client.get_top_artists(limit=50, time_range="medium_term")
    
    artist_infos = [
        ArtistInfo(
            id=artist["id"],
            name=artist["name"],
            genres=artist.get("genres", []),
            popularity=artist.get("popularity")
        )
        for artist in artists
    ]
    
    return UserArtistsResponse(artists=artist_infos)


@router.get("/podcasts", response_model=UserPodcastsResponse)
async def get_user_podcasts(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current user's saved podcasts."""
    user_id = get_active_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    spotify_client = SpotifyAPIClient(user_id, db)
    podcasts = await spotify_client.get_saved_podcasts()
    
    podcast_infos = [
        PodcastInfo(
            id=podcast["id"],
            name=podcast["name"],
            publisher=podcast.get("publisher"),
            description=podcast.get("description")
        )
        for podcast in podcasts
    ]
    
    return UserPodcastsResponse(podcasts=podcast_infos)


@router.get("/playlists", response_model=UserPlaylistsResponse)
async def get_user_playlists(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current user's playlists."""
    user_id = get_active_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    spotify_client = SpotifyAPIClient(user_id, db)
    playlists = await spotify_client.get_user_playlists()
    
    playlist_infos = [
        PlaylistInfo(
            id=playlist["id"],
            name=playlist["name"],
            description=playlist.get("description"),
            owner=playlist["owner"],
            public=playlist.get("public"),
            tracks_total=playlist["tracks_total"]
        )
        for playlist in playlists
    ]
    
    return UserPlaylistsResponse(playlists=playlist_infos)
