function resolveUrl(path) {
  if (typeof path !== 'string' || !path) return path
  if (/^https?:\/\//i.test(path)) return path

  const baseUrl = import.meta.env.VITE_BACKEND_URL
  if (!baseUrl) {
    throw new Error('VITE_BACKEND_URL is required (example: http://127.0.0.1:8000)')
  }

  return new URL(path, baseUrl).toString()
}

export async function httpJson(path, { method = 'GET', token, body } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(resolveUrl(path), {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  const isJson = (res.headers.get('content-type') || '').includes('application/json')
  const payload = isJson ? await res.json() : null

  if (!res.ok) {
    const message = payload?.error || payload?.message || `Request failed (${res.status})`
    const error = new Error(message)
    error.status = res.status
    error.payload = payload
    throw error
  }

  return payload
}
