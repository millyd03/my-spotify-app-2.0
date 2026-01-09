"""Configuration management for the application."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Spotify API Configuration
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str = "http://localhost:8000/auth/callback"
    
    # Gemini AI Configuration
    gemini_api_key: str
    
    # Database Configuration
    database_url: str = "sqlite:///./playlist_builder.db"
    
    # Application URLs
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    
    # Security Configuration
    session_secret: str = "change-me-in-production"
    token_encryption_key: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
