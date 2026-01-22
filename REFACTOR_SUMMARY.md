# Playlist Generation Refactor Summary

## Overview
Refactored the playlist generation process to use a more structured, flag-based approach with explicit user input parsing and random song selection from followed artists.

## Changes Made

### 1. **[gemini/chat_handler.py](gemini/chat_handler.py)** - Enhanced User Input Parsing
- Updated system prompt to extract explicit playlist parameters:
  - `num_songs`: Number of songs to include (default: 20)
  - `is_daily_drive`: Whether it's a daily drive playlist (boolean)
  - `allow_explicit`: Whether to allow explicit songs (boolean)
  - `ruleset_name`: Specific ruleset to apply
  - `guidelines`: Additional description (optional)
  - `music_only`: Exclude podcasts (boolean)

- Modified `create_playlist` intent handling to pass parsed parameters to playlist generator
- Fallback to keyword matching if ruleset name not explicitly provided

### 2. **[spotify/api_client.py](spotify/api_client.py)** - New Spotify API Methods
Added two new methods:
- `get_followed_artists(limit=50)`: Retrieves user's followed artists (replaced top artists)
- `get_artist_top_tracks(artist_id, country="US")`: Gets top tracks for a specific artist

### 3. **[gemini/playlist_generator.py](gemini/playlist_generator.py)** - Core Refactoring

#### Function Signature Changed
```python
# OLD: matched_rulesets: List[Ruleset]
# NEW: ruleset: Optional[Ruleset]
async def generate_playlist(
    db: AsyncSession,
    user_id: int,
    num_songs: int,           # NEW
    is_daily_drive: bool,     # NEW
    allow_explicit: bool,     # NEW
    ruleset: Optional[Ruleset],  # CHANGED
    guidelines: str,
    music_only: bool,
    spotify_client
) -> PlaylistCreateResponse:
```

#### Random Song Selection Implementation
Replaced Gemini-driven track recommendations with random selection from followed artists:
1. Retrieves user's followed artists
2. Randomly selects up to 10 artists
3. For each selected artist:
   - Fetches top tracks
   - Randomly selects from those tracks
   - **Explicit Filtering**: If `allow_explicit=False`:
     - Checks each track's explicit flag
     - Retries up to 5 times to find non-explicit track
     - Uses last selected song if retries exhausted
   - Accumulates tracks until `num_songs` reached

#### Daily Drive Handling
- Properly checks `is_daily_drive` boolean instead of string matching
- Adds appropriate day intro from `definition/day_intros.py`
- Daily intro song **does not count** toward the `num_songs` total

#### Song Count Enforcement
- Final playlist is trimmed to exactly `num_songs`
- Daily intro is added as position 0, separate from count
- Ruleset filters may reduce tracks, but final count matches `num_songs`

#### Ruleset Application
- Single ruleset applied post-selection (if provided)
- Tracks filtered for date ranges and genres
- All ruleset constraints are mandatory

### Behavior Changes

| Aspect | Before | After |
|--------|--------|-------|
| Artist Source | Top artists (listening history) | Followed artists |
| Track Selection | Gemini picks specific tracks | Random selection from top tracks |
| Explicit Filter | Not implemented | Implemented with 5-retry logic |
| Daily Drive | String match in guidelines | Boolean flag |
| Ruleset Matching | Keyword-based auto-matching | Explicit name or fallback to keywords |
| Song Count | 15-30 (soft guideline) | Exact `num_songs` (strict) |
| Ruleset Count | Multiple rulesets | Single ruleset |

## Flow Diagram

```
User Chat
    ↓
parse_intent() → Extract [num_songs, is_daily_drive, allow_explicit, ruleset_name, guidelines]
    ↓
get_ruleset_by_name() (if provided) or match_rulesets() (fallback)
    ↓
generate_playlist()
    ├─ Get followed_artists()
    ├─ Randomly select artists and their top tracks
    ├─ Filter explicit (with retry) if allow_explicit=False
    ├─ Apply ruleset constraints
    ├─ Trim to num_songs
    └─ Add daily intro if is_daily_drive=True (doesn't count toward num_songs)
    ↓
Create Playlist & Store in DB
```

## Testing Recommendations

1. **Input Parsing**: Test that Gemini correctly extracts all 5 parameters
2. **Followed Artists**: Verify `get_followed_artists()` returns expected artists
3. **Random Selection**: Ensure tracks vary across multiple playlist generations
4. **Explicit Filtering**:
   - Test with `allow_explicit=True` (no filtering)
   - Test with `allow_explicit=False` (filters explicit tracks)
   - Test retry logic (5 retries before giving up)
5. **Song Count**:
   - Verify playlist has exactly `num_songs` songs
   - Verify daily intro is position 0 but not counted in `num_songs`
6. **Ruleset Application**: Verify filters are applied after track selection
7. **Daily Drive**: Confirm correct day intro and playlist name format

## Rollback
If needed, the changes are isolated to these three files. The old Gemini-based prompt logic can be restored from git history.

## Future Improvements
- Add paginated followed artists retrieval (handle >50 artists)
- Implement track caching to reduce API calls
- Add more granular genre filtering
- Support multiple rulesets in sequence
- Add user preferences for artist weighting
