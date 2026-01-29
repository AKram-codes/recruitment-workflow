import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from "./pages/Login";
import Candidates from "./pages/Candidates";
import Dashboard from "./pages/Dashboard";
import { AuthProvider } from "./auth/AuthContext";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/candidates" element={<Candidates />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
