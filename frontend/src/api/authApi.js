import { httpJson } from './http.js'

export function apiLogin({ username, password }) {
  return httpJson('/api/login', {
    method: 'POST',
    body: { username, password },
  })
}

export function apiMe({ token }) {
  return httpJson('/api/home', {
    method: 'GET',
    token,
  })
}

export function apiLogout({ token }) {
  return httpJson('/api/logout', {
    method: 'POST',
    token,
  })
}

export function apiOtpRequest({ channel, phone, email, team_no }) {
  return httpJson('/api/otp/request', {
    method: 'POST',
    body: { channel, phone, email, team_no },
  })
}

export function apiOtpVerify({ challenge_id, otp }) {
  return httpJson('/api/otp/verify', {
    method: 'POST',
    body: { challenge_id, otp },
  })
}

export function apiForgotPassword({ email, password }) {
  return httpJson('/api/forgot-password', {
    method: 'POST',
    body: { email, password },
  })
}

export function apiRegister({ display_name, email, phone_number, password }) {
  return httpJson('/api/register', {
    method: 'POST',
    body: { display_name, email, phone_number, password },
  })
}
