"""Spotify API client wrapper."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import httpx
from spotify.auth import get_user_token


class SpotifyAPIClient:
    """Client for interacting with Spotify Web API."""
    
    BASE_URL = "https://api.spotify.com/v1"
    
    def __init__(self, user_id: int, db: AsyncSession):
        self.user_id = user_id
        self.db = db
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with access token."""
        token = await get_user_token(self.user_id, self.db)
        if not token:
            raise ValueError("Failed to get access token")
        return {"Authorization": f"Bearer {token}"}
    
    async def get_user_profile(self) -> Dict[str, Any]:
        """Get current user's profile."""
        async with httpx.AsyncClient() as client:
            headers = await self._get_headers()
            response = await client.get(
                f"{self.BASE_URL}/me",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_top_artists(
        self,
        limit: int = 50,
        time_range: str = "medium_term"
    ) -> List[Dict[str, Any]]:
        """Get user's top artists."""
        async with httpx.AsyncClient() as client:
            headers = await self._get_headers()
            response = await client.get(
                f"{self.BASE_URL}/me/top/artists",
                headers=headers,
                params={
                    "limit": limit,
                    "time_range": time_range  # short_term, medium_term, long_term
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
    
    async def get_saved_podcasts(self) -> List[Dict[str, Any]]:
        """Get user's saved podcasts/shows."""
        async with httpx.AsyncClient() as client:
            headers = await self._get_headers()
            shows = []
            offset = 0
            limit = 50
            
            while True:
                response = await client.get(
                    f"{self.BASE_URL}/me/shows",
                    headers=headers,
                    params={"limit": limit, "offset": offset}
                )
                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])
                if not items:
                    break
                
                for item in items:
                    show = item.get("show", {})
                    shows.append({
                        "id": show.get("id"),
                        "name": show.get("name"),
                        "publisher": show.get("publisher"),
                        "description": show.get("description"),
                    })
                
                if len(items) < limit:
                    break
                offset += limit
            
            return shows
    
    async def search_tracks(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search for tracks."""
        async with httpx.AsyncClient() as client:
            headers = await self._get_headers()
            response = await client.get(
                f"{self.BASE_URL}/search",
                headers=headers,
                params={
                    "q": query,
                    "type": "track",
                    "limit": limit,
                    "offset": offset
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("tracks", {}).get("items", [])
    
    async def search_episodes(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search for episodes."""
        async with httpx.AsyncClient() as client:
            headers = await self._get_headers()
            response = await client.get(
                f"{self.BASE_URL}/search",
                headers=headers,
                params={
                    "q": query,
                    "type": "episode",
                    "limit": limit,
                    "offset": offset
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("episodes", {}).get("items", [])
    
    async def get_track(self, track_id: str) -> Dict[str, Any]:
        """Get track details."""
        async with httpx.AsyncClient() as client:
            headers = await self._get_headers()
            response = await client.get(
                f"{self.BASE_URL}/tracks/{track_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_episode(self, episode_id: str) -> Dict[str, Any]:
        """Get episode details."""
        async with httpx.AsyncClient() as client:
            headers = await self._get_headers()
            response = await client.get(
                f"{self.BASE_URL}/episodes/{episode_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def create_playlist(
        self,
        name: str,
        description: str = "",
        public: bool = False
    ) -> Dict[str, Any]:
        """Create a new playlist."""
        user_profile = await self.get_user_profile()
        user_id = user_profile["id"]
        
        async with httpx.AsyncClient() as client:
            headers = await self._get_headers()
            headers["Content-Type"] = "application/json"
            response = await client.post(
                f"{self.BASE_URL}/users/{user_id}/playlists",
                headers=headers,
                json={
                    "name": name,
                    "description": description,
                    "public": public
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def add_items_to_playlist(
        self,
        playlist_id: str,
        items: List[str],
        position: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add items (tracks or episodes) to a playlist.
        
        Items should be in format: "spotify:track:ID" or "spotify:episode:ID"
        """
        async with httpx.AsyncClient() as client:
            headers = await self._get_headers()
            headers["Content-Type"] = "application/json"
            
            # Items should already be in URI format (spotify:track:ID or spotify:episode:ID)
            # If not, try to convert them
            uris = []
            for item in items:
                if item.startswith("spotify:"):
                    uris.append(item)
                else:
                    # Assume track if not specified
                    uris.append(f"spotify:track:{item}")
            
            payload = {"uris": uris}
            if position is not None:
                payload["position"] = position
            
            response = await client.post(
                f"{self.BASE_URL}/playlists/{playlist_id}/tracks",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_saved_tracks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's saved/liked tracks."""
        async with httpx.AsyncClient() as client:
            headers = await self._get_headers()
            tracks = []
            offset = 0
            
            while len(tracks) < limit:
                response = await client.get(
                    f"{self.BASE_URL}/me/tracks",
                    headers=headers,
                    params={"limit": min(limit - len(tracks), 50), "offset": offset}
                )
                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])
                if not items:
                    break
                
                for item in items:
                    tracks.append(item.get("track", {}))
                
                if len(items) < 50:
                    break
                offset += len(items)
            
            return tracks[:limit]
