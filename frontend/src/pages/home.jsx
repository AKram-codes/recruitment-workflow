import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import '../styles/Home.css'

function HomePage() {
  const navigate = useNavigate()
  const { member, signOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    function onDocMouseDown(e) {
      if (!menuRef.current) return
      if (!menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', onDocMouseDown)
    return () => document.removeEventListener('mousedown', onDocMouseDown)
  }, [])

  async function onLogout() {
    await signOut()
    navigate('/auth')
  }

  return (
    <div className="home-shell">
      <div className="home-topbar">
        <div className="dropdown" ref={menuRef}>
          <button
            className="home-userbtn"
            type="button"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <i className="bi bi-person-circle" />
          </button>

          <ul
            className={`dropdown-menu dropdown-menu-end home-dropdown${menuOpen ? ' show' : ''}`}
          >
            <li className="px-3 pt-2 pb-1">
              <div className="home-userline">
                <i className="bi bi-person-circle" />
                <div>
                  <div className="home-username">{member?.name || '--'}</div>
                  <div className="home-userdetail">{member?.email || '--'}</div>
                  <div className="home-userdetail">{member?.phone || '--'}</div>
                </div>
              </div>
            </li>
            <li>
              <hr className="dropdown-divider" />
            </li>
            <li className="px-3 pb-3">
              <button className="btn btn-danger w-100" type="button" onClick={onLogout}>
                Logout
              </button>
            </li>
          </ul>
        </div>
      </div>

      <main className="home-center" aria-live="polite">
        <h1 className="home-title">Welcome to hackathon</h1>
        <p className="home-subtitle">This is your Starting point of your hackathon.</p>
      </main>
    </div>
  )
}

export default HomePage
