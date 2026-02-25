import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { apiForgotPassword, apiOtpRequest, apiRegister } from '../api/authApi.js'
import logo from '../assets/zdotapps.png'
import emailIcon from '../assets/email_icon.png'
import whatsappIcon from '../assets/whatsapp_icon.png'
import '../styles/auth.css'

function AuthPage() {
  const navigate = useNavigate()
  const { signIn, signInWithOtp, status, user } = useAuth()
  const [mode, setMode] = useState('login')
  const [passwordVisible, setPasswordVisible] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const [challengeId, setChallengeId] = useState(null)
  const [teams, setTeams] = useState([])
  const [teamNo, setTeamNo] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [infoMessage, setInfoMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotPassword, setForgotPassword] = useState('')
  const [forgotSubmitting, setForgotSubmitting] = useState(false)
  const [forgotError, setForgotError] = useState('')

  const [registerName, setRegisterName] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPhone, setRegisterPhone] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [registerSubmitting, setRegisterSubmitting] = useState(false)
  const [registerError, setRegisterError] = useState('')

  const otpRefs = useRef([])

  const otpKey = useMemo(() => otp.join(''), [otp])

  useEffect(() => {
    if (status === 'ready' && user) {
      navigate('/home', { replace: true })
    }
  }, [navigate, status, user])

  function onOtpChange(index, rawValue) {
    const nextValue = (rawValue || '').replace(/\s+/g, '').slice(0, 1)
    setOtp((prev) => {
      const copy = [...prev]
      copy[index] = nextValue
      return copy
    })

    if (nextValue && index < otpRefs.current.length - 1) {
      otpRefs.current[index + 1]?.focus()
    }
  }

  async function submitForgotPassword(e) {
    e.preventDefault()
    if (forgotSubmitting) return

    setForgotError('')
    setForgotSubmitting(true)
    try {
      const email = (forgotEmail || '').trim()
      const password = (forgotPassword || '').trim()
      const data = await apiForgotPassword({ email, password })
      setForgotPassword('')
      setForgotError('')
      setInfoMessage(data?.message || 'Password reset successful.')
      setMode('login')
    } catch (err) {
      setForgotError(err?.message || 'Unable to reset password')
    } finally {
      setForgotSubmitting(false)
    }
  }

  async function submitRegister(e) {
    e.preventDefault()
    if (registerSubmitting) return

    setRegisterError('')
    setRegisterSubmitting(true)
    try {
      const display_name = (registerName || '').trim()
      const email = (registerEmail || '').trim()
      const phone_number = (registerPhone || '').trim()
      const password = (registerPassword || '').trim()

      const data = await apiRegister({ display_name, email, phone_number, password })
      setInfoMessage(data?.message || 'Account created successfully. Please login.')
      setUsername(email)
      setPassword('')
      setOtp(['', '', '', '', '', ''])
      setChallengeId(null)
      setTeams([])
      setTeamNo('')
      setMode('login')
    } catch (err) {
      setRegisterError(err?.message || 'Unable to create account')
    } finally {
      setRegisterSubmitting(false)
    }
  }

  function onOtpKeyDown(index, e) {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus()
    }
  }

  async function requestOtp(channel) {
    if (submitting) return
    setErrorMessage('')
    setInfoMessage('')
    setSubmitting(true)
    try {
      const value = (username || '').trim()

      const payload = {
        channel,
        phone: channel === 'whatsapp' ? value : undefined,
        email: channel === 'email' ? value : undefined,
        team_no: teamNo || undefined,
      }

      const data = await apiOtpRequest(payload)
      setChallengeId(data.challenge_id)
      setTeams([])
      setOtp(['', '', '', '', '', ''])
      setInfoMessage(channel === 'email' ? 'Key sent to your Email Id.' : 'Key sent to your Mobile Number.')
      otpRefs.current[0]?.focus()
    } catch (err) {
      if (err?.status === 409 && Array.isArray(err?.payload?.teams)) {
        setTeams(err.payload.teams)
      }
      setChallengeId(null)
      setOtp(['', '', '', '', '', ''])
      setErrorMessage(err?.message || 'Unable to request key')
    } finally {
      setSubmitting(false)
    }
  }

  async function onSubmit(e) {
    e.preventDefault()
    if (submitting) return

    setErrorMessage('')
    setInfoMessage('')
    setSubmitting(true)
    try {
      const key = otpKey
      if (challengeId && key.length === 6) {
        await signInWithOtp({ challenge_id: challengeId, otp: key })
      } else {
        await signIn({ username, password })
      }
      navigate('/home')
    } catch (err) {
      setErrorMessage(err?.message || 'Login failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-wrapper">
      <div className="glass-panel">
        <div className="glass-content">
          <div className="logo">
            <img src={logo} alt="ZDrive" height="120" />
          </div>

          {mode === 'login' ? (
            <form id="authForm" onSubmit={onSubmit}>
              {errorMessage ? <div className="text-danger mb-2">{errorMessage}</div> : null}
              {infoMessage ? <div className="text-success mb-2">{infoMessage}</div> : null}

              <div className="field">
                <label>Email Id or Mobile Number</label>
                <input
                  type="text"
                  name="username"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value)
                    setErrorMessage('')
                    setInfoMessage('')
                    setChallengeId(null)
                    setTeams([])
                    setTeamNo('')
                    setOtp(['', '', '', '', '', ''])
                  }}
                />
              </div>

              <div className="get-key">
                <span>Get key from:</span>
                <button
                  type="button"
                  className="key-icon"
                  onClick={() => requestOtp('email')}
                  disabled={submitting}
                >
                  <img src={emailIcon} alt="Email" />
                </button>
                <button
                  type="button"
                  className="key-icon"
                  onClick={() => requestOtp('whatsapp')}
                  disabled={submitting}
                >
                  <img src={whatsappIcon} alt="WhatsApp" />
                </button>
              </div>

              {teams.length ? (
                <div className="field mt-3">
                  <label>Team Number</label>
                  <select
                    value={teamNo}
                    onChange={(e) => {
                      setTeamNo(e.target.value)
                      setErrorMessage('')
                      setInfoMessage('')
                      setChallengeId(null)
                      setOtp(['', '', '', '', '', ''])
                    }}
                  >
                    <option value="">Select team</option>
                    {teams.map((t) => (
                      <option key={`team-${t.team_no}`} value={t.team_no}>
                        Team {t.team_no}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}

              <div className="field mt-3">
                <label>Enter Key</label>
                <input type="hidden" name="key" value={otpKey} />
                <div className="otp-boxes">
                  {otp.map((value, index) => (
                    <input
                      key={`otp-${index}`}
                      type="text"
                      maxLength={1}
                      value={value}
                      onChange={(e) => onOtpChange(index, e.target.value)}
                      onKeyDown={(e) => onOtpKeyDown(index, e)}
                      ref={(el) => {
                        otpRefs.current[index] = el
                      }}
                    />
                  ))}
                </div>
              </div>

              <div className="or-text">(OR)</div>

              <div className="field password">
                <label>Password</label>
                <div className="password-input">
                  <input
                    type={passwordVisible ? 'text' : 'password'}
                    id="password"
                    name="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="password-control"
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    aria-label={passwordVisible ? 'Hide password' : 'Show password'}
                    onClick={() => setPasswordVisible((v) => !v)}
                    disabled={submitting}
                  >
                    <i className={`bi ${passwordVisible ? 'bi-eye-slash' : 'bi-eye'}`} />
                  </button>
                </div>
                <button
                  type="button"
                  className="forgot-password-under"
                  onClick={() => {
                    setInfoMessage('')
                    setErrorMessage('')
                    setForgotEmail((username || '').trim())
                    setForgotPassword('')
                    setForgotError('')
                    setMode('forgot')
                  }}
                  disabled={submitting}
                >
                  Forgot Password?
                </button>
              </div>

              <div className="create-account-row">
                <span>Doesn't have an account?</span>
                <button
                  type="button"
                  className="create-account-link"
                  onClick={() => {
                    setInfoMessage('')
                    setErrorMessage('')
                    setRegisterName('')
                    setRegisterEmail((username || '').trim())
                    setRegisterPhone('')
                    setRegisterPassword('')
                    setRegisterError('')
                    setMode('register')
                  }}
                  disabled={submitting}
                >
                  Create One
                </button>
              </div>

              <button className="auth-btn" type="submit" disabled={submitting}>
                Login
              </button>
            </form>
          ) : null}

          {mode === 'forgot' ? (
            <form onSubmit={submitForgotPassword}>
              {forgotError ? <div className="text-danger mb-2">{forgotError}</div> : null}
              {infoMessage ? <div className="text-success mb-2">{infoMessage}</div> : null}

              <div className="field">
                <label>Email</label>
                <input
                  type="email"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  disabled={forgotSubmitting}
                />
              </div>

              <div className="field">
                <label>New Password</label>
                <input
                  type="password"
                  value={forgotPassword}
                  onChange={(e) => setForgotPassword(e.target.value)}
                  disabled={forgotSubmitting}
                />
              </div>

              <div className="create-account-row">
                <button
                  type="button"
                  className="create-account-link"
                  onClick={() => {
                    if (forgotSubmitting) return
                    setForgotError('')
                    setMode('login')
                  }}
                >
                  Back to Login
                </button>
              </div>

              <button className="auth-btn" type="submit" disabled={forgotSubmitting}>
                {forgotSubmitting ? 'Submitting...' : 'Submit'}
              </button>
            </form>
          ) : null}

          {mode === 'register' ? (
            <form onSubmit={submitRegister}>
              {registerError ? <div className="text-danger mb-2">{registerError}</div> : null}
              {infoMessage ? <div className="text-success mb-2">{infoMessage}</div> : null}

              <div className="field">
                <label>User Name</label>
                <input
                  type="text"
                  value={registerName}
                  onChange={(e) => setRegisterName(e.target.value)}
                  disabled={registerSubmitting}
                />
              </div>

              <div className="field">
                <label>E-mail ID</label>
                <input
                  type="email"
                  value={registerEmail}
                  onChange={(e) => setRegisterEmail(e.target.value)}
                  disabled={registerSubmitting}
                />
              </div>

              <div className="field">
                <label>Mobile</label>
                <input
                  type="text"
                  value={registerPhone}
                  onChange={(e) => setRegisterPhone(e.target.value)}
                  disabled={registerSubmitting}
                />
              </div>

              <div className="field">
                <label>Password</label>
                <input
                  type="password"
                  value={registerPassword}
                  onChange={(e) => setRegisterPassword(e.target.value)}
                  disabled={registerSubmitting}
                />
              </div>

              <div className="create-account-row">
                <button
                  type="button"
                  className="create-account-link"
                  onClick={() => {
                    if (registerSubmitting) return
                    setRegisterError('')
                    setMode('login')
                  }}
                >
                  Back to Login
                </button>
              </div>

              <button className="auth-btn" type="submit" disabled={registerSubmitting}>
                {registerSubmitting ? 'Submitting...' : 'Create Account'}
              </button>
            </form>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export default AuthPage
