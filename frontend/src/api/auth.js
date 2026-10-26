import { apiFetch } from './client'

export function fetchMe() {
  return apiFetch('/api/me')
}
