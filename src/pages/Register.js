import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';
import styles from './Login.module.css';

export default function Register() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // ✅ Redirect if user is already logged in
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      navigate('/profile');
    }
  }, [navigate]);

  const handleRegister = async () => {
    try {
      await api.post('/register', { username, email, password });
      navigate('/login');
    } catch (err) {
      setError('Registration failed. Try a different email or username.');
    }
  };

  return (
    <div className={styles.container}>
      <h2>Register</h2>
      {error && <p className={styles.error}>{error}</p>}
      <input
        className={styles.input}
        placeholder="Username"
        value={username}
        onChange={e => setUsername(e.target.value)}
      /><br />
      <input
        className={styles.input}
        type="email"
        placeholder="Email"
        value={email}
        onChange={e => setEmail(e.target.value)}
      /><br />
      <input
        className={styles.input}
        type="password"
        placeholder="Password"
        value={password}
        onChange={e => setPassword(e.target.value)}
      /><br />
      <button className={styles.button} onClick={handleRegister}>Register</button>
      <p>Already have an account? <Link to="/login">Log in</Link></p>
    </div>
  );
}
