"""Session management utilities."""
from fastapi import Request
from typing import Optional
import json


def get_active_user_id(request: Request) -> Optional[int]:
    """Get the active user ID from session."""
    session = request.session
    return session.get("active_user_id")


def set_active_user_id(request: Request, user_id: int):
    """Set the active user ID in session."""
    request.session["active_user_id"] = user_id


def clear_session(request: Request):
    """Clear the session."""
    request.session.clear()
