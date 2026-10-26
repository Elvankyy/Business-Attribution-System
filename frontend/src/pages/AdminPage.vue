<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { getConfigs, getLogs, getTasks, reloadConfigs } from '../api/admin'
import AppHeader from '../components/AppHeader.vue'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { user, loadUser, logout } = useAuth()

const configs = ref([])
const logs = ref([])
const tasks = ref([])
const loading = ref(false)
const error = ref('')
const message = ref('')
const activeTab = ref('configs')
const expandedTaskId = ref('')
const taskLogs = ref([])
const taskLogsLoading = ref(false)

const dataSourceGroups = ['data_source', 'datasource', 'data-source']
const featureGroups = ['feature', 'feature_flag', 'feature-flag', 'switch']

const displayedConfigs = computed(() => {
  if (activeTab.value === 'dataSources') {
    return configs.value.filter((config) =>
      dataSourceGroups.includes(config.config_group),
    )
  }
  if (activeTab.value === 'features') {
    return configs.value.filter((config) =>
      featureGroups.includes(config.config_group),
    )
  }
  return configs.value
})

const configTitle = computed(() => {
  if (activeTab.value === 'dataSources') return '数据源连接'
  if (activeTab.value === 'features') return '功能开关'
  return '系统配置'
})

const configHint = computed(() => {
  if (activeTab.value === 'dataSources') {
    return '数据源连接统一存放在 system_configs，按 config_group=data_source 区分。'
  }
  if (activeTab.value === 'features') {
    return '功能开关统一存放在 system_configs，按 config_group=feature 区分。'
  }
  return ''
})

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [configRows, logRows, taskRows] = await Promise.all([
      getConfigs(),
      getLogs({ limit: 50 }),
      getTasks({ limit: 50 }),
    ])
    configs.value = configRows
    logs.value = logRows
    tasks.value = taskRows
  } catch (exc) {
    error.value = exc.message
  } finally {
    loading.value = false
  }
}

async function refreshLogs() {
  error.value = ''
  try {
    logs.value = await getLogs({ limit: 50 })
  } catch (exc) {
    error.value = exc.message
  }
}

async function loadTaskLogs(taskId) {
  taskLogsLoading.value = true
  taskLogs.value = []
  try {
    taskLogs.value = await getLogs({ task_id: taskId, limit: 100 })
  } catch (exc) {
    error.value = exc.message
  } finally {
    taskLogsLoading.value = false
  }
}

async function toggleTaskLogs(task) {
  if (expandedTaskId.value === task.task_id) {
    expandedTaskId.value = ''
    taskLogs.value = []
    return
  }
  expandedTaskId.value = task.task_id
  await loadTaskLogs(task.task_id)
}

async function refreshTasks() {
  error.value = ''
  try {
    tasks.value = await getTasks({ limit: 50 })
    if (expandedTaskId.value) {
      await loadTaskLogs(expandedTaskId.value)
    }
  } catch (exc) {
    error.value = exc.message
  }
}

async function reload() {
  message.value = ''
  error.value = ''
  try {
    const response = await reloadConfigs()
    message.value = response.message
    await load()
  } catch (exc) {
    error.value = exc.message
  }
}

function back() {
  router.push('/workspace')
}

onMounted(async () => {
  await loadUser()
  await load()
})
</script>

