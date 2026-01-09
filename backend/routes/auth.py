"""Authentication routes."""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from datetime import datetime, timedelta
from urllib.parse import urlencode
import base64

from config import settings
from database import get_db
from users.service import get_user_by_spotify_id, create_user, update_user_tokens
from utils.encryption import encrypt_token
from utils.session import set_active_user_id

router = APIRouter()


def get_spotify_auth_url(state: str = None) -> str:
    """Generate Spotify OAuth authorization URL."""
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": "user-read-private user-read-email user-top-read user-library-read playlist-modify-public playlist-modify-private user-read-playback-state",
    }
    if state:
        params["state"] = state
    
    auth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    return auth_url


@router.get("/login")
async def login(request: Request):
    """Initiate Spotify OAuth flow."""
    auth_url = get_spotify_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    request: Request,
    code: str = None,
    error: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Handle Spotify OAuth callback."""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    # Exchange code for tokens
    token_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    ).decode()
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.spotify_redirect_uri,
            },
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to exchange token: {token_response.text}"
            )
        
        token_data = token_response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expires_in = token_data.get("expires_in", 3600)
        
        # Get user info from Spotify
        user_response = await client.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if user_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get user info: {user_response.text}"
            )
        
        user_data = user_response.json()
        spotify_user_id = user_data["id"]
        display_name = user_data.get("display_name")
        email = user_data.get("email")
    
    # Encrypt tokens
    encrypted_access_token = encrypt_token(access_token)
    encrypted_refresh_token = encrypt_token(refresh_token)
    token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    # Check if user exists
    existing_user = await get_user_by_spotify_id(db, spotify_user_id)
    
    if existing_user:
        # Update tokens
        user = await update_user_tokens(
            db,
            existing_user.id,
            encrypted_access_token,
            encrypted_refresh_token,
            token_expires_at
        )
    else:
        # Create new user
        user = await create_user(
            db,
            spotify_user_id,
            display_name,
            email,
            encrypted_access_token,
            encrypted_refresh_token,
            token_expires_at
        )
    
    # Set active user in session
    set_active_user_id(request, user.id)
    
    # Redirect to frontend
    return RedirectResponse(url=f"{settings.frontend_url}/?logged_in=true")


@router.post("/logout")
async def logout(request: Request):
    """Logout current user."""
    from utils.session import clear_session
    clear_session(request)
    return {"message": "Logged out successfully"}


@router.get("/status")
async def status(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current authentication status."""
    from utils.session import get_active_user_id
    from users.service import get_user_by_id
    from models import UserResponse
    
    user_id = get_active_user_id(request)
    if not user_id:
        return {"authenticated": False, "user": None}
    
    user = await get_user_by_id(db, user_id)
    if not user:
        return {"authenticated": False, "user": None}
    
    return {
        "authenticated": True,
        "user": UserResponse(
            id=user.id,
            spotify_user_id=user.spotify_user_id,
            display_name=user.display_name,
            email=user.email,
            created_at=user.created_at
        )
    }
