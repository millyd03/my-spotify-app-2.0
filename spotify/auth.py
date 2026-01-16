"""Spotify authentication utilities."""
from sqlalchemy.ext.asyncio import AsyncSession
from users.service import get_user_by_id, update_user_tokens
from utils.encryption import encrypt_token, decrypt_token
from datetime import datetime, timedelta
import httpx
import base64
from config import settings
from typing import Optional


async def get_user_token(user_id: int, db: AsyncSession) -> Optional[str]:
    """Get user's access token, refreshing if necessary."""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    # Check if token is expired
    if datetime.utcnow() >= user.token_expires_at:
        # Refresh token
        await refresh_user_token(user_id, db)
        user = await get_user_by_id(db, user_id)
        if not user:
            return None
    
    return decrypt_token(user.access_token)


async def refresh_user_token(user_id: int, db: AsyncSession) -> bool:
    """Refresh user's access token."""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    refresh_token = decrypt_token(user.refresh_token)
    
    token_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    ).decode()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        
        if response.status_code != 200:
            return False
        
        token_data = response.json()
        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        
        # Encrypt tokens
        encrypted_access_token = encrypt_token(access_token)
        # Only encrypt refresh token if it's a new one (not already encrypted)
        if "refresh_token" in token_data:
            encrypted_refresh_token = encrypt_token(token_data["refresh_token"])
        else:
            # Keep existing encrypted refresh token
            encrypted_refresh_token = user.refresh_token
        
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        await update_user_tokens(
            db,
            user_id,
            encrypted_access_token,
            encrypted_refresh_token,
            token_expires_at
        )
        
        return True


async def store_user_tokens(
    user_id: int,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    db: AsyncSession
) -> bool:
    """Store user's tokens (already encrypted)."""
    encrypted_access_token = encrypt_token(access_token)
    encrypted_refresh_token = encrypt_token(refresh_token)
    token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    await update_user_tokens(
        db,
        user_id,
        encrypted_access_token,
        encrypted_refresh_token,
        token_expires_at
    )
    
    return True
