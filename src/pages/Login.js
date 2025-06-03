// Import dependencies
import { useState, useEffect, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api'; // Axios instance
import styles from './Login.module.css'; // Styling
import UserContext from '../UserContext'; // Global context

// Login page component
export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { setUser } = useContext(UserContext); // Global user setter
  const navigate = useNavigate();

  // If token exists, try to auto-login
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api.get('/me')
        .then(res => {
          setUser(res.data); // Set global user
          navigate('/profile'); // Redirect
        })
        .catch(() => {
          localStorage.removeItem('token'); // Remove invalid token
        });
    }
  }, [navigate, setUser]);

  // Handle login
  const handleLogin = async () => {
    try {
      const res = await api.post('/login', { email, password });

      localStorage.setItem('token', res.data.token); // Save token
      setUser(res.data.user); // Set global user info
      navigate('/profile'); // Go to profile
    } catch (err) {
      console.error('Login failed:', err);
      setError('Invalid email or password');
    }
  };

  return (
    <div className={styles.container}>
      <h2>Login</h2>
      {error && <p className={styles.error}>{error}</p>}

      <input
        className={styles.input}
        type="email"
        value={email}
        onChange={e => setEmail(e.target.value)}
        placeholder="Email"
      />
      <input
        className={styles.input}
        type="password"
        value={password}
        onChange={e => setPassword(e.target.value)}
        placeholder="Password"
      />
      <button className={styles.button} onClick={handleLogin}>
        Log In
      </button>

      <p>Don't have an account? <Link to="/register">Register here</Link></p>
    </div>
  );
}
