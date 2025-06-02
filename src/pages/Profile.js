// Import dependencies
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api'; // Axios instance for making API requests

// Profile page component
export default function Profile() {
  const [user, setUser] = useState(null); // Store user data
  const [loading, setLoading] = useState(true); // Loading state
  const navigate = useNavigate(); // React Router navigation

  // Run once on mount to fetch user info
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login'); // Redirect if no token
      return;
    }

    // Attempt to fetch user data
    api.get('/me')
      .then(res => {
        setUser(res.data); // Save user info
        setLoading(false); // Stop loading
      })
      .catch(err => {
        console.error('Token invalid or expired');
        localStorage.removeItem('token'); // Remove bad token
        navigate('/login'); // Redirect to login
      });
  }, [navigate]);

  // Show loading message until data is ready
  if (loading) return <p>Loading profile...</p>;

  // Render user profile info
  return (
    <div style={{ padding: '2rem' }}>
      <h2>Welcome, {user.username}!</h2>
      <p>Email: {user.email}</p>
      <p>Caps: {user.caps_balance}</p>
    </div>
  );
}
