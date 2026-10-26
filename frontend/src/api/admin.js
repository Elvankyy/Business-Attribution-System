import { apiFetch } from './client'

export function getConfigs() {
  return apiFetch('/api/admin/configs')
}

export function reloadConfigs() {
  return apiFetch('/api/admin/reload', { method: 'POST' })
}

function buildQuery(filters = {}) {
  const query = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) {
      query.set(key, String(value))
    }
  })
  return query.toString() ? `?${query.toString()}` : ''
}

export function getLogs(filters = {}) {
  return apiFetch(`/api/admin/logs${buildQuery(filters)}`)
}

export function getTasks(filters = {}) {
  return apiFetch(`/api/admin/tasks${buildQuery(filters)}`)
}
