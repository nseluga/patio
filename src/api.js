// Import axios for HTTP requests
import axios from 'axios';

// Create a reusable Axios instance with base URL
const api = axios.create({
  baseURL: 'http://localhost:5000', // Flask backend base URL
});

// Add an interceptor to include the auth token (if present)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = token; // Add token to request headers
  }
  return config;
});

// Export the configured Axios instance
export default api;
