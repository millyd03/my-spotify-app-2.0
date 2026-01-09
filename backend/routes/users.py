"""User management routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database import get_db
from users.service import get_all_users, get_user_by_id, delete_user
from models import UserResponse, SwitchUserRequest
from utils.session import set_active_user_id, get_active_user_id
from fastapi import Request

router = APIRouter()


@router.get("", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db)
):
    """List all registered users."""
    users = await get_all_users(db)
    return [
        UserResponse(
            id=user.id,
            spotify_user_id=user.spotify_user_id,
            display_name=user.display_name,
            email=user.email,
            created_at=user.created_at
        )
        for user in users
    ]


@router.post("/switch")
async def switch_user(
    request: Request,
    switch_request: SwitchUserRequest,
    db: AsyncSession = Depends(get_db)
):
    """Switch active user."""
    # Verify user exists
    user = await get_user_by_id(db, switch_request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Set active user in session
    set_active_user_id(request, switch_request.user_id)
    
    return {
        "message": "User switched successfully",
        "user": UserResponse(
            id=user.id,
            spotify_user_id=user.spotify_user_id,
            display_name=user.display_name,
            email=user.email,
            created_at=user.created_at
        )
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get user details."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        spotify_user_id=user.spotify_user_id,
        display_name=user.display_name,
        email=user.email,
        created_at=user.created_at
    )


@router.delete("/{user_id}")
async def delete_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a user."""
    success = await delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}
