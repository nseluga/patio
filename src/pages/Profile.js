import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export default function Profile() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login'); // redirect if not logged in
      return;
    }

    // fetch user info
    api.get('/me')
      .then(res => {
        setUser(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Token invalid or expired');
        localStorage.removeItem('token');
        navigate('/login');
      });
  }, [navigate]);

  if (loading) return <p>Loading profile...</p>;

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Welcome, {user.username}!</h2>
      <p>Email: {user.email}</p>
      <p>Caps: {user.caps_balance}</p>
    </div>
  );
}
