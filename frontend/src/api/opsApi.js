import { httpJson } from './http.js'

export function apiGetOnboarding(empId) {
  return httpJson(`/api/employees/${empId}/onboarding`)
}

export function apiAddDocument(empId, payload) {
  return httpJson(`/api/employees/${empId}/documents`, {
    method: 'POST',
    body: payload,
  })
}

export function apiUpdateDocument(empId, docId, payload) {
  return httpJson(`/api/employees/${empId}/documents/${docId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function apiGetOnboardingProgress() {
  return httpJson('/api/onboarding/progress')
}

export function apiGetCtcHistory(empId) {
  return httpJson(`/api/employees/${empId}/ctc-history`)
}

export function apiAddCtcHistory(empId, payload) {
  return httpJson(`/api/employees/${empId}/ctc-history`, {
    method: 'POST',
    body: payload,
  })
}

export function apiGetComplianceDashboard({ limit, offset } = {}) {
  const params = new URLSearchParams()
  if (Number.isFinite(limit)) params.set('limit', String(limit))
  if (Number.isFinite(offset)) params.set('offset', String(offset))
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return httpJson(`/api/compliance/dashboard${suffix}`)
}

export function apiGetAlerts({ limit, offset } = {}) {
  const params = new URLSearchParams()
  if (Number.isFinite(limit)) params.set('limit', String(limit))
  if (Number.isFinite(offset)) params.set('offset', String(offset))
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return httpJson(`/api/alerts${suffix}`)
}

export function apiGetHeadcountReport() {
  return httpJson('/api/reports/headcount')
}

export function apiGetJoinersLeaversReport({ start_month, end_month } = {}) {
  const params = new URLSearchParams()
  if (start_month) params.set('start_month', start_month)
  if (end_month) params.set('end_month', end_month)
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return httpJson(`/api/reports/joiners-leavers${suffix}`)
}

export function apiGetCtcLevelDistribution() {
  return httpJson('/api/reports/ctc-level-distribution')
}

export function apiGetComplianceStatusReport({ status, type } = {}) {
  const params = new URLSearchParams()
  if (status && status !== 'all') params.set('status', status)
  if (type && type !== 'all') params.set('type', type)
  const suffix = params.toString() ? `?${params.toString()}` : ''
  return httpJson(`/api/reports/compliance-status${suffix}`)
}
