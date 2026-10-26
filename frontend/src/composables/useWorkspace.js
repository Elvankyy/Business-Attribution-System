import { ref } from 'vue'

import * as api from '../api/workspace'

export function useWorkspace() {
  const conversations = ref([])
  const currentId = ref('')
  const messages = ref([])
  const attachments = ref([])
  const loading = ref(false)
  const error = ref('')

  async function loadConversations() {
    loading.value = true
    error.value = ''
    try {
      conversations.value = await api.listConversations()
    } catch (exc) {
      error.value = exc.message
    } finally {
      loading.value = false
    }
  }

  async function create(title = '新会话') {
    const conversation = await api.createConversation(title)
    await loadConversations()
    return conversation
  }

  async function rename(conversationId, title) {
    await api.renameConversation(conversationId, title)
    await loadConversations()
  }

  async function remove(conversationId) {
    await api.deleteConversations([conversationId])
    if (currentId.value === conversationId) {
      currentId.value = ''
      messages.value = []
      attachments.value = []
    }
    await loadConversations()
  }

  async function loadMessages(conversationId) {
    if (!conversationId) {
      messages.value = []
      return
    }
    loading.value = true
    try {
      messages.value = await api.listMessages(conversationId)
    } catch (exc) {
      error.value = exc.message
      messages.value = []
    } finally {
      loading.value = false
    }
  }

  async function loadAttachments(conversationId) {
    if (!conversationId) {
      attachments.value = []
      return
    }
    try {
      attachments.value = await api.listAttachments(conversationId)
    } catch {
      attachments.value = []
    }
  }

  async function select(conversationId) {
    currentId.value = conversationId
    await Promise.all([
      loadMessages(conversationId),
      loadAttachments(conversationId),
    ])
  }

  return {
    conversations,
    currentId,
    messages,
    attachments,
    loading,
    error,
    loadConversations,
    create,
    rename,
    remove,
    select,
    loadMessages,
    loadAttachments,
  }
}
