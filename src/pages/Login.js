// Import dependencies
import { useState, useEffect, useContext } from "react";
import { useNavigate, Navigate, Link } from "react-router-dom";
import api from "../api"; // Axios instance
import styles from "./Login.module.css"; // Styling
import UserContext from "../UserContext"; // Global context


// Login page component
export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { user, setUser } = useContext(UserContext); // Global user setter
  const navigate = useNavigate();

  // If token exists, try to auto-login
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token && !user) {
      api
        .get("/me")
        .then((res) => {
          setUser(res.data);
          // Only navigate if still on login page
          if (window.location.pathname === "/login") {
            navigate("/pvp");
          }
        })
        .catch(() => {
          localStorage.removeItem("token");
        });
    }
  }, [navigate, user, setUser]);

  // Redirect only if you're on login and already logged in
  if (user && window.location.pathname === "/login") {
    return <Navigate to="/pvp" />;
  }

  // Handle login
  const handleLogin = async () => {
  try {
    const res = await api.post('/login', { email, password });

    // ✅ Store the token for future auth
    localStorage.setItem('token', res.data.token);
    localStorage.setItem("playerId", res.data.user.id.toString()); 
    localStorage.setItem("username", res.data.user.username);

    // ✅ Set user globally for Profile page
    setUser({
      ...res.data.user,
      playerId: res.data.user.id, // 👈 explicitly add playerId
      token: res.data.token,
    });

    // ✅ Redirect to /profile
    window.location.href = "/pvp";
  } catch (err) {
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
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
      />
      <input
        className={styles.input}
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
      />
      <button className={styles.button} onClick={handleLogin}>
        Log In
      </button>

      <p>
        Don't have an account? <Link to="/register">Register here</Link>
      </p>
    </div>
  );
}
