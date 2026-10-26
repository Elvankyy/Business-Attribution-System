import { apiFetch, downloadWithAuth } from './client'

export function issueWsToken(conversationId) {
  return apiFetch('/api/chat/ws-token', {
    method: 'POST',
    body: { conversation_id: conversationId },
  })
}

export function getTask(taskId) {
  return apiFetch(`/api/tasks/${encodeURIComponent(taskId)}`)
}

export function listTasks(conversationId) {
  return apiFetch(
    `/api/tasks?conversation_id=${encodeURIComponent(conversationId)}`,
  )
}

export function getTaskLogs(taskId) {
  return apiFetch(`/api/tasks/${encodeURIComponent(taskId)}/logs`)
}

export function cancelTask(taskId) {
  return apiFetch(`/api/tasks/${encodeURIComponent(taskId)}/cancel`, {
    method: 'POST',
  })
}

export function getResult(taskId) {
  return apiFetch(`/api/results/${encodeURIComponent(taskId)}`)
}

export function downloadResult(taskId, fileName = 'analysis-result.md') {
  return downloadWithAuth(
    `/api/results/${encodeURIComponent(taskId)}/file`,
    fileName,
  )
}
