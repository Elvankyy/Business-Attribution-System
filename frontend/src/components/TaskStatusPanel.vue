<script setup>
defineProps({
  task: { type: Object, default: null },
  toolEvents: { type: Array, default: () => [] },
})

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}
</script>

<template>
  <section class="side-panel">
    <h3>实时任务</h3>

    <div v-if="!task" class="empty">暂无任务</div>

    <template v-else>
      <div class="task-summary">
        <span class="badge" :class="task.task_status">{{ task.task_status }}</span>
        <strong>{{ task.current_step || '—' }}</strong>
      </div>

      <dl class="kv">
        <dt>任务</dt>
        <dd class="mono">{{ task.task_id }}</dd>
        <dt>开始</dt>
        <dd>{{ formatTime(task.started_at) }}</dd>
        <dt>结束</dt>
        <dd>{{ formatTime(task.finished_at) }}</dd>
      </dl>

      <p v-if="task.error_message" class="error-text">{{ task.error_message }}</p>

      <h4>工具执行</h4>
      <div v-if="!toolEvents.length" class="empty small">暂无工具调用</div>
      <ul v-else class="tool-timeline">
        <li v-for="(item, index) in toolEvents" :key="index" :class="item.status">
          <span class="dot"></span>
          <div>
            <strong>{{ item.name }}</strong>
            <small>{{ item.summary }}</small>
          </div>
        </li>
      </ul>
    </template>
  </section>
</template>
