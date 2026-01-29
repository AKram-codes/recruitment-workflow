import { useContext, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../services/api";
import { AuthContext } from "../auth/AuthContext";
import "./Login.css";

export default function Login() {
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleLogin = async () => {
    try {
      const res = await API.post(
        `/api/auth/login?username=${username}&password=${password}`
      );

      // Save JWT
      login(res.data);

      // 🔥 REDIRECT AFTER LOGIN
      navigate("/candidates");

    } catch (err) {
      setError("Invalid username or password");
    }
  };

  return (
  <div className="login-container">
    <div className="login-card">
      <h2>Recruitment Login</h2>

      {error && <div className="login-error">{error}</div>}

      <input
        placeholder="Username"
        onChange={(e) => setUsername(e.target.value)}
      />

      <input
        type="password"
        placeholder="Password"
        onChange={(e) => setPassword(e.target.value)}
      />

      <button onClick={handleLogin}>Login</button>
    </div>
  </div>
);
}