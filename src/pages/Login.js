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
  console.log("🔐 handleLogin called");

  try {
    const res = await api.post("/login", { email, password });

    console.log("✅ Login response:", res); // Full raw response

    // Comment out navigation to see logs
    // window.location.href = "/pvp";

    setUser({
      ...res.data.user,
      playerId: res.data.user.id,
      token: res.data.token,
    });

  } catch (err) {
    console.error("❌ Login error:", err.message);
    if (err.response) {
      console.error("🚨 Server responded with:", err.response.status, err.response.data);
    } else {
      console.error("🧨 Network error or server unreachable");
    }
    setError('Login failed');
  }
};



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
