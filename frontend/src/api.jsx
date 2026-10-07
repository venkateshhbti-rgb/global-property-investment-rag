export const API_URL = 'http://localhost:8000'

let onUnauthorized = () => {}
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

export async function api(path, { method = 'GET', body, token } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined
    })
  } catch {
    throw new Error('Cannot reach the backend. Is it running on http://localhost:8000?')
  }

  if (response.status === 401 && token) onUnauthorized()

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Request failed'
    throw new Error(detail)
  }
  return data
}

export const formatTokens = (n) => (n || 0).toLocaleString()

export const renderInline = (text) =>
  text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4 ? <strong key={i}>{part.slice(2, -2)}</strong> : part
  )
