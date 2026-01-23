"""Database models and setup."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON
from datetime import datetime, timezone
from typing import AsyncGenerator
from config import settings

# Convert SQLite URL to async-compatible format
database_url = settings.database_url.replace("sqlite://", "sqlite+aiosqlite://")

engine = create_async_engine(
    database_url,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


class User(Base):
    """User model for storing Spotify OAuth credentials."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    spotify_user_id = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    access_token = Column(Text, nullable=False)  # Encrypted
    refresh_token = Column(Text, nullable=False)  # Encrypted
    token_expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Playlist(Base):
    """Playlist model for storing generated playlist metadata."""
    __tablename__ = "playlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    spotify_playlist_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    guidelines_used = Column(Text, nullable=False)
    rulesets_applied = Column(JSON, nullable=True)  # Array of ruleset names
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Ruleset(Base):
    """Ruleset model for storing playlist generation rules."""
    __tablename__ = "rulesets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    keywords = Column(JSON, nullable=False)  # Array of trigger keywords
    description = Column(Text, nullable=True)
    criteria = Column(JSON, nullable=False)  # Filter criteria object
    source_playlist_names = Column(JSON, nullable=True)  # Array of source playlist names
    source_mode = Column(String, nullable=True)  # 'replace' or 'supplement'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
