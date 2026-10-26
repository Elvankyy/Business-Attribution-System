<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  cancelTask,
  downloadResult,
  getResult,
  getTask,
  getTaskLogs,
  listTasks,
} from '../api/analysis'
import {
  deleteAttachment,
  downloadAttachment,
  uploadAttachment,
} from '../api/workspace'
import AppHeader from '../components/AppHeader.vue'
import AttachmentSidebar from '../components/AttachmentSidebar.vue'
import ChatPanel from '../components/ChatPanel.vue'
import ConversationList from '../components/ConversationList.vue'
import MessageInput from '../components/MessageInput.vue'
import ResultPanel from '../components/ResultPanel.vue'
import TaskHistorySelect from '../components/TaskHistorySelect.vue'
import TaskStatusPanel from '../components/TaskStatusPanel.vue'
import { useAuth } from '../composables/useAuth'
import { useRealtime } from '../composables/useRealtime'
import { useWorkspace } from '../composables/useWorkspace'

const route = useRoute()
const router = useRouter()
const { user, loadUser, logout } = useAuth()
const workspace = useWorkspace()
const {
  conversations,
  currentId,
  messages,
  attachments,
  loading,
  error,
} = workspace

const rightTab = ref('result')
const task = ref(null)
const taskHistory = ref([])
const selectedTaskId = ref('')
const result = ref(null)
const toolEvents = ref([])
const streamingText = ref('')
const sending = ref(false)
const uploading = ref(false)
const actionError = ref('')

const realtime = useRealtime({ onEvent: handleRealtimeEvent })
const wsStatus = realtime.status
const realtimeError = realtime.lastError

const currentConversation = computed(
  () =>
    conversations.value.find(
      (conversation) => conversation.conversation_id === currentId.value,
    ) || null,
)

function taskKey(conversationId) {
  return `bas_last_task_${conversationId}`
}

function resetRun() {
  task.value = null
  selectedTaskId.value = ''
  result.value = null
  toolEvents.value = []
  streamingText.value = ''
  actionError.value = ''
}

async function selectConversation(conversationId) {
  if (!conversationId) return
  await workspace.select(conversationId)
  resetRun()
  taskHistory.value = []
  router.replace(`/workspace/${conversationId}`)
  await realtime.connect(conversationId)
  await loadTaskHistory(conversationId)
}

async function loadTaskHistory(conversationId) {
  if (!conversationId) {
    taskHistory.value = []
    return
  }
  try {
    taskHistory.value = await listTasks(conversationId)
    if (!taskHistory.value.length) {
      resetRun()
      return
    }
    const stored = localStorage.getItem(taskKey(conversationId))
    const chosen =
      taskHistory.value.find((item) => item.task_id === stored) ||
      taskHistory.value[0]
    await selectTask(chosen.task_id)
  } catch (exc) {
    taskHistory.value = []
    actionError.value = exc.message
  }
}

async function selectTask(taskId) {
  if (!taskId) return
  selectedTaskId.value = taskId
  if (currentId.value) {
    localStorage.setItem(taskKey(currentId.value), taskId)
  }

  try {
    const [latestTask, logs] = await Promise.all([
      getTask(taskId),
      getTaskLogs(taskId),
    ])
    task.value = latestTask
    toolEvents.value = logs
      .filter((log) => log.log_type === 'tool')
      .map((log) => {
        const [name, rest] = log.log_content.split(' 耗时 ', 2)
        const summary =
          rest && rest.includes('：')
            ? rest.split('：').slice(1).join('：')
            : log.log_content
        return { name, status: 'done', summary }
      })

    if (latestTask.task_status === 'success') {
      try {
        result.value = await getResult(taskId)
        rightTab.value = 'result'
      } catch {
        result.value = null
        rightTab.value = 'task'
      }
    } else {
      result.value = null
      rightTab.value = 'task'
    }
  } catch (exc) {
    actionError.value = exc.message
  }
}

