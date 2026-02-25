import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'

function RequireAuth({ children }) {
  const { user, status } = useAuth()
  const location = useLocation()

  if (status !== 'ready') return null

  if (!user) {
    return <Navigate to="/auth" replace state={{ from: location }} />
  }

  return children
}

export default RequireAuth
