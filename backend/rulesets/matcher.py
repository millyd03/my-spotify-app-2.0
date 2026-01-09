"""Ruleset matching logic."""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime

from rulesets.service import get_all_rulesets
from database import Ruleset


async def match_rulesets(db: AsyncSession, guidelines: str) -> List[Ruleset]:
    """Match rulesets based on keywords in guidelines text."""
    # Get all active rulesets
    all_rulesets = await get_all_rulesets(db, active_only=True)
    
    if not all_rulesets:
        return []
    
    # Convert guidelines to lowercase for case-insensitive matching
    guidelines_lower = guidelines.lower()
    
    # Match rulesets
    matched = []
    for ruleset in all_rulesets:
        # Check if any keyword matches
        for keyword in ruleset.keywords:
            if keyword.lower() in guidelines_lower:
                matched.append(ruleset)
                break  # Don't add the same ruleset twice
    
    return matched


def get_date_filters(ruleset) -> dict:
    """Calculate actual date range filters from ruleset criteria."""
    current_year = datetime.now().year
    criteria = ruleset.criteria if hasattr(ruleset, 'criteria') else {}
    
    min_year = None
    max_year = None
    
    # Handle max_year (e.g., throwback: max_year = 2010)
    if "max_year" in criteria:
        max_year = criteria["max_year"]
    
    # Handle min_year
    if "min_year" in criteria:
        min_year = criteria["min_year"]
    
    # Handle years_back (e.g., fresh: years_back = 5 → min_year = current_year - 5)
    if "years_back" in criteria:
        years_back = criteria["years_back"]
        min_year = current_year - years_back
    
    return {
        "min_year": min_year,
        "max_year": max_year
    }


def apply_ruleset_filters(tracks: List[dict], ruleset) -> List[dict]:
    """Filter tracks based on ruleset criteria."""
    if not ruleset or not tracks:
        return tracks
    
    criteria = ruleset.criteria if hasattr(ruleset, 'criteria') else {}
    date_filters = get_date_filters(ruleset)
    
    filtered = []
    for track in tracks:
        # Apply date filter if specified
        if date_filters["min_year"] is not None or date_filters["max_year"] is not None:
            # Get release date from track
            album = track.get("album", {})
            release_date = album.get("release_date", "")
            
            if not release_date:
                # Skip tracks without release date if date filter is active
                continue
            
            # Parse release date (format: YYYY-MM-DD or YYYY)
            try:
                if len(release_date) >= 4:
                    track_year = int(release_date[:4])
                else:
                    continue
            except (ValueError, TypeError):
                continue
            
            # Check year constraints
            if date_filters["max_year"] is not None and track_year > date_filters["max_year"]:
                continue
            
            if date_filters["min_year"] is not None and track_year < date_filters["min_year"]:
                continue
        
        # Apply genre filter if specified
        if "genre_filter" in criteria:
            genre_filter = criteria["genre_filter"]
            # This could be a list of allowed genres or a pattern
            # For now, we'll implement a simple inclusion check
            track_genres = []
            for artist in track.get("artists", []):
                track_genres.extend(artist.get("genres", []))
            
            if isinstance(genre_filter, list) and genre_filter:
                # Check if any track genre matches any filter genre
                if not any(genre.lower() in [g.lower() for g in track_genres] for genre in genre_filter):
                    continue
        
        filtered.append(track)
    
    return filtered
