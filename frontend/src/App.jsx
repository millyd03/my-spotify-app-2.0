import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { UserProvider, useUser } from './contexts/UserContext';
import LoginButton from './components/LoginButton';
import PlaylistBuilder from './components/PlaylistBuilder';
import UserSwitcher from './components/UserSwitcher';
import UserList from './components/UserList';
import RulesetManager from './components/RulesetManager';
import UserProfile from './components/UserProfile';
import './App.css';

const AppContent = () => {
  const { user, loading } = useUser();

  if (loading) {
    return (
      <div className="container">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container">
        <header>
          <h1>Spotify Gemini Playlist Builder</h1>
          <p>Create custom playlists using AI based on your guidelines</p>
        </header>
        <LoginButton />
      </div>
    );
  }

  return (
    <Router>
      <div className="container">
        <header>
          <h1>Spotify Gemini Playlist Builder</h1>
          <nav>
            <ul>
              <li><a href="/">Home</a></li>
              <li><a href="/users">Users</a></li>
              <li><a href="/rulesets">Rulesets</a></li>
            </ul>
          </nav>
        </header>
        
        <div className="user-info">
          <UserProfile />
          <UserSwitcher />
        </div>

        <Routes>
          <Route path="/" element={<PlaylistBuilder />} />
          <Route path="/users" element={<UserList />} />
          <Route path="/rulesets" element={<RulesetManager />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </Router>
  );
};

const App = () => {
  return (
    <UserProvider>
      <AppContent />
    </UserProvider>
  );
};

export default App;
