import React from 'react';
import { useUser } from '../contexts/UserContext';

const UserProfile = () => {
  const { user, logout } = useUser();

  if (!user) return null;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
      <div>
        <div style={{ fontWeight: 600, color: '#1db954' }}>
          {user.display_name || user.spotify_user_id}
        </div>
        {user.email && (
          <div style={{ fontSize: '0.9em', color: '#b3b3b3' }}>{user.email}</div>
        )}
      </div>
      <button onClick={logout} className="secondary" style={{ padding: '8px 16px', fontSize: '0.9em' }}>
        Logout
      </button>
    </div>
  );
};

export default UserProfile;
