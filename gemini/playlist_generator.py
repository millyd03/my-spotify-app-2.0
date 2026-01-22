"""Playlist generation using Gemini AI."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import google.genai as genai
import math
from collections import defaultdict
from datetime import datetime
from config import settings
from database import Playlist
from models import PlaylistCreateResponse
from database import Ruleset
from rulesets.matcher import apply_ruleset_filters, get_date_filters
from datetime import datetime
from sqlalchemy import delete
from definition.day_intros import DayIntros
from definition.artist_tiers import ArtistTiers


async def generate_playlist(
    db: AsyncSession,
    user_id: int,
    num_songs: int,
    is_daily_drive: bool,
    allow_explicit: bool,
    ruleset: Optional[Ruleset],
    guidelines: Optional[str],
    music_only: bool,
    spotify_client
) -> PlaylistCreateResponse:
    """Generate a playlist using Gemini AI or source playlists."""
    # Ensure guidelines is a string
    guidelines = guidelines or ""
    
    # Check for source playlists
    source_playlist_names = []
    has_replace_mode = False
    if ruleset and hasattr(ruleset, 'source_playlist_names') and ruleset.source_playlist_names:
        source_playlist_names.extend(ruleset.source_playlist_names)
    if ruleset and hasattr(ruleset, 'source_mode') and ruleset.source_mode == 'replace':
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
        if ruleset:
            source_tracks = apply_ruleset_filters(source_tracks, ruleset)
    
    # If we have source tracks and replace mode, use them directly
    if source_tracks and has_replace_mode:
        found_tracks = [track['id'] for track in source_tracks]
        found_episodes = []  # Source playlists are music-only for now
        playlist_name = f"{guidelines} ({ruleset.name if ruleset else 'Ruleset'})"
        playlist_description = f"Generated from ruleset: {ruleset.name if ruleset else 'Unknown'}"
    else:
        # Proceed with AI generation
        # Get user's followed artists (fallback to top artists if permission not granted)
        followed_artists = []
        try:
            followed_artists = await spotify_client.get_followed_artists(limit=50)
        except Exception as e:
            print(f"Warning: Could not fetch followed artists ({e}), falling back to top artists")
            followed_artists = await spotify_client.get_top_artists(limit=50, time_range="long_term")
        
        # Get user's saved podcasts (if not music_only)
        podcasts = []
        if not music_only:
            podcasts = await spotify_client.get_saved_podcasts()
        
        # Get user's saved tracks for reference
        saved_tracks = await spotify_client.get_user_saved_tracks(limit=100)
        
        # Build context for Gemini
        artists_info = "\n".join([f"- {artist['name']}" for artist in followed_artists[:30]])
        podcasts_info = "\n".join([f"- {podcast['name']}" for podcast in podcasts[:20]]) if podcasts else "None"
        
        # Build ruleset constraints
        ruleset_constraints = []
        if ruleset:
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
        
        # Generate playlist from followed artists using tier-based selection
        import random
        
        found_tracks = []
        found_episodes = []  # Skip episodes for now
        
        if followed_artists:
            # Get artist details and assign tiers
            artist_details = []
            for artist in followed_artists:
                try:
                    details = await spotify_client.get_artist(artist['id'])
                    followers = details.get('followers', {}).get('total', 0)
                    tier = None
                    for t in ArtistTiers:
                        if followers <= t.value:
                            tier = t
                            break
                    if tier is None:
                        tier = ArtistTiers.TIER_6
                    artist_details.append({
                        'id': artist['id'],
                        'name': artist['name'],
                        'tier': tier,
                        'followers': followers
                    })
                except Exception:
                    # If can't get details, assign lowest tier
                    artist_details.append({
                        'id': artist['id'],
                        'name': artist['name'],
                        'tier': ArtistTiers.TIER_1,
                        'followers': 0
                    })
            
            # Select all followed artists
            selected_artists = artist_details
            
            # Calculate limits based on follower tiers
            artist_limits = {}
            for artist in selected_artists:
                f = artist['followers']
                if f < ArtistTiers.TIER_1.value:
                    percent = 0.02
                elif f < ArtistTiers.TIER_2.value:
                    percent = 0.05
                elif f < ArtistTiers.TIER_3.value:
                    percent = 0.10
                elif f < ArtistTiers.TIER_4.value:
                    percent = 0.15
                elif f < ArtistTiers.TIER_5.value:
                    percent = 0.20
                else:
                    percent = 1.0
                max_songs = math.ceil(num_songs * percent) if percent < 1.0 else num_songs
                artist_limits[artist['id']] = max_songs
            
            artist_counts = defaultdict(int)
            artist_track_lists = {}
            for artist in selected_artists:
                artist_track_lists[artist['id']] = await spotify_client.get_artist_top_tracks(artist['id'])
            
            tracks_needed = num_songs
            while tracks_needed > 0:
                available_artists = [a for a in selected_artists if artist_counts[a['id']] < artist_limits[a['id']] and artist_track_lists[a['id']]]
                if not available_artists:
                    break
                artist = random.choice(available_artists)
                track = random.choice(artist_track_lists[artist['id']])
                artist_track_lists[artist['id']].remove(track)
                
                # Check explicit filter
                if not allow_explicit and track.get('explicit', False):
                    retry_count = 0
                    while retry_count < 5 and artist_track_lists[artist['id']] and (not allow_explicit and track.get('explicit', False)):
                        if artist_track_lists[artist['id']]:
                            track = random.choice(artist_track_lists[artist['id']])
                            artist_track_lists[artist['id']].remove(track)
                        retry_count += 1
                    if not allow_explicit and track.get('explicit', False):
                        continue
                
                found_tracks.append(track['id'])
                artist_counts[artist['id']] += 1
                tracks_needed -= 1
        
        playlist_name = guidelines if guidelines else "Generated Playlist"
        playlist_description = f"Playlist with {num_songs} songs from followed artists"
        
        # Apply ruleset filters to found tracks
        if ruleset:
            track_details = []
            for track_id in found_tracks:
                try:
                    track = await spotify_client.get_track(track_id)
                    track_details.append(track)
                except Exception:
                    continue
            
            filtered_track_details = track_details
            filtered_track_details = apply_ruleset_filters(filtered_track_details, ruleset)
            
            found_tracks = [track["id"] for track in filtered_track_details]
        
        # Trim to num_songs
        if len(found_tracks) > num_songs:
            found_tracks = found_tracks[:num_songs]
        
        # If we have source tracks, combine them
        if source_tracks:
            source_track_ids = [track['id'] for track in source_tracks]
            found_tracks.extend(source_track_ids)
            # Remove duplicates
            found_tracks = list(set(found_tracks))
        
        # Trim to num_songs
        if len(found_tracks) > num_songs:
            found_tracks = found_tracks[:num_songs]
    
    # Handle daily drive special case and name conflicts
    if is_daily_drive:
        # Override name for daily drive
        day_name = datetime.now().strftime('%A')
        playlist_name = f"Daily Drive - {day_name}"
        
        # Ensure guidelines has a value for daily drive
        if not guidelines:
            guidelines = f"Daily drive playlist for {day_name}"
        
        # Delete existing playlists with this name
        user_playlists = await spotify_client.get_user_playlists()
        for p in user_playlists:
            if p['name'] == playlist_name:
                try:
                    await spotify_client.delete_playlist(p['id'])
                    print(f"Deleted existing daily drive playlist: {p['id']}")
                except Exception as e:
                    print(f"Warning: Failed to delete playlist {p['id']}: {e}")
                # Delete from database regardless
                try:
                    await db.execute(delete(Playlist).where(Playlist.spotify_playlist_id == p['id']))
                except Exception as e:
                    print(f"Warning: Failed to delete playlist from database {p['id']}: {e}")
        await db.commit()
        
        # Add day intro as first track
        day_enum = day_name.upper()
        if hasattr(DayIntros, day_enum):
            intro_track_id = getattr(DayIntros, day_enum).value
            found_tracks.insert(0, intro_track_id)
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
        # For daily drive, add intro at position 0 first
        if is_daily_drive and all_items:
            await spotify_client.add_items_to_playlist(playlist_id, [all_items[0]], position=0)
            remaining_items = all_items[1:]
        else:
            remaining_items = all_items
        
        # Add remaining items in batches
        for i in range(0, len(remaining_items), 100):
            batch = remaining_items[i:i+100]
            await spotify_client.add_items_to_playlist(playlist_id, batch)
    
    # Store playlist in database
    db_playlist = Playlist(
        user_id=user_id,
        spotify_playlist_id=playlist_id,
        name=playlist_name,
        guidelines_used=guidelines or "",
        rulesets_applied=[ruleset.name] if ruleset else []
    )
    db.add(db_playlist)
    await db.commit()
    
    return PlaylistCreateResponse(
        playlist_id=playlist_id,
        name=playlist_name,
        spotify_url=spotify_url,
        rulesets_applied=[ruleset.name] if ruleset else [],
        tracks_count=len(found_tracks) + len(found_episodes) - (1 if is_daily_drive else 0)
    )
