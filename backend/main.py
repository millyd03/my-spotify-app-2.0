"""Main FastAPI application."""
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from config import settings
from database import init_db, get_db
from routes import auth, users, playlists, user_data, rulesets, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    await init_db()
    
    # Seed initial rulesets
    from database_seed import seed_initial_rulesets
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await seed_initial_rulesets(db)
    
    yield
    
    # Shutdown
    pass


app = FastAPI(
    title="Spotify Gemini Playlist Builder",
    description="AI-powered playlist generation using Spotify API and Google Gemini",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
cors_origins = ["*"] if settings.allowed_origins == "*" else [origin.strip() for origin in settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    max_age=86400 * 7,  # 7 days
    same_site="lax"
)


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(playlists.router, prefix="/api/playlists", tags=["playlists"])
app.include_router(user_data.router, prefix="/api/user", tags=["user-data"])
app.include_router(rulesets.router, prefix="/api/rulesets", tags=["rulesets"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Spotify Gemini Playlist Builder API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
