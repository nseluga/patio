import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const api = axios.create({
  baseURL: 'https://patio-backend-y4ft.onrender.com',
});

api.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Registered by App.js once the UserContext provider mounts. Lets a 401 from
// anywhere in the app (not just the cold-boot bootstrap) clear the dead
// session and drop the user back to the login screen instead of leaving
// screens stuck showing a silently-failing session.
let onUnauthorized = null;

export function setOnUnauthorized(handler) {
  onUnauthorized = handler;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response && error.response.status === 401) {
      await SecureStore.deleteItemAsync('token');
      await SecureStore.deleteItemAsync('playerId');
      if (onUnauthorized) {
        onUnauthorized();
      }
    }
    return Promise.reject(error);
  }
);

export default api;
