<script setup>
import { ref } from 'vue'

const props = defineProps({
  attachments: { type: Array, default: () => [] },
  uploading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['upload', 'delete', 'download'])

const input = ref(null)

function choose() {
  if (!props.disabled && !props.uploading) input.value?.click()
}

function onChange(event) {
  const file = event.target.files?.[0]
  if (file) {
    emit('upload', file)
  }
  event.target.value = ''
}

function formatSize(bytes) {
  if (!bytes) return '0 KB'
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.ceil(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <section class="side-panel">
    <div class="panel-head" style="padding: 0 0 12px; border-bottom: none">
      <h3>附件</h3>
      <button class="btn primary small" :disabled="disabled || uploading" @click="choose">
        {{ uploading ? '上传中...' : '上传' }}
      </button>
    </div>
    <input ref="input" class="hidden-input" type="file" @change="onChange" />

    <div v-if="!attachments.length" class="empty">暂无附件</div>

    <ul v-else class="attachment-list">
      <li v-for="attachment in attachments" :key="attachment.attachment_id">
        <div class="file-icon">文件</div>
        <div class="file-info">
          <strong>{{ attachment.file_name }}</strong>
          <small>
            {{ attachment.file_type || '未知类型' }} ·
            {{ formatSize(attachment.file_size) }} ·
            {{ attachment.parse_status }}
          </small>
        </div>
        <div class="conv-actions">
          <button class="icon-btn" @click="$emit('download', attachment)">下载</button>
          <button class="icon-btn danger" @click="$emit('delete', attachment)">删除</button>
        </div>
      </li>
    </ul>
  </section>
</template>
