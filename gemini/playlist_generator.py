"""Playlist generation using Gemini AI."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import google.generativeai as genai
from config import settings
from database import Playlist
from models import PlaylistCreateResponse
from database import Ruleset
from rulesets.matcher import apply_ruleset_filters, get_date_filters
from datetime import datetime
from sqlalchemy import delete

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)


async def generate_playlist(
    db: AsyncSession,
    user_id: int,
    guidelines: str,
    matched_rulesets: List[Ruleset],
    music_only: bool,
    spotify_client
) -> PlaylistCreateResponse:
    """Generate a playlist using Gemini AI or source playlists."""
    # Check for source playlists
    source_playlist_names = []
    has_replace_mode = False
    for ruleset in matched_rulesets:
        if hasattr(ruleset, 'source_playlist_names') and ruleset.source_playlist_names:
            source_playlist_names.extend(ruleset.source_playlist_names)
        if hasattr(ruleset, 'source_mode') and ruleset.source_mode == 'replace':
            has_replace_mode = True
    
    source_tracks = []
    if source_playlist_names:
        # Get user's playlists to find IDs by name
        user_playlists = await spotify_client.get_user_playlists()
        playlist_name_to_id = {p['name']: p['id'] for p in user_playlists}
        
        for name in source_playlist_names:
            if name in playlist_name_to_id:
                tracks = await spotify_client.get_playlist_tracks(playlist_name_to_id[name])
                source_tracks.extend(tracks)
        
        # Remove duplicates by URI
        seen_uris = set()
        unique_source_tracks = []
        for track in source_tracks:
            uri = track.get('uri')
            if uri and uri not in seen_uris:
                seen_uris.add(uri)
                unique_source_tracks.append(track)
        source_tracks = unique_source_tracks
        
        # Apply ruleset filters
        for ruleset in matched_rulesets:
            source_tracks = apply_ruleset_filters(source_tracks, ruleset)
    
    # If we have source tracks and replace mode, use them directly
    if source_tracks and has_replace_mode:
        found_tracks = [track['id'] for track in source_tracks]
        found_episodes = []  # Source playlists are music-only for now
        playlist_name = f"{guidelines} (Ruleset)"
        playlist_description = f"Generated from rulesets: {', '.join([r.name for r in matched_rulesets])}"
    else:
        # Proceed with AI generation
        # Get user's top artists
        top_artists = await spotify_client.get_top_artists(limit=50, time_range="long_term")
        
        # Get user's saved podcasts (if not music_only)
        podcasts = []
        if not music_only:
            podcasts = await spotify_client.get_saved_podcasts()
        
        # Get user's saved tracks for reference
        saved_tracks = await spotify_client.get_user_saved_tracks(limit=100)
        
        # Build context for Gemini
        artists_info = "\n".join([f"- {artist['name']}" for artist in top_artists[:30]])
        podcasts_info = "\n".join([f"- {podcast['name']}" for podcast in podcasts[:20]]) if podcasts else "None"
        
        # Build ruleset constraints
        ruleset_constraints = []
        if matched_rulesets:
            for ruleset in matched_rulesets:
                date_filters = get_date_filters(ruleset)
                constraint_parts = []
                
                if date_filters["max_year"] is not None:
                    constraint_parts.append(f"all songs must be from {date_filters['max_year']} or earlier")
                if date_filters["min_year"] is not None:
                    constraint_parts.append(f"all songs must be from {date_filters['min_year']} or later")
                
                if "genre_filter" in ruleset.criteria:
                    genres = ruleset.criteria["genre_filter"]
                    if isinstance(genres, list):
                        constraint_parts.append(f"only include genres: {', '.join(genres)}")
                
                if constraint_parts:
                    ruleset_constraints.append(f"- {ruleset.name}: " + "; ".join(constraint_parts))
                else:
                    ruleset_constraints.append(f"- {ruleset.name}: follow the ruleset criteria")
        
        ruleset_text = "\n".join(ruleset_constraints) if ruleset_constraints else "None"
        
        # If we have source tracks, mention them in prompt
        source_info = ""
        if source_tracks:
            source_info = f"\nAvailable source tracks from playlists ({len(source_tracks)} tracks): prioritize using these tracks when possible."
        
        # Build prompt
        prompt = f"""You are a music playlist curator. Create a personalized playlist based on the following guidelines and constraints.

User's Guidelines:
{guidelines}{source_info}

User's Favorite Artists (prioritize songs from these artists when possible):
{artists_info}

User's Saved Podcasts (include if relevant and music_only is false):
{podcasts_info}

Active Ruleset Constraints (these are MANDATORY):
{ruleset_text}

Requirements:
1. Select tracks that match the user's guidelines
2. Prioritize tracks from the user's favorite artists list
3. MUST strictly follow all ruleset constraints (e.g., if a ruleset says "all songs before 2010", DO NOT include any songs from 2010 or later)
4. If music_only is true, do not include any podcasts
5. Use only tracks that exist in Spotify's catalog
6. Aim for 15-30 tracks/episodes total
7. Consider variety in the selection

Return a JSON response with the following format:
{{
    "playlist_name": "A descriptive name for the playlist",
    "playlist_description": "A brief description of the playlist",
    "tracks": [
        {{
            "name": "Track name",
            "artist": "Artist name",
            "year": 2008
        }},
        ...
    ],
    "episodes": [
        {{
            "name": "Episode name",
            "show": "Podcast/show name"
        }},
        ...
    ]
}}

