<script setup>
const props = defineProps({
  tasks: { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
})

defineEmits(['update:modelValue'])

function label(task, index) {
  const status = task.task_status || 'unknown'
  const time = task.started_at
    ? new Date(task.started_at).toLocaleString()
    : '时间未知'
  const text = (task.input_text || '').replace(/\s+/g, ' ').slice(0, 18)
  const round = props.tasks.length - index
  return `第 ${round} 轮 · ${status} · ${time}${text ? ` · ${text}` : ''}`
}
</script>

<template>
  <label class="history-select">
    <span>历史任务</span>
    <select
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option v-for="(task, index) in tasks" :key="task.task_id" :value="task.task_id">
        {{ label(task, index) }}
      </option>
    </select>
  </label>
</template>
