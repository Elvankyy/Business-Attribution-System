export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '')

export const WS_BASE = (
  import.meta.env.VITE_WS_BASE_URL || 'ws://127.0.0.1:8000'
).replace(/\/$/, '')

const TOKEN_KEY = 'bas_access_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function apiFetch(path, options = {}) {
  const { method = 'GET', body, isForm = false, signal } = options
  const headers = { ...(options.headers || {}), ...authHeaders() }
  if (body !== undefined && !isForm) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  })

  if (response.status === 401) {
    clearToken()
    if (window.location.pathname !== '/login') {
      window.location.assign('/login')
    }
    throw new Error('登录已过期，请重新登录')
  }

  if (!response.ok) {
    let detail = `请求失败（${response.status}）`
    try {
      const data = await response.json()
      detail = data.detail || detail
    } catch {
      // Keep the default message when the response is not JSON.
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  if (response.status === 204) return null
  const contentType = response.headers.get('content-type') || ''
  return contentType.includes('application/json') ? response.json() : response
}

export async function downloadWithAuth(path, fallbackName = 'download') {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: authHeaders(),
  })
  if (response.status === 401) {
    clearToken()
    window.location.assign('/login')
    throw new Error('登录已过期，请重新登录')
  }
  if (!response.ok) {
    let detail = '下载失败'
    try {
      const data = await response.json()
      detail = data.detail || detail
    } catch {
      // Keep the default message when the response is not JSON.
    }
    throw new Error(typeof detail === 'string' ? detail : '下载失败')
  }

  const blob = await response.blob()
  const disposition = response.headers.get('content-disposition') || ''
  const match = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i)
  const filename = match ? decodeURIComponent(match[1]) : fallbackName
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function loginUrl(asAdmin = false) {
  return `${API_BASE}/auth/login${asAdmin ? '?as_admin=true' : ''}`
}
