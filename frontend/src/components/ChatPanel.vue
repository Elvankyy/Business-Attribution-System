<script setup>
import MessageItem from './MessageItem.vue'

defineProps({
  messages: { type: Array, default: () => [] },
  streamingText: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

defineEmits(['download-attachment'])
</script>

<template>
  <div class="chat-panel">
    <div v-if="loading" class="empty">加载中...</div>
    <div v-else-if="!messages.length && !streamingText" class="empty">
      发送一个业务问题，开始分析。
    </div>

    <div v-else class="messages">
      <MessageItem
        v-for="message in messages"
        :key="message.message_id"
        :message="message"
        @download-attachment="$emit('download-attachment', $event)"
      />

      <div v-if="streamingText" class="message assistant streaming">
        <div class="message-meta">分析助手</div>
        <div class="bubble">
          <div class="plain">{{ streamingText }}<span class="cursor">▍</span></div>
        </div>
      </div>
    </div>
  </div>
</template>