Only include episodes if music_only is false and podcasts are relevant. Include the release year for tracks so we can validate against ruleset constraints."""

        # Generate with Gemini
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # Parse response
        response_text = response.text
        
        # Extract JSON from response (might be wrapped in markdown code blocks)
        import json
        import re
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("Could not parse JSON from Gemini response")
        
        playlist_data = json.loads(json_str)
        
        playlist_name = playlist_data.get("playlist_name", "Generated Playlist")
        playlist_description = playlist_data.get("playlist_description", "")
        recommended_tracks = playlist_data.get("tracks", [])
        recommended_episodes = playlist_data.get("episodes", []) if not music_only else []
        
        # Search for tracks on Spotify
        found_tracks = []
        for track in recommended_tracks:
            query = f"{track['name']} {track['artist']}"
            search_results = await spotify_client.search_tracks(query, limit=5)
            
            if search_results:
                # Try to find best match
                for result in search_results:
                    # Check if year matches (if specified)
                    album = result.get("album", {})
                    release_date = album.get("release_date", "")
                    if release_date and len(release_date) >= 4:
                        try:
                            track_year = int(release_date[:4])
                            if "year" in track and abs(track_year - track["year"]) > 2:
                                continue  # Year mismatch
                        except (ValueError, TypeError):
                            pass
                    
                    # Check if artist matches
                    artists = [a["name"].lower() for a in result.get("artists", [])]
                    if track["artist"].lower() in artists or any(track["artist"].lower() in a for a in artists):
                        found_tracks.append(result["id"])
                        break
        
        # Search for episodes on Spotify
        found_episodes = []
        for episode in recommended_episodes:
            query = f"{episode.get('name', '')} {episode.get('show', '')}"
            if not query.strip():
                continue
            search_results = await spotify_client.search_episodes(query, limit=5)
            
            if search_results:
                # Try to find best match
                for result in search_results:
                    show_name = result.get("show", {}).get("name", "").lower()
                    episode_show = episode.get("show", "").lower()
                    if episode_show and (episode_show in show_name or show_name in episode_show):
                        found_episodes.append(result["id"])
                        break
        
        # Apply ruleset filters to found tracks
        if matched_rulesets:
            track_details = []
            for track_id in found_tracks:
                try:
                    track = await spotify_client.get_track(track_id)
                    track_details.append(track)
                except Exception:
                    continue
            
            filtered_track_details = track_details
            for ruleset in matched_rulesets:
                filtered_track_details = apply_ruleset_filters(filtered_track_details, ruleset)
            
            found_tracks = [track["id"] for track in filtered_track_details]
        
        # If we have source tracks, combine them
        if source_tracks:
            source_track_ids = [track['id'] for track in source_tracks]
            found_tracks.extend(source_track_ids)
            # Remove duplicates
            found_tracks = list(set(found_tracks))
    
    # Handle daily drive special case and name conflicts
    if "daily drive" in guidelines.lower():
        # Override name for daily drive
        day_name = datetime.now().strftime('%A')
        playlist_name = f"Daily Drive - {day_name}"
        
        # Delete existing playlists with this name
        user_playlists = await spotify_client.get_user_playlists()
        for p in user_playlists:
            if p['name'] == playlist_name:
                await spotify_client.delete_playlist(p['id'])
                # Delete from database
                await db.execute(delete(Playlist).where(Playlist.spotify_playlist_id == p['id']))
        await db.commit()
    else:
        # Check for existing playlist with same name
        user_playlists = await spotify_client.get_user_playlists()
        existing_names = {p['name'] for p in user_playlists}
        if playlist_name in existing_names:
            raise ValueError(f"Playlist name '{playlist_name}' already exists. Please choose a different name.")
    
    # Create playlist on Spotify
    if not found_tracks and not found_episodes:
        raise ValueError("No tracks or episodes found matching the recommendations")
    
    playlist = await spotify_client.create_playlist(
        name=playlist_name,
        description=playlist_description,
        public=False
    )
    
    playlist_id = playlist["id"]
    spotify_url = playlist.get("external_urls", {}).get("spotify", f"https://open.spotify.com/playlist/{playlist_id}")
    
    # Add tracks and episodes to playlist
    all_items = []
    if found_tracks:
        # Format as spotify:track: URIs
        all_items.extend([f"spotify:track:{track_id}" for track_id in found_tracks])
    if found_episodes:
        # Format as spotify:episode: URIs
        all_items.extend([f"spotify:episode:{episode_id}" for episode_id in found_episodes])
    
    if all_items:
        # Spotify API allows adding up to 100 items at once
        for i in range(0, len(all_items), 100):
            batch = all_items[i:i+100]
            await spotify_client.add_items_to_playlist(playlist_id, batch)
    
    # Store playlist in database
    db_playlist = Playlist(
        user_id=user_id,
        spotify_playlist_id=playlist_id,
        name=playlist_name,
        guidelines_used=guidelines,
        rulesets_applied=[r.name for r in matched_rulesets] if matched_rulesets else []
    )
    db.add(db_playlist)
    await db.commit()
    
    return PlaylistCreateResponse(
        playlist_id=playlist_id,
        name=playlist_name,
        spotify_url=spotify_url,
        rulesets_applied=[r.name for r in matched_rulesets] if matched_rulesets else [],
        tracks_count=len(found_tracks) + len(found_episodes)
    )
