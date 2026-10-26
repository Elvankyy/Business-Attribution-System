import { createRouter, createWebHistory } from 'vue-router'

import AdminPage from '../pages/AdminPage.vue'
import CallbackPage from '../pages/CallbackPage.vue'
import LoginPage from '../pages/LoginPage.vue'
import WorkspacePage from '../pages/WorkspacePage.vue'
import { fetchMe } from '../api/auth'
import { getToken } from '../api/client'

const routes = [
  { path: '/', redirect: '/workspace' },
  { path: '/login', component: LoginPage, meta: { public: true } },
  {
    path: '/auth/callback',
    component: CallbackPage,
    meta: { public: true },
  },
  { path: '/workspace/:conversationId?', component: WorkspacePage },
  { path: '/admin', component: AdminPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const token = getToken()
  if (!to.meta.public && !token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && token) {
    return { path: '/workspace' }
  }
  if (to.path === '/admin' && token) {
    try {
      const user = await fetchMe()
      if (user.role !== 'admin') {
        return { path: '/workspace' }
      }
    } catch {
      return { path: '/login' }
    }
  }
  return true
})

export default router
