# AI Coding Agent Instructions for Spotify Playlist Builder

## Architecture Overview
This is a FastAPI-based Spotify playlist generator that uses Google Gemini AI for conversational playlist creation. The app integrates Spotify OAuth, stores user data in SQLite via SQLAlchemy async, and generates playlists by randomly selecting tracks from followed artists with optional ruleset filtering.

**Core Components:**
- `routes/`: FastAPI routers for auth, playlists, chat, rulesets, users
- `gemini/`: AI-powered chat handling and playlist generation logic
- `spotify/`: Spotify API client with OAuth and track retrieval
- `rulesets/`: Playlist filtering rules based on genres, years, keywords
- `users/`: User management and token encryption
- `utils/`: Session handling and encryption utilities

## Key Patterns & Conventions

### Async Everywhere
Use `async/await` for all database operations and API calls. Example:
```python
async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
```

### Pydantic Models
Request/response validation uses Pydantic in `models.py`. Database models use SQLAlchemy in `database.py`. Always use `from_attributes = True` in response models.

### Session-Based Auth
User authentication via `utils/session.py`. Get active user ID with:
```python
user_id = get_active_user_id(request)
```

### Gemini Intent Parsing
Chat messages are parsed by Gemini to extract structured parameters. System prompts in `gemini/chat_handler.py` define JSON extraction format for actions like playlist creation.

### Playlist Generation Flow
1. Parse user guidelines via Gemini to extract: `num_songs`, `is_daily_drive`, `allow_explicit`, `ruleset_name`, `guidelines`, `music_only`
2. Fetch followed artists from Spotify
3. Randomly select artists and their top tracks
4. Apply explicit filtering (5 retries for non-explicit tracks if `allow_explicit=False`)
5. Apply ruleset constraints (genres, years)
6. Trim to exact `num_songs`
7. Add daily drive intro (position 0, not counted in total)

### Ruleset Matching
Rulesets filter tracks post-selection. Criteria include `min_year`, `max_year`, `years_back`, `genre_filter`. Match via keywords in guidelines or explicit name.

### Spotify Integration
Use `SpotifyAPIClient` for API calls. Tokens are encrypted in DB. Key methods: `get_followed_artists()`, `get_artist_top_tracks()`, `create_playlist()`.

## Developer Workflows

### Running the App
- Use `.\start.ps1` (PowerShell) to start server on port 8000
- Activates virtual environment if present (`venv/` or `.venv/`)
- API docs at `http://localhost:8000/docs`

### Testing
Run with `pytest` in `test/` directory. Uses `pytest-asyncio` for async tests. Example test structure in `test/conftest.py` for DB fixtures.

### Database
SQLite with aiosqlite. Tables auto-created on startup via `database/init_db()`. Seeds initial rulesets from `database_seed.py`.

### Environment
Configure via `.env` file with Pydantic settings. Required: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `GEMINI_API_KEY`, `TOKEN_ENCRYPTION_KEY`.

## Common Tasks
- **Add new route**: Create in appropriate `routes/` file, include in `main.py`
- **Modify playlist logic**: Update `gemini/playlist_generator.py`, ensure async
- **Add ruleset criteria**: Extend `criteria` dict in `Ruleset` model and filtering logic
- **Handle Spotify errors**: Check for token refresh in `spotify/api_client.py`