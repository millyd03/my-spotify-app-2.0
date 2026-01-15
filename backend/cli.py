#!/usr/bin/env python3
"""Interactive CLI for Spotify Agent Service."""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlencode, parse_qs, urlparse
from datetime import datetime, timedelta
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import base64

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from database import AsyncSessionLocal, init_db
from users.service import get_user_by_spotify_id, create_user, update_user_tokens, get_user_by_id
from utils.encryption import encrypt_token
from spotify.api_client import SpotifyAPIClient
from gemini.playlist_generator import generate_playlist
from gemini.chat_handler import get_chat_handler
from models import ChatMessage
from rulesets.service import get_all_rulesets


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""
    
    def do_GET(self):
        """Handle OAuth callback."""
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        
        code = query_params.get('code', [None])[0]
        error = query_params.get('error', [None])[0]
        
        self.server.auth_code = code
        self.server.auth_error = error
        
        if error:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Authentication failed. Please close this window.</h1></body></html>')
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Authentication successful! You can close this window and return to the CLI.</h1></body></html>')
    
    def log_message(self, format, *args):
        """Suppress log messages."""
        pass


async def authenticate_user() -> Optional[int]:
    """Perform OAuth flow and return user_id."""
    print("\n🔐 Starting Spotify authentication...")
    print("This will open your browser for authorization.\n")
    
    # Start local HTTP server for callback
    server_port = 8765
    httpd = HTTPServer(('localhost', server_port), OAuthCallbackHandler)
    httpd.auth_code = None
    httpd.auth_error = None
    
    def run_server():
        httpd.handle_request()
        httpd.server_close()
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Build authorization URL
    redirect_uri = f"http://localhost:{server_port}/callback"
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "user-read-private user-read-email user-top-read user-library-read playlist-modify-public playlist-modify-private user-read-playback-state",
    }
    auth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    
    # Open browser
    print(f"Opening browser: {auth_url}")
    webbrowser.open(auth_url)
    
    # Wait for callback
    print("Waiting for authentication...")
    server_thread.join(timeout=120)
    
    if httpd.auth_error:
        print(f"❌ Authentication failed: {httpd.auth_error}")
        return None
    
    if not httpd.auth_code:
        print("❌ No authorization code received. Authentication may have timed out.")
        return None
    
    # Exchange code for tokens
    token_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    ).decode()
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": httpd.auth_code,
                "redirect_uri": redirect_uri,
            },
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        
        if token_response.status_code != 200:
            print(f"❌ Failed to exchange token: {token_response.text}")
            return None
        
        token_data = token_response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        expires_in = token_data.get("expires_in", 3600)
        
        # Get user info from Spotify
        user_response = await client.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if user_response.status_code != 200:
            print(f"❌ Failed to get user info: {user_response.text}")
            return None
        
        user_data = user_response.json()
        spotify_user_id = user_data["id"]
        display_name = user_data.get("display_name")
        email = user_data.get("email")
    
    # Initialize database
    await init_db()
    
    # Store user in database
    async with AsyncSessionLocal() as db:
        encrypted_access_token = encrypt_token(access_token)
        encrypted_refresh_token = encrypt_token(refresh_token)
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        existing_user = await get_user_by_spotify_id(db, spotify_user_id)
        
        if existing_user:
            user = await update_user_tokens(
                db,
                existing_user.id,
                encrypted_access_token,
                encrypted_refresh_token,
                token_expires_at
            )
            user_id = existing_user.id
        else:
            user = await create_user(
                db,
                spotify_user_id,
                display_name,
                email,
                encrypted_access_token,
                encrypted_refresh_token,
                token_expires_at
            )
            user_id = user.id
        
        await db.commit()
    
    print(f"✅ Authenticated as: {display_name or spotify_user_id}")
    return user_id


async def run_cli():
    """Run the interactive CLI."""
    print("=" * 60)
    print("🎵 Spotify Agent CLI")
    print("=" * 60)
    print()
    
    # Authenticate user
    user_id = await authenticate_user()
    if not user_id:
        print("❌ Authentication failed. Exiting.")
        return
    
    print("\n" + "=" * 60)
    print("💬 Chat Mode - Type your messages to interact with the agent")
    print("Commands: /help, /clear, /rulesets, /exit")
    print("=" * 60 + "\n")
    
    # Initialize conversation history
    conversation_history: List[ChatMessage] = []
    chat_handler = get_chat_handler()
    
    # Main chat loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                if user_input == "/exit":
                    print("\n👋 Goodbye!")
                    break
                elif user_input == "/help":
                    print("\n📋 Available commands:")
                    print("  /help      - Show this help message")
                    print("  /clear     - Clear conversation history")
                    print("  /rulesets  - List all available rulesets")
                    print("  /exit      - Exit the CLI")
                    print("\nYou can also just type messages to:")
                    print("  - Generate playlists")
                    print("  - Create, edit, or delete rulesets")
                    print("  - Ask questions about your music\n")
                    continue
                elif user_input == "/clear":
                    conversation_history.clear()
                    print("✅ Conversation history cleared.\n")
                    continue
                elif user_input == "/rulesets":
                    async with AsyncSessionLocal() as db:
                        rulesets = await get_all_rulesets(db, active_only=False)
                        if rulesets:
                            print("\n📋 Available Rulesets:")
                            for r in rulesets:
                                status = "✓" if r.is_active else "✗"
                                print(f"  {status} {r.name}: {r.description or 'No description'}")
                                print(f"    Keywords: {', '.join(r.keywords)}")
                                if r.criteria:
                                    print(f"    Criteria: {json.dumps(r.criteria, indent=6)}")
                                print()
                        else:
                            print("\n📋 No rulesets available.\n")
                    continue
                else:
                    print(f"❌ Unknown command: {user_input}. Type /help for available commands.\n")
                    continue
            
            # Process chat message
            print("🤔 Thinking...")
            
            async with AsyncSessionLocal() as db:
                # Get Spotify client
                spotify_client = SpotifyAPIClient(user_id, db)
                
                # Process message
                response_text, action_type, action_data = await chat_handler.process_message(
                    user_message=user_input,
                    conversation_history=conversation_history,
                    db=db,
                    user_id=user_id,
                    spotify_client=spotify_client,
                    playlist_generator=generate_playlist
                )
            
            # Add user message to history
            user_message = ChatMessage(
                role="user",
                content=user_input,
                timestamp=datetime.utcnow()
            )
            conversation_history.append(user_message)
            
            # Add assistant response to history
            assistant_message = ChatMessage(
                role="assistant",
                content=response_text,
                timestamp=datetime.utcnow()
            )
            conversation_history.append(assistant_message)
            
            # Print response
            print(f"\n🤖 Agent: {response_text}\n")
            
            # Print action data if present
            if action_type == "playlist_created" and action_data:
                print(f"✅ Playlist created: {action_data.get('name')}")
                print(f"   Spotify URL: {action_data.get('spotify_url')}")
                print(f"   Tracks: {action_data.get('tracks_count')}")
                if action_data.get('rulesets_applied'):
                    print(f"   Rulesets applied: {', '.join(action_data['rulesets_applied'])}")
                print()
            elif action_type == "ruleset_created" and action_data:
                print(f"✅ Ruleset created: {action_data.get('name')}")
                print()
            elif action_type == "ruleset_updated" and action_data:
                print(f"✅ Ruleset updated: {action_data.get('name')}")
                print()
            elif action_type == "ruleset_deleted" and action_data:
                print(f"✅ Ruleset deleted (ID: {action_data.get('ruleset_id')})")
                print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_cli())
