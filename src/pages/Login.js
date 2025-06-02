// Import dependencies
import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api'; // Axios instance for backend requests
import styles from './Login.module.css'; // CSS module for styling

// Login page component
export default function Login() {
  // Form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate(); // Navigation hook

  // Redirect to profile if already logged in
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      navigate('/profile');
    }
  }, [navigate]);

  // Handle login button click
  const handleLogin = async () => {
    try {
      const res = await api.post('/login', { email, password }); // Send login request
      localStorage.setItem('token', res.data.token); // Save token
      navigate('/profile'); // Redirect on success
    } catch (err) {
      setError('Invalid email or password'); // Show error
    }
  };

  // Render login form
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
      <button className={styles.button} onClick={handleLogin}>Log In</button>
      <p>Don’t have an account? <Link to="/register">Register here</Link></p>
    </div>
  );
}
