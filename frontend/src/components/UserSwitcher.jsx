import React, { useState, useEffect } from 'react';
import { usersAPI } from '../services/api';
import { useUser } from '../contexts/UserContext';

const UserSwitcher = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user: currentUser, updateUser, checkAuthStatus } = useUser();

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
      const response = await usersAPI.switch(userId);
      updateUser(response.user);
    } catch (error) {
      console.error('Failed to switch user:', error);
      alert('Failed to switch user. Please try again.');
    }
  };

  if (loading) {
    return <div>Loading users...</div>;
  }

  if (users.length <= 1) {
    return null;
  }

  return (
    <div>
      <select
        value={currentUser?.id || ''}
        onChange={(e) => switchUser(parseInt(e.target.value))}
        style={{ padding: '8px 12px', fontSize: '0.9em' }}
      >
        {users.map((user) => (
          <option key={user.id} value={user.id}>
            {user.display_name || user.spotify_user_id}
          </option>
        ))}
      </select>
    </div>
  );
};

export default UserSwitcher;
