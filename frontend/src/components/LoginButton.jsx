import React from 'react';
import { useUser } from '../contexts/UserContext';

const LoginButton = () => {
  const { login } = useUser();

  return (
    <div className="card" style={{ textAlign: 'center', maxWidth: '500px', margin: '0 auto' }}>
      <h2>Welcome to Spotify Gemini Playlist Builder</h2>
      <p style={{ marginBottom: '30px', color: '#b3b3b3' }}>
        Connect your Spotify account to start creating AI-powered playlists
      </p>
      <button onClick={login} style={{ fontSize: '1.1em', padding: '15px 40px' }}>
        Login with Spotify
      </button>
    </div>
  );
};

export default LoginButton;
