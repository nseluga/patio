import { useState, useEffect, useContext } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import api from "../api";
import UserContext from "../UserContext";
import styles from "./Login.module.css"; // or "./Login.css"
import { Link } from "react-router-dom"; // ✅ Fixes 'Link is not defined'

// Login page component
export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { user, setUser } = useContext(UserContext);
  const navigate = useNavigate();

  // Try auto-login if token exists but no user in context
  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token || user) return;

    const fetchProfile = async () => {
      try {
        const res = await api.get("/me", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        const fullUser = {
          ...res.data,
          playerId: res.data.id, // standardize key for frontend
          token,
        };

        setUser(fullUser);
        navigate("/pvp");
      } catch (err) {
        console.error("❌ Failed to fetch /me during auto-login:", err);
        localStorage.removeItem("token");
        setUser(null);
      }
    };

    fetchProfile();
  }, [user, setUser, navigate]);

  // Handle login form submission
  const handleLogin = async () => {
    try {
      const res = await api.post("/login", { email, password });

      const token = res.data.token;
      const userFromBackend = res.data.user;

      const userObj = {
        ...userFromBackend,
        playerId: userFromBackend.id,
        token,
      };

      // Save to context first
      setUser(userObj);

      // Save to localStorage after (for persistence on refresh)
      localStorage.setItem("token", token);
      localStorage.setItem("playerId", userObj.playerId);
      localStorage.setItem("username", userObj.username);

      if (res.data.caps_refreshed) {
        localStorage.setItem("capsRefreshed", "true");
      }

      navigate("/pvp"); // ✅ redirect after login

    } catch (err) {
      console.error("❌ Login error:", err);
      if (err.response) {
        console.error("🚨 Server responded with:", err.response.status, err.response.data);
      } else {
        console.error("🧨 Network error or server unreachable");
      }
      setError("Login failed");
    }
  };

  // If already logged in, redirect
  if (user && window.location.pathname === "/login") {
    return <Navigate to="/pvp" />;
  }

  return (
      <div className={styles.container}>
        <h2>LOGIN</h2>
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
