import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const UserContext = createContext(null);

export const UserProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const status = await authAPI.getStatus();
      if (status.authenticated && status.user) {
        setUser(status.user);
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error('Failed to check auth status:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = () => {
    authAPI.login();
  };

  const logout = async () => {
    try {
      await authAPI.logout();
      setUser(null);
    } catch (error) {
      console.error('Failed to logout:', error);
    }
  };

  const updateUser = (userData) => {
    setUser(userData);
  };

  return (
    <UserContext.Provider value={{ user, loading, login, logout, updateUser, checkAuthStatus }}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};