async function bootstrap() {
  await loadUser()
  await workspace.loadConversations()
  const routeId =
    typeof route.params.conversationId === 'string'
      ? route.params.conversationId
      : ''
  const exists = conversations.value.some(
    (conversation) => conversation.conversation_id === routeId,
  )
  if (routeId && exists) {
    await selectConversation(routeId)
  } else if (conversations.value.length) {
    await selectConversation(conversations.value[0].conversation_id)
  }
}

onMounted(bootstrap)

async function createConversation() {
  actionError.value = ''
  try {
    const conversation = await workspace.create('新会话')
    await selectConversation(conversation.conversation_id)
  } catch (exc) {
    actionError.value = exc.message
  }
}

async function renameConversation(conversation) {
  const title = window.prompt('会话标题', conversation.title)
  if (!title || !title.trim() || title.trim() === conversation.title) return
  try {
    await workspace.rename(conversation.conversation_id, title.trim())
  } catch (exc) {
    actionError.value = exc.message
  }
}

async function deleteConversation(conversation) {
  if (!window.confirm(`删除会话“${conversation.title}”？此操作会清理消息和附件。`)) {
    return
  }
  const wasCurrent = currentId.value === conversation.conversation_id
  try {
    await workspace.remove(conversation.conversation_id)
    if (wasCurrent) {
      realtime.disconnect()
      resetRun()
      router.replace('/workspace')
    }
  } catch (exc) {
    actionError.value = exc.message
  }
}

async function sendMessage(content) {
  if (!currentId.value) {
    actionError.value = '请先创建或选择会话'
    return
  }
  if (task.value?.task_status === 'running') {
    actionError.value = '当前会话已有运行中的分析任务'
    return
  }
  actionError.value = ''
  resetRun()
  sending.value = true

  const optimistic = {
    message_id: `local-${Date.now()}`,
    role: 'user',
    message_type: 'text',
    content,
    attachments: [],
    created_at: new Date().toISOString(),
  }
  messages.value = [...messages.value, optimistic]

  const sent = realtime.send({ type: 'user_message', content })
  if (!sent) {
    actionError.value = '实时连接未就绪，请稍后重试'
    messages.value = messages.value.filter(
      (message) => message.message_id !== optimistic.message_id,
    )
  }
  sending.value = false
}

async function handleRealtimeEvent(event) {
  switch (event.type) {
    case 'message_start':
      task.value = {
        task_id: event.task_id,
        task_status: 'running',
        current_step: '准备分析',
        started_at: new Date().toISOString(),
        finished_at: null,
        error_message: null,
      }
      selectedTaskId.value = event.task_id
      toolEvents.value = []
      result.value = null
      streamingText.value = ''
      rightTab.value = 'task'
      localStorage.setItem(taskKey(currentId.value), event.task_id)
      break
    case 'task_status':
      task.value = {
        ...(task.value || {}),
        task_id: event.task_id,
        task_status: event.task_status,
        current_step: event.current_step,
      }
      break
    case 'tool_start':
      toolEvents.value = [
        ...toolEvents.value,
        { name: event.tool_name, status: 'running', summary: '执行中...' },
      ]
      break
    case 'tool_finish':
      toolEvents.value = [
        ...toolEvents.value,
        {
          name: event.tool_name,
          status: 'done',
          summary: event.tool_result_summary,
        },
      ]
      break
    case 'message_delta':
      streamingText.value += event.delta_text || ''
      break
    case 'result_ready':
      loadResult(event.task_id)
      break
    case 'error':
      actionError.value = event.error_message || '分析失败'
      break
    case 'done':
      if (event.task_id) {
        localStorage.setItem(taskKey(currentId.value), event.task_id)
      }
      streamingText.value = ''
      await workspace.loadMessages(currentId.value)
      await loadTaskHistory(currentId.value)
      break
    default:
      break
  }
}

async function loadResult(taskId) {
  try {
    result.value = await getResult(taskId)
    rightTab.value = 'result'
  } catch (exc) {
    actionError.value = exc.message
  }
}

