import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Important for session cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth API
export const authAPI = {
  login: () => {
    window.location.href = `${API_BASE_URL}/auth/login`;
  },
  
  logout: async () => {
    const response = await api.post('/auth/logout');
    return response.data;
  },
  
  getStatus: async () => {
    const response = await api.get('/auth/status');
    return response.data;
  },
};

// Users API
export const usersAPI = {
  list: async () => {
    const response = await api.get('/api/users');
    return response.data;
  },
  
  switch: async (userId) => {
    const response = await api.post('/api/users/switch', { user_id: userId });
    return response.data;
  },
  
  get: async (userId) => {
    const response = await api.get(`/api/users/${userId}`);
    return response.data;
  },
  
  delete: async (userId) => {
    const response = await api.delete(`/api/users/${userId}`);
    return response.data;
  },
};

// Playlists API
export const playlistsAPI = {
  create: async (guidelines, musicOnly = false) => {
    const response = await api.post('/api/playlists/create', {
      guidelines,
      music_only: musicOnly,
    });
    return response.data;
  },
};

// User Data API
export const userDataAPI = {
  getArtists: async () => {
    const response = await api.get('/api/user/artists');
    return response.data;
  },
  
  getPodcasts: async () => {
    const response = await api.get('/api/user/podcasts');
    return response.data;
  },
};

// Rulesets API
export const rulesetsAPI = {
  list: async (activeOnly = false) => {
    const response = await api.get('/api/rulesets', {
      params: { active_only: activeOnly },
    });
    return response.data;
  },
  
  get: async (rulesetId) => {
    const response = await api.get(`/api/rulesets/${rulesetId}`);
    return response.data;
  },
  
  create: async (rulesetData) => {
    const response = await api.post('/api/rulesets', rulesetData);
    return response.data;
  },
  
  update: async (rulesetId, rulesetData) => {
    const response = await api.put(`/api/rulesets/${rulesetId}`, rulesetData);
    return response.data;
  },
  
  delete: async (rulesetId) => {
    const response = await api.delete(`/api/rulesets/${rulesetId}`);
    return response.data;
  },
  
  match: async (guidelines) => {
    const response = await api.post('/api/rulesets/match', { guidelines });
    return response.data;
  },
};

export default api;
