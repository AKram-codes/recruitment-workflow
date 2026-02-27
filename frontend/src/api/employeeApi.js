import { httpJson } from './http.js'

export function apiListEmployees({ status = 'all', search = '', limit = 25, offset = 0 } = {}) {
  const params = new URLSearchParams({
    status,
    search,
    limit: String(limit),
    offset: String(offset),
  })
  return httpJson(`/api/employees?${params.toString()}`)
}

export function apiGetEmployee(empId) {
  return httpJson(`/api/employees/${empId}`)
}

export function apiGetEmployeeProfile(empId) {
  return httpJson(`/api/employees/${empId}/profile`)
}

export function apiCreateEmployee(payload) {
  return httpJson('/api/employees', {
    method: 'POST',
    body: payload,
  })
}

export function apiUpdateEmployee(empId, payload) {
  return httpJson(`/api/employees/${empId}`, {
    method: 'PUT',
    body: payload,
  })
}

export function apiExitEmployee(empId, endDate) {
  return httpJson(`/api/employees/${empId}/exit`, {
    method: 'POST',
    body: { end_date: endDate },
  })
}
