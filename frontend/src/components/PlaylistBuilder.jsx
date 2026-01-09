import React, { useState, useEffect } from 'react';
import { playlistsAPI, userDataAPI, rulesetsAPI } from '../services/api';
import { useUser } from '../contexts/UserContext';

const PlaylistBuilder = () => {
  const [guidelines, setGuidelines] = useState('');
  const [musicOnly, setMusicOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [matchedRulesets, setMatchedRulesets] = useState([]);
  const [artists, setArtists] = useState([]);
  const [podcasts, setPodcasts] = useState([]);
  const [checkingRulesets, setCheckingRulesets] = useState(false);
  const { user } = useUser();

  useEffect(() => {
    loadUserData();
  }, [user]);

  useEffect(() => {
    // Check for matched rulesets when guidelines change
    if (guidelines.trim()) {
      checkRulesets();
    } else {
      setMatchedRulesets([]);
    }
  }, [guidelines]);

  const loadUserData = async () => {
    try {
      const [artistsData, podcastsData] = await Promise.all([
        userDataAPI.getArtists().catch(() => ({ artists: [] })),
        userDataAPI.getPodcasts().catch(() => ({ podcasts: [] })),
      ]);
      setArtists(artistsData.artists || []);
      setPodcasts(podcastsData.podcasts || []);
    } catch (error) {
      console.error('Failed to load user data:', error);
    }
  };

  const checkRulesets = async () => {
    setCheckingRulesets(true);
    try {
      const matchResult = await rulesetsAPI.match(guidelines);
      setMatchedRulesets(matchResult.matched_rulesets || []);
    } catch (error) {
      console.error('Failed to check rulesets:', error);
    } finally {
      setCheckingRulesets(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!guidelines.trim()) {
      setError('Please enter playlist guidelines');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const playlist = await playlistsAPI.create(guidelines, musicOnly);
      setResult(playlist);
      setGuidelines(''); // Clear form
    } catch (error) {
      console.error('Failed to create playlist:', error);
      setError(error.response?.data?.detail || 'Failed to create playlist. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Create New Playlist</h2>
      
      {user && (
        <div className="info" style={{ marginBottom: '20px' }}>
          Creating playlist for: <strong>{user.display_name || user.spotify_user_id}</strong>
        </div>
      )}

      <form onSubmit={handleSubmit} className="card">
        <div className="form-group">
          <label htmlFor="guidelines">
            Playlist Guidelines <span style={{ color: '#666' }}>(e.g., "Create a throwback playlist with 90s hits")</span>
          </label>
          <textarea
            id="guidelines"
            value={guidelines}
            onChange={(e) => setGuidelines(e.target.value)}
            placeholder="Describe the kind of playlist you want. Include style, mood, genre, era, or any specific requirements..."
            required
          />
        </div>

        {matchedRulesets.length > 0 && (
          <div className="info" style={{ marginBottom: '20px' }}>
            <strong>Matched Rulesets:</strong>
            {matchedRulesets.map((ruleset) => (
              <div key={ruleset.name} className="ruleset-tag">
                {ruleset.name}
                {ruleset.description && ` - ${ruleset.description}`}
              </div>
            ))}
          </div>
        )}

        <div className="form-group">
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="musicOnly"
              checked={musicOnly}
              onChange={(e) => setMusicOnly(e.target.checked)}
            />
            <label htmlFor="musicOnly" style={{ marginBottom: 0 }}>
              Music only (exclude podcasts)
            </label>
          </div>
        </div>

        {error && <div className="error">{error}</div>}

        <button type="submit" disabled={loading || !guidelines.trim()}>
          {loading ? 'Creating Playlist...' : 'Create Playlist'}
        </button>
      </form>

      {result && (
        <div className="card success">
          <h3>Playlist Created Successfully!</h3>
          <p><strong>Name:</strong> {result.name}</p>
          {result.rulesets_applied && result.rulesets_applied.length > 0 && (
            <p>
              <strong>Rulesets Applied:</strong>{' '}
              {result.rulesets_applied.map((name) => (
                <span key={name} className="ruleset-tag">{name}</span>
              ))}
            </p>
          )}
          <p><strong>Tracks Added:</strong> {result.tracks_count}</p>
          <a
            href={result.spotify_url}
            target="_blank"
            rel="noopener noreferrer"
            className="playlist-link"
          >
            Open in Spotify
          </a>
        </div>
      )}

      {artists.length > 0 && (
        <div className="card">
          <h3>Your Top Artists</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            {artists.slice(0, 20).map((artist) => (
              <span key={artist.id} className="keyword-tag">{artist.name}</span>
            ))}
          </div>
        </div>
      )}

      {podcasts.length > 0 && !musicOnly && (
        <div className="card">
          <h3>Your Saved Podcasts</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            {podcasts.slice(0, 15).map((podcast) => (
              <span key={podcast.id} className="keyword-tag">{podcast.name}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PlaylistBuilder;
