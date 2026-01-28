"""Pydantic models for request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# User Models
class UserResponse(BaseModel):
    """User response model."""
    id: int
    spotify_user_id: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SwitchUserRequest(BaseModel):
    """Request to switch active user."""
    user_id: int


# Playlist Models
class PlaylistCreateRequest(BaseModel):
    """Request to create a playlist."""
    guidelines: str = Field(..., min_length=1, description="Natural language guidelines for playlist generation")
    music_only: bool = Field(default=False, description="If true, only include music (no podcasts)")
    timezone: Optional[str] = Field(default=None, description="Timezone for daily drive day determination (e.g., 'America/New_York'). If not provided, uses server timezone.")


class RulesetInfo(BaseModel):
    """Ruleset information."""
    name: str
    description: Optional[str] = None
    criteria: Dict[str, Any]


class PlaylistCreateResponse(BaseModel):
    """Response after creating a playlist."""
    playlist_id: str
    name: str
    spotify_url: str
    rulesets_applied: List[str] = []
    tracks_count: int


# Ruleset Models
class RulesetCreate(BaseModel):
    """Request to create a ruleset."""
    name: str = Field(..., min_length=1)
    keywords: List[str] = Field(..., min_items=1)
    description: Optional[str] = None
    criteria: Dict[str, Any] = Field(default_factory=dict)
    source_playlist_names: Optional[List[str]] = None
    source_mode: Optional[str] = None
    is_active: bool = True


class RulesetUpdate(BaseModel):
    """Request to update a ruleset."""
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    description: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    source_playlist_names: Optional[List[str]] = None
    source_mode: Optional[str] = None
    is_active: Optional[bool] = None


class RulesetResponse(BaseModel):
    """Ruleset response model."""
    id: int
    name: str
    keywords: List[str]
    description: Optional[str] = None
    criteria: Dict[str, Any]
    source_playlist_names: Optional[List[str]] = None
    source_mode: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RulesetMatchRequest(BaseModel):
    """Request to test ruleset matching."""
    guidelines: str


class RulesetMatchResponse(BaseModel):
    """Response with matched rulesets."""
    matched_rulesets: List[RulesetInfo]
    keywords_found: List[str]


# User Data Models
class ArtistInfo(BaseModel):
    """Artist information."""
    id: str
    name: str
    genres: List[str] = []
    popularity: Optional[int] = None


class PodcastInfo(BaseModel):
    """Podcast/show information."""
    id: str
    name: str
    publisher: Optional[str] = None
    description: Optional[str] = None


class PlaylistInfo(BaseModel):
    """Playlist information."""
    id: str
    name: str
    description: Optional[str] = None
    owner: str
    public: Optional[bool] = None
    tracks_total: int


class UserPlaylistsResponse(BaseModel):
    """Response with user's playlists."""
    playlists: List[PlaylistInfo]


class UserArtistsResponse(BaseModel):
    """Response with user's top artists."""
    artists: List[ArtistInfo]


class UserPodcastsResponse(BaseModel):
    """Response with user's saved podcasts."""
    podcasts: List[PodcastInfo]


# Chat Models
class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(..., min_length=1, description="User's chat message")


class ChatResponse(BaseModel):
    """Response from chat."""
    message: str = Field(..., description="Assistant's response message")
    action_type: Optional[str] = Field(None, description="Type of action taken: 'playlist_created', 'ruleset_created', 'ruleset_updated', 'ruleset_deleted', 'ruleset_listed', or None")
    action_data: Optional[Dict[str, Any]] = Field(None, description="Data related to the action (playlist info, ruleset info, etc.)")


class ChatHistoryResponse(BaseModel):
    """Response with chat history."""
    messages: List[ChatMessage]