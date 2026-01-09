import React, { useState, useEffect } from 'react';
import { usersAPI } from '../services/api';
import { useUser } from '../contexts/UserContext';

const UserList = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user: currentUser } = useUser();

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const userList = await usersAPI.list();
      setUsers(userList);
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setLoading(false);
    }
  };

  const switchUser = async (userId) => {
    try {
      await usersAPI.switch(userId);
      window.location.reload(); // Reload to update context
    } catch (error) {
      console.error('Failed to switch user:', error);
      alert('Failed to switch user. Please try again.');
    }
  };

  const deleteUser = async (userId) => {
    if (!confirm('Are you sure you want to delete this user?')) {
      return;
    }

    try {
      await usersAPI.delete(userId);
      loadUsers(); // Reload list
      if (currentUser?.id === userId) {
        // If deleted user was current user, logout
        window.location.href = '/';
      }
    } catch (error) {
      console.error('Failed to delete user:', error);
      alert('Failed to delete user. Please try again.');
    }
  };

  if (loading) {
    return <div className="loading">Loading users...</div>;
  }

  return (
    <div>
      <h2>Registered Users</h2>
      <div className="user-list">
        {users.map((user) => (
          <div
            key={user.id}
            className={`user-card ${currentUser?.id === user.id ? 'active' : ''}`}
          >
            <h3>{user.display_name || user.spotify_user_id}</h3>
            {user.email && <p style={{ color: '#b3b3b3', marginBottom: '10px' }}>{user.email}</p>}
            <div style={{ fontSize: '0.9em', color: '#666', marginBottom: '15px' }}>
              Spotify ID: {user.spotify_user_id}
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              {currentUser?.id !== user.id && (
                <button onClick={() => switchUser(user.id)} className="secondary" style={{ flex: 1 }}>
                  Switch
                </button>
              )}
              {currentUser?.id === user.id && (
                <span style={{ flex: 1, textAlign: 'center', color: '#1db954', fontWeight: 600 }}>
                  Current User
                </span>
              )}
              <button
                onClick={() => deleteUser(user.id)}
                className="danger"
                style={{ flex: 1 }}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
      {users.length === 0 && (
        <div className="info">No users registered yet. Login with Spotify to create your first user.</div>
      )}
    </div>
  );
};

export default UserList;
