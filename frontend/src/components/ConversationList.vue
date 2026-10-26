<script setup>
defineProps({
  conversations: { type: Array, default: () => [] },
  currentId: { type: String, default: '' },
})

defineEmits(['create', 'select', 'rename', 'delete'])

function formatTime(value) {
  if (!value) return '暂无消息'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '暂无消息' : date.toLocaleString()
}
</script>

<template>
  <aside class="conversation-list">
    <div class="panel-head">
      <h3>会话</h3>
      <button class="btn primary small" @click="$emit('create')">新建</button>
    </div>

    <div v-if="!conversations.length" class="empty">还没有会话，点击“新建”开始。</div>

    <ul v-else>
      <li
        v-for="conversation in conversations"
        :key="conversation.conversation_id"
        :class="{ active: conversation.conversation_id === currentId }"
        @click="$emit('select', conversation.conversation_id)"
      >
        <div class="conv-main">
          <strong>{{ conversation.title }}</strong>
          <small>{{ formatTime(conversation.last_message_at) }}</small>
        </div>
        <div class="conv-actions">
          <button class="icon-btn" title="重命名" @click.stop="$emit('rename', conversation)">改</button>
          <button class="icon-btn danger" title="删除" @click.stop="$emit('delete', conversation)">删</button>
        </div>
      </li>
    </ul>
  </aside>
</template>
