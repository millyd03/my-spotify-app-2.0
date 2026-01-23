"""Chat handler using Gemini AI for conversational playlist and ruleset management."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional, Tuple
import google.generativeai as genai
import json
import re
from datetime import datetime

from config import settings
from models import ChatMessage, ChatResponse, RulesetCreate, RulesetUpdate
from database import Ruleset
from rulesets.service import (
    get_all_rulesets,
    get_ruleset_by_name,
    create_ruleset,
    update_ruleset,
    delete_ruleset
)
from rulesets.matcher import match_rulesets

class ChatHandler:
    """Handles chat conversations using Gemini AI."""
    
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(model_name='gemini-2.5-flash')
    
    async def process_message(
        self,
        user_message: str,
        conversation_history: List[ChatMessage],
        db: AsyncSession,
        user_id: int,
        spotify_client=None,
        playlist_generator=None
    ) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
        """
        Process a user message and return response.
        
        Returns:
            Tuple of (response_message, action_type, action_data)
        """
        # Build conversation context
        conversation_text = self._build_conversation_context(conversation_history, user_message)
        
        # Get available rulesets for context
        all_rulesets = await get_all_rulesets(db, active_only=False)
        rulesets_context = self._build_rulesets_context(all_rulesets)
        
        # Build system prompt
        system_prompt = f"""You are a helpful assistant for a Spotify playlist generator. You can help users:
1. Generate playlists by understanding their music preferences
2. Create, edit, delete, and list rulesets (filters for playlist generation)

Available Rulesets:
{rulesets_context}

When a user wants to:
- **Create a playlist**: Extract the number of songs, whether it's a daily drive playlist, whether to allow explicit songs, the ruleset name, and any additional guidelines. Respond naturally, then the system will generate the playlist.
- **Create a ruleset**: Extract name, keywords (list), description, and criteria (dict with min_year, max_year, years_back, or genre_filter).
- **Edit a ruleset**: Identify which ruleset (by name or ID) and what fields to update.
- **Delete a ruleset**: Identify which ruleset to delete (by name or ID).
- **List rulesets**: Provide a helpful response about available rulesets.

For ruleset creation, extract the structure as JSON. The criteria can include:
- max_year: maximum year (e.g., 2010)
- min_year: minimum year (e.g., 2000)
- years_back: number of years back from current year
- genre_filter: list of genres (e.g., ["rock", "alternative"])

Respond naturally in a conversational way. If the user wants to perform an action, end your response with a JSON block in this format:
```json
{{
    "intent": "create_playlist|create_ruleset|update_ruleset|delete_ruleset|list_rulesets",
    "data": {{...}}
}}
```

For create_playlist intent:
{{
    "intent": "create_playlist",
    "data": {{
        "num_songs": 20,
        "is_daily_drive": false,
        "allow_explicit": true,
        "ruleset_name": "ruleset_name",
        "guidelines": "additional description of playlist",
        "music_only": true/false
    }}
}}

For create_ruleset intent:
{{
    "intent": "create_ruleset",
    "data": {{
        "name": "ruleset_name",
        "keywords": ["keyword1", "keyword2"],
        "description": "optional description",
        "criteria": {{
            "min_year": 2000,
            "max_year": 2010,
            "genre_filter": ["rock"]
        }},
        "is_active": true
    }}
}}

For update_ruleset intent:
{{
    "intent": "update_ruleset",
    "data": {{
        "ruleset_identifier": "name or id",
        "updates": {{
            "name": "new_name",
            "keywords": ["new", "keywords"],
            "criteria": {{...}}
        }}
    }}
}}

For delete_ruleset intent:
{{
    "intent": "delete_ruleset",
    "data": {{
        "ruleset_identifier": "name or id"
    }}
}}

For list_rulesets, just respond naturally without JSON.

Conversation history:
{conversation_text}

