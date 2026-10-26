<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchMe } from '../api/auth'
import { clearToken, setToken } from '../api/client'

const router = useRouter()
const status = ref('正在完成登录...')
const error = ref('')

onMounted(async () => {
  const hash = window.location.hash.replace(/^#/, '')
  const hashParams = new URLSearchParams(hash)
  const queryParams = new URLSearchParams(window.location.search)
  const token = hashParams.get('token') || queryParams.get('token')

  if (!token) {
    status.value = '登录失败'
    error.value = '未收到登录令牌，请重新登录。'
    return
  }

  setToken(token)
  window.history.replaceState(null, '', window.location.pathname)

  try {
    await fetchMe()
    status.value = '登录成功，正在进入工作台...'
    await router.replace('/workspace')
  } catch (exc) {
    clearToken()
    status.value = '登录失败'
    error.value = exc.message || '登录态校验失败'
  }
})
</script>

<template>
  <div class="callback-shell">
    <div class="callback-card">
      <div class="brand-mark" style="margin: 0 auto 18px">归因</div>
      <h1 style="font-size: 20px; margin-bottom: 10px">{{ status }}</h1>
      <p v-if="error" class="error-text">{{ error }}</p>
      <p v-else class="hint">请稍候，不要关闭页面。</p>
      <p v-if="error">
        <a href="/login">返回登录入口</a>
      </p>
    </div>
  </div>
</template>