<template>
  <div class="admin-shell">
    <AppHeader :user="user" ws-status="closed" @logout="logout" />

    <main class="admin-page">
      <div class="admin-head">
        <div>
          <h1>系统管理</h1>
          <p>查看系统配置、重载配置缓存、检查任务运行日志。</p>
        </div>
        <div>
          <button class="btn ghost" @click="back">返回工作台</button>
          <button class="btn primary" :disabled="loading" @click="reload">重载配置</button>
        </div>
      </div>

      <p v-if="error" class="error-banner">{{ error }}</p>
      <p v-if="message" class="ok-banner">{{ message }}</p>

      <div class="tabs admin-tabs">
        <button :class="{ active: activeTab === 'configs' }" @click="activeTab = 'configs'">
          配置
        </button>
        <button :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'">
          日志
        </button>
        <button :class="{ active: activeTab === 'tasks' }" @click="activeTab = 'tasks'">
          任务记录
        </button>
        <button
          :class="{ active: activeTab === 'dataSources' }"
          @click="activeTab = 'dataSources'"
        >
          数据源
        </button>
        <button
          :class="{ active: activeTab === 'features' }"
          @click="activeTab = 'features'"
        >
          功能开关
        </button>
      </div>

      <section v-if="activeTab !== 'logs' && activeTab !== 'tasks'" class="panel">
        <h2>{{ configTitle }}</h2>
        <p v-if="configHint" class="hint" style="margin-bottom: 12px">{{ configHint }}</p>
        <table v-if="displayedConfigs.length" class="data-table">
          <thead>
            <tr>
              <th>Key</th>
              <th>值</th>
              <th>分组</th>
              <th>更新时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="config in displayedConfigs" :key="config.config_key">
              <td class="mono">{{ config.config_key }}</td>
              <td>{{ config.config_value }}</td>
              <td>{{ config.config_group }}</td>
              <td>{{ formatTime(config.updated_at) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">暂无数据</div>
      </section>

      <section v-else-if="activeTab === 'logs'" class="panel">
        <div class="panel-title-row">
          <h2>任务日志</h2>
          <button class="btn ghost small" @click="refreshLogs">刷新日志</button>
        </div>
        <table v-if="logs.length" class="data-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>任务</th>
              <th>级别</th>
              <th>类型</th>
              <th>内容</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(log, index) in logs" :key="`${log.task_id}-${index}`">
              <td>{{ formatTime(log.created_at) }}</td>
              <td class="mono">{{ log.task_id }}</td>
              <td>{{ log.log_level }}</td>
              <td>{{ log.log_type }}</td>
              <td>{{ log.log_content }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">暂无日志</div>
      </section>

      <section v-else class="panel">
        <div class="panel-title-row">
          <h2>任务记录</h2>
          <button class="btn ghost small" @click="refreshTasks">刷新任务</button>
        </div>
        <p class="hint" style="margin-bottom: 12px">
          跨会话查看任务状态、发起用户与输入问题；点击“查看日志”展开该任务的工具日志。
        </p>
        <table v-if="tasks.length" class="data-table">
          <thead>
            <tr>
              <th>开始时间</th>
              <th>会话</th>
              <th>用户</th>
              <th>状态</th>
              <th>输入</th>
              <th>任务 ID</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="task in tasks" :key="task.task_id">
              <tr>
                <td>{{ formatTime(task.started_at) }}</td>
                <td>{{ task.conversation_title || task.conversation_id }}</td>
                <td>{{ task.display_name || task.username }}</td>
                <td>
                  <span class="badge" :class="task.task_status">{{ task.task_status }}</span>
                </td>
                <td>{{ task.input_text }}</td>
                <td class="mono">{{ task.task_id }}</td>
                <td>
                  <button class="icon-btn" @click="toggleTaskLogs(task)">
                    {{ expandedTaskId === task.task_id ? '收起' : '查看日志' }}
                  </button>
                </td>
              </tr>
              <tr v-if="expandedTaskId === task.task_id">
                <td colspan="7">
                  <div class="task-log-detail">
                    <div class="task-log-head">
                      <strong>工具日志 · {{ task.task_id }}</strong>
                      <button class="icon-btn" @click="toggleTaskLogs(task)">收起</button>
                    </div>
                    <div v-if="taskLogsLoading" class="empty small">加载中...</div>
                    <div v-else-if="taskLogs.length" class="task-log-list">
                      <div
                        v-for="(log, index) in taskLogs"
                        :key="`${log.created_at}-${index}`"
                        class="task-log-item"
                      >
                        <span class="mono">{{ formatTime(log.created_at) }}</span>
                        <span class="badge">{{ log.log_type }}</span>
                        <span>{{ log.log_content }}</span>
                      </div>
                    </div>
                    <div v-else class="empty small">
                      该任务没有工具日志（可能未调用工具或执行前失败）。
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <div v-else class="empty">暂无任务记录</div>
      </section>
    </main>
  </div>
</template>
