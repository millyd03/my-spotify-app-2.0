import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from gemini.playlist_generator import generate_playlist


@pytest.mark.asyncio
async def test_daily_drive_playlist_deletion_logic():
    """Test that the playlist generator correctly handles daily drive deletion logic."""
    # Mock all the external dependencies
    with patch('spotify.api_client.SpotifyAPIClient') as mock_spotify_class, \
         patch('gemini.playlist_generator.datetime') as mock_datetime:

        # Mock datetime to return Monday
        mock_datetime.now.return_value.strftime.return_value = "Monday"

        # Setup mocks
        mock_spotify_client = MagicMock()
        mock_spotify_class.return_value = mock_spotify_client

        # Setup mocks
        mock_spotify_client = MagicMock()
        mock_spotify_class.return_value = mock_spotify_client

        # Mock followed artists
        mock_spotify_client.get_followed_artists = AsyncMock(return_value=[
            {"id": "artist1", "name": "Test Artist 1"},
            {"id": "artist2", "name": "Test Artist 2"}
        ])

        # Mock artist top tracks
        mock_spotify_client.get_artist_top_tracks = AsyncMock(return_value=[
            {"id": "track1", "name": "Song 1", "explicit": False},
            {"id": "track2", "name": "Song 2", "explicit": False}
        ])

        # Mock other required methods
        mock_spotify_client.get_user_saved_tracks = AsyncMock(return_value=[])
        mock_spotify_client.get_saved_podcasts = AsyncMock(return_value=[])

        # Mock ruleset filtering (no filtering needed for this test)
        with patch('gemini.playlist_generator.apply_ruleset_filters', return_value=[
            {"id": "track1", "name": "Song 1", "explicit": False}
        ]):

            # Mock Spotify API methods
            mock_spotify_client.get_user_playlists = AsyncMock(return_value=[
                {"id": "existing_playlist", "name": "Daily Drive - 2024-01-15", "description": "Daily drive playlist"}
            ])
            mock_spotify_client.delete_playlist = AsyncMock()
            mock_spotify_client.create_playlist = AsyncMock(return_value={"id": "new_playlist"})
            mock_spotify_client.add_items_to_playlist = AsyncMock()
            mock_spotify_client.get_track = AsyncMock(return_value={"id": "track1", "name": "Song 1", "explicit": False})

            # First call - no existing daily drive playlist
            mock_spotify_client.get_user_playlists.side_effect = [
                [],  # First check - no playlists
                [{"id": "existing_playlist", "name": "Daily Drive - Monday"}]  # Second check - existing playlist
            ]

            mock_spotify_client.create_playlist.side_effect = [
                {"id": "playlist_1", "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist_1"}},
                {"id": "playlist_2", "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist_2"}}
            ]

            # Test first daily drive playlist creation
            mock_db = MagicMock()
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()
            result1 = await generate_playlist(
                db=mock_db,
                user_id=1,
                num_songs=20,
                is_daily_drive=True,
                allow_explicit=False,
                ruleset=None,
                guidelines="",
                music_only=True,
                timezone=None,
                spotify_client=mock_spotify_client
            )

            # Verify first playlist was created
            assert result1.playlist_id == "playlist_1"
            assert "Daily Drive" in result1.name
            mock_spotify_client.delete_playlist.assert_not_called()  # No existing playlist to delete

            # Reset delete_playlist call count
            mock_spotify_client.delete_playlist.reset_mock()

            # Test second daily drive playlist creation (should delete first)
            result2 = await generate_playlist(
                db=mock_db,
                user_id=1,
                num_songs=20,
                is_daily_drive=True,
                allow_explicit=False,
                ruleset=None,
                guidelines="",
                music_only=True,
                timezone=None,
                spotify_client=mock_spotify_client
            )

            # Verify second playlist was created
            assert result2.playlist_id == "playlist_2"
            assert "Daily Drive" in result2.name

            # Verify first playlist was deleted
            mock_spotify_client.delete_playlist.assert_called_once_with("existing_playlist")


