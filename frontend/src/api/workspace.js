import { apiFetch, downloadWithAuth } from './client'

export function listConversations() {
  return apiFetch('/api/chat/ls')
}

export function createConversation(title = '新会话') {
  return apiFetch('/api/chat/create', {
    method: 'POST',
    body: { title },
  })
}

export function renameConversation(conversationId, title) {
  return apiFetch('/api/chat/update', {
    method: 'POST',
    body: { conversation_id: conversationId, title },
  })
}

export function deleteConversations(conversationIds) {
  return apiFetch('/api/chat/delete', {
    method: 'POST',
    body: { conversation_ids: conversationIds },
  })
}

export function listMessages(conversationId) {
  return apiFetch(`/api/chat/ls/${encodeURIComponent(conversationId)}`)
}

export function listAttachments(conversationId) {
  return apiFetch(
    `/api/attachment/ls?conversation_id=${encodeURIComponent(conversationId)}`,
  )
}

export function uploadAttachment(conversationId, file) {
  const form = new FormData()
  form.append('conversation_id', conversationId)
  form.append('file', file)
  return apiFetch('/api/attachment/upload', {
    method: 'POST',
    body: form,
    isForm: true,
  })
}

export function deleteAttachment(attachmentId) {
  return apiFetch('/api/attachment/delete', {
    method: 'POST',
    body: { attachment_id: attachmentId },
  })
}

export function downloadAttachment(attachmentId, fileName) {
  return downloadWithAuth(
    `/api/attachment/get?attachment_id=${encodeURIComponent(attachmentId)}`,
    fileName,
  )
}