Now respond to the user's latest message:"""

        # Generate response
        response = self.model.generate_content(system_prompt)
        response_text = response.text
        
        # Extract intent JSON if present
        intent_data = self._extract_intent_json(response_text)
        
        action_type = None
        action_data = None
        
        # Process intent if found
        if intent_data:
            intent = intent_data.get("intent")
            data = intent_data.get("data", {})
            
            if intent == "create_playlist" and spotify_client and playlist_generator:
                # Generate playlist
                num_songs = data.get("num_songs", 20)
                is_daily_drive = data.get("is_daily_drive", False)
                allow_explicit = data.get("allow_explicit", True)
                ruleset_name = data.get("ruleset_name")
                guidelines = data.get("guidelines", "")
                music_only = data.get("music_only", False)
                
                # Get ruleset if specified
                matched_rulesets = []
                if ruleset_name:
                    ruleset = await get_ruleset_by_name(db, ruleset_name)
                    if ruleset:
                        matched_rulesets = [ruleset]
                else:
                    # Fallback to keyword matching
                    matched_rulesets = await match_rulesets(db, guidelines or f"{num_songs} songs {'daily drive' if is_daily_drive else ''} {'non-explicit' if not allow_explicit else ''}")
                
                playlist_result = await playlist_generator(
                    db=db,
                    user_id=user_id,
                    num_songs=num_songs,
                    is_daily_drive=is_daily_drive,
                    allow_explicit=allow_explicit,
                    ruleset=matched_rulesets[0] if matched_rulesets else None,
                    guidelines=guidelines,
                    music_only=music_only,
                    spotify_client=spotify_client
                )
                action_type = "playlist_created"
                action_data = {
                    "playlist_id": playlist_result.playlist_id,
                    "name": playlist_result.name,
                    "spotify_url": playlist_result.spotify_url,
                    "rulesets_applied": playlist_result.rulesets_applied,
                    "tracks_count": playlist_result.tracks_count
                }
            
            elif intent == "create_ruleset":
                # Create ruleset
                try:
                    ruleset_data = RulesetCreate(**data)
                    ruleset = await create_ruleset(db, ruleset_data)
                    action_type = "ruleset_created"
                    action_data = {
                        "id": ruleset.id,
                        "name": ruleset.name,
                        "keywords": ruleset.keywords,
                        "description": ruleset.description,
                        "criteria": ruleset.criteria
                    }
                except ValueError as e:
                    # Ruleset already exists or invalid data
                    response_text = f"{response_text}\n\n⚠️ Error: {str(e)}"
            
            elif intent == "update_ruleset":
                # Update ruleset
                identifier = data.get("ruleset_identifier")
                updates = data.get("updates", {})
                
                # Find ruleset by name or ID
                if isinstance(identifier, str) and identifier.isdigit():
                    ruleset_id = int(identifier)
                else:
                    # Try to find by name
                    ruleset = await get_ruleset_by_name(db, identifier)
                    if ruleset:
                        ruleset_id = ruleset.id
                    else:
                        response_text = f"{response_text}\n\n⚠️ Error: Ruleset '{identifier}' not found."
                        return response_text, action_type, action_data
                
                try:
                    update_data = RulesetUpdate(**updates)
                    ruleset = await update_ruleset(db, ruleset_id, update_data)
                    if ruleset:
                        action_type = "ruleset_updated"
                        action_data = {
                            "id": ruleset.id,
                            "name": ruleset.name,
                            "keywords": ruleset.keywords,
                            "description": ruleset.description,
                            "criteria": ruleset.criteria
                        }
                    else:
                        response_text = f"{response_text}\n\n⚠️ Error: Ruleset not found."
                except ValueError as e:
                    response_text = f"{response_text}\n\n⚠️ Error: {str(e)}"
            
            elif intent == "delete_ruleset":
                # Delete ruleset
                identifier = data.get("ruleset_identifier")
                
                # Find ruleset by name or ID
                if isinstance(identifier, str) and identifier.isdigit():
                    ruleset_id = int(identifier)
                else:
                    # Try to find by name
                    ruleset = await get_ruleset_by_name(db, identifier)
                    if ruleset:
                        ruleset_id = ruleset.id
                    else:
                        response_text = f"{response_text}\n\n⚠️ Error: Ruleset '{identifier}' not found."
                        return response_text, action_type, action_data
                
                success = await delete_ruleset(db, ruleset_id)
                if success:
                    action_type = "ruleset_deleted"
                    action_data = {"ruleset_id": ruleset_id}
                else:
                    response_text = f"{response_text}\n\n⚠️ Error: Ruleset not found."
            
            elif intent == "list_rulesets":
                # List rulesets
                all_rulesets = await get_all_rulesets(db, active_only=False)
                action_type = "ruleset_listed"
                action_data = {
                    "rulesets": [
                        {
                            "id": r.id,
                            "name": r.name,
                            "keywords": r.keywords,
                            "description": r.description,
                            "criteria": r.criteria,
                            "is_active": r.is_active
                        }
                        for r in all_rulesets
                    ]
                }
                # Enhance response with ruleset list
                rulesets_text = "\n".join([
                    f"- {r.name}: {r.description or 'No description'} (Keywords: {', '.join(r.keywords)})"
                    for r in all_rulesets
                ])
                if rulesets_text:
                    response_text = f"{response_text}\n\nAvailable rulesets:\n{rulesets_text}"
        
        # Clean up response (remove JSON block if present)
        response_text = self._clean_response_text(response_text)
        
        return response_text, action_type, action_data
    
    def _build_conversation_context(self, history: List[ChatMessage], current_message: str) -> str:
        """Build conversation context string from history."""
        if not history:
            return f"User: {current_message}"
        
        context_parts = []
        for msg in history[-10:]:  # Last 10 messages for context
            role = "User" if msg.role == "user" else "Assistant"
            context_parts.append(f"{role}: {msg.content}")
        
        context_parts.append(f"User: {current_message}")
        return "\n".join(context_parts)
    
    def _build_rulesets_context(self, rulesets: List[Ruleset]) -> str:
        """Build context string about available rulesets."""
        if not rulesets:
            return "No rulesets available."
        
        context_parts = []
        for r in rulesets:
            status = "active" if r.is_active else "inactive"
            context_parts.append(
                f"- {r.name} ({status}): Keywords: {', '.join(r.keywords)}. "
                f"Description: {r.description or 'No description'}. "
                f"Criteria: {json.dumps(r.criteria)}"
            )
        
        return "\n".join(context_parts)
    
    def _extract_intent_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract intent JSON from response text."""
        # Look for JSON code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object directly
        json_match = re.search(r'\{\s*"intent"\s*:\s*"[^"]+",\s*"data"\s*:\s*\{.*?\}\s*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _clean_response_text(self, text: str) -> str:
        """Remove JSON code blocks from response text."""
        # Remove JSON code blocks
        text = re.sub(r'```(?:json)?\s*\{.*?\}\s*```', '', text, flags=re.DOTALL)
        # Remove standalone JSON objects
        text = re.sub(r'\{\s*"intent"\s*:\s*"[^"]+",\s*"data"\s*:\s*\{.*?\}\s*\}', '', text, flags=re.DOTALL)
        return text.strip()


# Global instance
_chat_handler = None

def get_chat_handler() -> ChatHandler:
    """Get or create chat handler instance."""
    global _chat_handler
    if _chat_handler is None:
        _chat_handler = ChatHandler()
    return _chat_handler
