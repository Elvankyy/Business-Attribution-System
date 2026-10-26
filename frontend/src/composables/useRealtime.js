import { onBeforeUnmount, ref } from 'vue'

import { issueWsToken } from '../api/analysis'
import { WS_BASE } from '../api/client'

export function useRealtime(handlers = {}) {
  const status = ref('closed')
  const lastError = ref('')

  let socket = null
  let conversationId = ''
  let manualClose = false
  let attempts = 0
  let reconnectTimer = null

  async function connect(id) {
    if (!id) return
    disconnect()
    conversationId = id
    manualClose = false
    status.value = 'connecting'

    try {
      const { websocket_token: token } = await issueWsToken(id)
      const url =
        `${WS_BASE}/api/chat/ws/chat` +
        `?websocket_token=${encodeURIComponent(token)}` +
        `&conversation_id=${encodeURIComponent(id)}`

      socket = new WebSocket(url)
      socket.onopen = () => {
        attempts = 0
        status.value = 'connected'
        lastError.value = ''
      }
      socket.onmessage = (event) => {
        try {
          handlers.onEvent?.(JSON.parse(event.data))
        } catch {
          lastError.value = '收到无法解析的消息'
        }
      }
      socket.onerror = () => {
        status.value = 'error'
      }
      socket.onclose = () => {
        status.value = 'closed'
        if (manualClose || conversationId !== id) return
        if (attempts >= 5) {
          status.value = 'error'
          lastError.value = '实时连接多次重连失败'
          return
        }
        attempts += 1
        const delay = Math.min(1000 * 2 ** attempts, 10000)
        reconnectTimer = setTimeout(() => {
          connect(id).catch((exc) => {
            lastError.value = exc.message
          })
        }, delay)
      }
    } catch (exc) {
      status.value = 'error'
      lastError.value = exc.message
    }
  }

  function send(payload) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload))
      return true
    }
    return false
  }

  function disconnect() {
    manualClose = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (socket) {
      socket.close()
      socket = null
    }
    status.value = 'closed'
  }

  onBeforeUnmount(disconnect)

  return { status, lastError, connect, disconnect, send }
}
