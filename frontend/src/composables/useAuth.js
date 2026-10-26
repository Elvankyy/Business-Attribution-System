import { ref } from 'vue'

import { fetchMe } from '../api/auth'
import { clearToken, getToken } from '../api/client'

export function useAuth() {
  const user = ref(null)
  const loading = ref(false)

  async function loadUser() {
    if (!getToken()) {
      user.value = null
      return null
    }
    loading.value = true
    try {
      user.value = await fetchMe()
    } catch {
      user.value = null
    } finally {
      loading.value = false
    }
    return user.value
  }

  function logout() {
    clearToken()
    user.value = null
    window.location.assign('/login')
  }

  return { user, loading, loadUser, logout }
}
