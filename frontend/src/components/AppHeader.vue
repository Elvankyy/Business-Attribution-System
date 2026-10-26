<script setup>
import { RouterLink } from 'vue-router'

defineProps({
  user: { type: Object, default: null },
  wsStatus: { type: String, default: 'closed' },
})

defineEmits(['logout'])
</script>

<template>
  <header class="app-header">
    <div class="brand">
      <span class="brand-mark">归因</span>
      <div>
        <strong>经营归因分析系统</strong>
        <small>Business Attribution</small>
      </div>
    </div>

    <nav class="nav">
      <RouterLink to="/workspace">工作台</RouterLink>
      <RouterLink to="/admin">管理端</RouterLink>
    </nav>

    <div class="user-area">
      <span class="badge" :class="wsStatus">
        {{ wsStatus === 'connected' ? '实时在线' : wsStatus === 'connecting' ? '连接中' : '离线' }}
      </span>
      <span class="user-name">{{ user?.display_name || user?.username || '未登录' }}</span>
      <button class="btn ghost small" @click="$emit('logout')">退出</button>
    </div>
  </header>
</template>