@pytest.mark.asyncio
async def test_artist_tiers_playlist_generation():
    """Test that playlist generation respects artist tiers distribution."""
    # Mock all the external dependencies
    with patch('spotify.api_client.SpotifyAPIClient') as mock_spotify_class, \
         patch('gemini.playlist_generator.datetime') as mock_datetime:

        # Setup mocks
        mock_spotify_client = MagicMock()
        mock_spotify_class.return_value = mock_spotify_client

        # Mock followed artists
        mock_spotify_client.get_followed_artists = AsyncMock(return_value=[
            {"id": "6qJAs9BStSfy9v3Rgnv9A3", "name": "blink-182"},
            {"id": "3pAtv7T99996pY9u3v96go", "name": "Relient K"},
            {"id": "6YvT1vMvWv8NlXhS9UqE9r", "name": "Beth Vandal"}
        ])

        # Mock artist details with follower counts for tiers
        def mock_get_artist(artist_id):
            if artist_id == "6qJAs9BStSfy9v3Rgnv9A3":  # blink-182
                return {"followers": {"total": 8000000}}  # TIER_5
            elif artist_id == "3pAtv7T99996pY9u3v96go":  # Relient K
                return {"followers": {"total": 500000}}   # TIER_2
            elif artist_id == "6YvT1vMvWv8NlXhS9UqE9r":  # Beth Vandal
                return {"followers": {"total": 10000}}    # TIER_1
            return {"followers": {"total": 0}}

        mock_spotify_client.get_artist = AsyncMock(side_effect=mock_get_artist)

        # Mock top tracks for each artist (10 tracks each)
        blink_tracks = [{"id": f"blink_track_{i}", "name": f"Blink Track {i}", "explicit": False} for i in range(10)]
        relient_tracks = [{"id": f"relient_track_{i}", "name": f"Relient Track {i}", "explicit": False} for i in range(10)]
        beth_tracks = [{"id": f"beth_track_{i}", "name": f"Beth Track {i}", "explicit": False} for i in range(10)]

        def mock_get_artist_top_tracks(artist_id):
            if artist_id == "6qJAs9BStSfy9v3Rgnv9A3":
                return blink_tracks
            elif artist_id == "3pAtv7T99996pY9u3v96go":
                return relient_tracks
            elif artist_id == "6YvT1vMvWv8NlXhS9UqE9r":
                return beth_tracks
            return []

        mock_spotify_client.get_artist_top_tracks = AsyncMock(side_effect=mock_get_artist_top_tracks)

        # Mock other required methods
        mock_spotify_client.get_user_saved_tracks = AsyncMock(return_value=[])
        mock_spotify_client.get_saved_podcasts = AsyncMock(return_value=[])
        mock_spotify_client.get_user_playlists = AsyncMock(return_value=[])
        mock_spotify_client.create_playlist = AsyncMock(return_value={"id": "test_playlist", "external_urls": {"spotify": "https://open.spotify.com/playlist/test_playlist"}})
        mock_spotify_client.add_items_to_playlist = AsyncMock()
        mock_spotify_client.delete_playlist = AsyncMock()

        # Test playlist generation
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        result = await generate_playlist(
            db=mock_db,
            user_id=1,
            num_songs=10,
            is_daily_drive=False,
            allow_explicit=False,
            ruleset=None,
            guidelines="Test Tier Playlist",
            music_only=True,
            timezone=None,
            spotify_client=mock_spotify_client
        )

        # Verify playlist was created
        assert result.playlist_id == "test_playlist"
        assert result.tracks_count == 8  # Tier limits: 5 (blink) + 2 (relient) + 1 (beth) = 8

        # Verify add_items_to_playlist was called
        mock_spotify_client.add_items_to_playlist.assert_called()

        # Get the tracks added
        call_args = mock_spotify_client.add_items_to_playlist.call_args_list
        added_items = []
        for call in call_args:
            added_items.extend(call[0][1])  # Second arg is the items list

        # Extract track IDs
        track_ids = [item.split(":")[-1] for item in added_items if item.startswith("spotify:track:")]

        # Count tracks from each artist
        blink_count = sum(1 for tid in track_ids if tid.startswith("blink_track_"))
        relient_count = sum(1 for tid in track_ids if tid.startswith("relient_track_"))
        beth_count = sum(1 for tid in track_ids if tid.startswith("beth_track_"))

        # Verify tier distribution
        assert blink_count <= 5, f"Expected no more than 5 blink-182 tracks (tier 5), got {blink_count}"
        assert relient_count <= 2, f"Expected no more than 2 Relient K tracks (tier 2), got {relient_count}"
        assert beth_count <= 1, f"Expected no more than 1 Beth Vandal track (tier 1), got {beth_count}"
        assert blink_count + relient_count + beth_count == 8

        # Delete the playlist when test is complete
        await mock_spotify_client.delete_playlist("test_playlist")