"""User management service."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from database import User
from models import UserResponse
from datetime import datetime


async def get_all_users(db: AsyncSession) -> List[User]:
    """Get all registered users."""
    result = await db.execute(select(User))
    return result.scalars().all()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_spotify_id(db: AsyncSession, spotify_user_id: str) -> Optional[User]:
    """Get user by Spotify user ID."""
    result = await db.execute(select(User).where(User.spotify_user_id == spotify_user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    spotify_user_id: str,
    display_name: Optional[str],
    email: Optional[str],
    access_token: str,
    refresh_token: str,
    token_expires_at: datetime
) -> User:
    """Create a new user."""
    user = User(
        spotify_user_id=spotify_user_id,
        display_name=display_name,
        email=email,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expires_at=token_expires_at
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_tokens(
    db: AsyncSession,
    user_id: int,
    access_token: str,
    refresh_token: str,
    token_expires_at: datetime
) -> User:
    """Update user's tokens."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    
    user.access_token = access_token
    user.refresh_token = refresh_token
    user.token_expires_at = token_expires_at
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete a user."""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    return True
