<script setup>
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed } from 'vue'

const props = defineProps({
  message: { type: Object, required: true },
})

defineEmits(['download-attachment'])

const isTool = computed(() => props.message.role === 'tool')
const isUser = computed(() => props.message.role === 'user')
const rendered = computed(() => {
  if (props.message.role !== 'assistant') return ''
  const html = marked.parse(props.message.content || '')
  return DOMPurify.sanitize(typeof html === 'string' ? html : '')
})
</script>

<template>
  <div v-if="isTool" class="message tool">
    <div class="tool-line">
      <span class="tool-name">{{ message.tool_name || 'tool' }}</span>
      <span class="tool-status" :class="message.tool_status">
        {{ message.tool_status || 'done' }}
      </span>
      <span>{{ message.content }}</span>
    </div>
  </div>

  <div v-else class="message" :class="message.role">
    <div class="message-meta">
      {{ isUser ? '我' : message.role === 'assistant' ? '分析助手' : message.role }}
      <span
        v-if="message.role === 'assistant' && message.message_type === 'analysis'"
        class="analysis-chip"
      >
        分析完成
      </span>
    </div>
    <div class="bubble">
      <div v-if="message.role === 'assistant'" v-html="rendered"></div>
      <div v-else class="plain">{{ message.content }}</div>

      <div v-if="message.attachments?.length" class="attachment-chips">
        <button
          v-for="attachment in message.attachments"
          :key="attachment.attachment_id"
          class="chip"
          @click="$emit('download-attachment', attachment)"
        >
          {{ attachment.file_name }}
        </button>
      </div>
    </div>
  </div>
</template>