async function cancelCurrent() {
  if (!task.value?.task_id) return
  try {
    await cancelTask(task.value.task_id)
    actionError.value = ''
  } catch (exc) {
    actionError.value = exc.message
  }
}

async function uploadFile(file) {
  if (!currentId.value || !file) return
  uploading.value = true
  actionError.value = ''
  try {
    await uploadAttachment(currentId.value, file)
    await workspace.loadAttachments(currentId.value)
  } catch (exc) {
    actionError.value = exc.message
  } finally {
    uploading.value = false
  }
}

async function removeAttachment(attachment) {
  if (!window.confirm(`删除附件“${attachment.file_name}”？`)) return
  try {
    await deleteAttachment(attachment.attachment_id)
    await workspace.loadAttachments(currentId.value)
  } catch (exc) {
    actionError.value = exc.message
  }
}

function downloadAtt(attachment) {
  downloadAttachment(attachment.attachment_id, attachment.file_name).catch(
    (exc) => {
      actionError.value = exc.message
    },
  )
}

async function downloadCurrentResult() {
  if (!task.value?.task_id) return
  try {
    await downloadResult(task.value.task_id)
  } catch (exc) {
    actionError.value = exc.message
  }
}

function logoutUser() {
  realtime.disconnect()
  logout()
}
</script>

<template>
  <div class="app-shell">
    <AppHeader :user="user" :ws-status="wsStatus" @logout="logoutUser" />

    <main class="workspace">
      <ConversationList
        :conversations="conversations"
        :current-id="currentId"
        @create="createConversation"
        @select="selectConversation"
        @rename="renameConversation"
        @delete="deleteConversation"
      />

      <section class="center">
        <div class="center-head">
          <div>
            <h2>{{ currentConversation?.title || '聊天工作台' }}</h2>
            <p>
              {{
                currentConversation
                  ? `会话 ${currentConversation.conversation_id}`
                  : '创建或选择一个会话开始分析'
              }}
            </p>
          </div>
          <span class="badge" :class="wsStatus">
            {{
              wsStatus === 'connected'
                ? '实时连接'
                : wsStatus === 'connecting'
                  ? '连接中'
                  : '未连接'
            }}
          </span>
        </div>

        <ChatPanel
          :messages="messages"
          :streaming-text="streamingText"
          :loading="loading"
          @download-attachment="downloadAtt"
        />

        <MessageInput
          :disabled="!currentId"
          :running="task?.task_status === 'running'"
          :sending="sending"
          @send="sendMessage"
          @cancel="cancelCurrent"
        />

        <p v-if="actionError || realtimeError || error" class="error-banner">
          {{ actionError || realtimeError || error }}
        </p>
      </section>

      <aside class="right">
        <TaskHistorySelect
          v-if="taskHistory.length"
          :tasks="taskHistory"
          :model-value="selectedTaskId"
          @update:model-value="selectTask"
        />

        <div class="tabs">
          <button :class="{ active: rightTab === 'result' }" @click="rightTab = 'result'">
            结果
          </button>
          <button :class="{ active: rightTab === 'task' }" @click="rightTab = 'task'">
            任务
          </button>
          <button
            :class="{ active: rightTab === 'attachment' }"
            @click="rightTab = 'attachment'"
          >
            附件
          </button>
        </div>

        <ResultPanel
          v-if="rightTab === 'result'"
          :result="result"
          :task-id="task?.task_id || ''"
          @download="downloadCurrentResult"
        />

        <TaskStatusPanel
          v-else-if="rightTab === 'task'"
          :task="task"
          :tool-events="toolEvents"
        />

        <AttachmentSidebar
          v-else
          :attachments="attachments"
          :uploading="uploading"
          :disabled="!currentId"
          @upload="uploadFile"
          @delete="removeAttachment"
          @download="downloadAtt"
        />
      </aside>
    </main>
  </div>
</template>
