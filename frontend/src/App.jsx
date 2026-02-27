import { Navigate, Route, Routes } from 'react-router-dom'
import AuthPage from './pages/auth.jsx'
import HomePage from './pages/home.jsx'
import OperationsPage from './pages/operations.jsx'
import ProfilePage from './pages/profile.jsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/home" replace />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/home" element={<HomePage />} />
      <Route path="/operations" element={<OperationsPage />} />
      <Route path="/employees/:empId/profile" element={<ProfilePage />} />
      <Route path="*" element={<Navigate to="/home" replace />} />
    </Routes>
  )
}

export default App
