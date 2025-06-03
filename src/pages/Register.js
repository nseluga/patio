// Import dependencies
import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api'; // Axios instance for API requests
import styles from './Login.module.css'; // Shared CSS module for form styling

// Register page component
export default function Register() {
  // Form state
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // Redirect if already logged in
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      navigate('/profile');
    }
  }, [navigate]);

  // Handle register button click
  const handleRegister = async () => {
    console.log("🔁 Submitting register form...", { username, email, password });
    try {
      await api.post('/register', { username, email, password }); // Send data to backend
      navigate('/login'); // ✅ Go to login (not profile)
    } catch (err) {
      console.error("❌ Registration failed:", err);
      setError("Registration failed. Try again."); // Show error message
    }
  };

  // Render registration form
  return (
    <div className={styles.container}>
      <h2>Register</h2>

      {/* Error message */}
      {error && <p className={styles.error}>{error}</p>}

      {/* Username input */}
      <input
        className={styles.input}
        placeholder="Username"
        value={username}
        onChange={e => setUsername(e.target.value)}
      /><br />

      {/* Email input */}
      <input
        className={styles.input}
        type="email"
        placeholder="Email"
        value={email}
        onChange={e => setEmail(e.target.value)}
      /><br />

      {/* Password input */}
      <input
        className={styles.input}
        type="password"
        placeholder="Password"
        value={password}
        onChange={e => setPassword(e.target.value)}
      /><br />

      {/* Register button */}
      <button
        type="button"
        className={styles.button}
        onClick={handleRegister}
      >
        Register
      </button>

      {/* Link to login */}
      <p>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
