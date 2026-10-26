<script setup>
import { ref } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  running: { type: Boolean, default: false },
  sending: { type: Boolean, default: false },
})

const emit = defineEmits(['send', 'cancel'])
const text = ref('')

function submit() {
  const value = text.value.trim()
  if (!value || props.disabled || props.sending || props.running) return
  emit('send', value)
  text.value = ''
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}
</script>

<template>
  <div class="composer">
    <textarea
      v-model="text"
      :disabled="disabled"
      rows="2"
      placeholder="输入经营问题，Enter 发送，Shift+Enter 换行"
      @keydown="onKeydown"
    ></textarea>
    <div class="composer-actions">
      <button v-if="running" class="btn danger" @click="$emit('cancel')">停止分析</button>
      <button
        v-else
        class="btn primary"
        :disabled="disabled || sending || !text.trim()"
        @click="submit"
      >
        发送
      </button>
    </div>
  </div>
</template>
