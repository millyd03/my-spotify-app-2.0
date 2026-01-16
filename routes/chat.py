"""Chat routes for conversational playlist and ruleset management."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List
from datetime import datetime

from database import get_db
from models import ChatRequest, ChatResponse, ChatMessage, ChatHistoryResponse
from utils.session import get_active_user_id
from users.service import get_user_by_id
from spotify.api_client import SpotifyAPIClient
from gemini.playlist_generator import generate_playlist
from gemini.chat_handler import get_chat_handler

router = APIRouter()

# In-memory conversation storage (per user session)
# In production, consider storing in database or Redis
_conversations: Dict[int, List[ChatMessage]] = {}


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send a chat message and get AI response."""
    # Get active user
    user_id = get_active_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get or create conversation history
    if user_id not in _conversations:
        _conversations[user_id] = []
    
    conversation_history = _conversations[user_id]
    
    # Add user message to history
    user_message = ChatMessage(
        role="user",
        content=chat_request.message,
        timestamp=datetime.utcnow()
    )
    conversation_history.append(user_message)
    
    # Get chat handler
    chat_handler = get_chat_handler()
    
    # Get Spotify client for playlist generation
    spotify_client = SpotifyAPIClient(user_id, db)
    
    # Process message
    response_text, action_type, action_data = await chat_handler.process_message(
        user_message=chat_request.message,
        conversation_history=conversation_history[:-1],  # Exclude the just-added user message
        db=db,
        user_id=user_id,
        spotify_client=spotify_client,
        playlist_generator=generate_playlist
    )
    
    # Add assistant response to history
    assistant_message = ChatMessage(
        role="assistant",
        content=response_text,
        timestamp=datetime.utcnow()
    )
    conversation_history.append(assistant_message)
    
    # Keep only last 50 messages to prevent memory issues
    if len(conversation_history) > 50:
        _conversations[user_id] = conversation_history[-50:]
    
    return ChatResponse(
        message=response_text,
        action_type=action_type,
        action_data=action_data
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(request: Request):
    """Get conversation history for current session."""
    user_id = get_active_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get conversation history
    conversation_history = _conversations.get(user_id, [])
    
    return ChatHistoryResponse(messages=conversation_history)


@router.post("/clear")
async def clear_chat_history(request: Request):
    """Clear conversation history for current session."""
    user_id = get_active_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Clear conversation history
    if user_id in _conversations:
        _conversations[user_id] = []
    
    return {"message": "Conversation history cleared"}
