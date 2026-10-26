<script setup>
import { ref } from 'vue'

import ResultSection from './ResultSection.vue'

const props = defineProps({
  result: { type: Object, default: null },
  taskId: { type: String, default: '' },
})

defineEmits(['download'])

const copied = ref(false)

function metricLine(metric) {
  return `${metric.metric_name}: ${metric.metric_value}${metric.metric_unit || ''}（${metric.metric_period || '—'}）`
}

async function copyAll() {
  if (!props.result) return
  const sections = [
    `问题定义\n${props.result.problem_definition}`,
    `关键指标\n${(props.result.key_metrics || []).map(metricLine).join('\n')}`,
    `证据列表\n${(props.result.evidence_list || [])
      .map((item) => `[${item.source_type}] ${item.source_name}：${item.evidence_text}`)
      .join('\n')}`,
    `归因结论\n${props.result.conclusion_text}`,
    `待补充数据\n${props.result.missing_data_text}`,
    `下一步建议\n${props.result.next_action_text}`,
  ]
  try {
    await navigator.clipboard.writeText(sections.join('\n\n'))
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 1500)
  } catch {
    copied.value = false
  }
}
</script>

<template>
  <section class="side-panel result-panel">
    <div class="panel-head" style="padding: 0 0 12px; border-bottom: none">
      <h3>分析结果</h3>
      <div class="panel-actions">
        <button class="btn ghost small" :disabled="!result" @click="copyAll">
          {{ copied ? '已复制' : '复制全部' }}
        </button>
        <button
          class="btn primary small"
          :disabled="!result || !taskId"
          @click="$emit('download')"
        >
          导出文件
        </button>
      </div>
    </div>

    <div v-if="!result" class="empty">本轮暂无结构化结果</div>

    <div v-else class="result-sections">
      <ResultSection title="问题定义">
        <p>{{ result.problem_definition }}</p>
      </ResultSection>

      <ResultSection title="关键指标">
        <table class="data-table">
          <thead>
            <tr>
              <th>指标</th>
              <th>数值</th>
              <th>单位</th>
              <th>周期</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(metric, index) in result.key_metrics" :key="index">
              <td>{{ metric.metric_name }}</td>
              <td>{{ metric.metric_value }}</td>
              <td>{{ metric.metric_unit }}</td>
              <td>{{ metric.metric_period }}</td>
            </tr>
          </tbody>
        </table>
      </ResultSection>

      <ResultSection title="证据列表">
        <div
          v-for="(evidence, index) in result.evidence_list"
          :key="index"
          class="evidence-card"
        >
          <div class="evidence-head">
            <span class="chip">{{ evidence.source_type }}</span>
            <strong>{{ evidence.source_name }}</strong>
            <span class="confidence">
              置信度 {{ Math.round((evidence.confidence || 0) * 100) }}%
            </span>
          </div>
          <p>{{ evidence.evidence_text }}</p>
          <small>关联指标：{{ evidence.related_metric || '—' }}</small>
        </div>
      </ResultSection>

      <ResultSection title="归因结论">
        <p>{{ result.conclusion_text }}</p>
      </ResultSection>

      <ResultSection title="待补充数据">
        <p>{{ result.missing_data_text }}</p>
      </ResultSection>

      <ResultSection title="下一步建议">
        <pre class="pre-wrap">{{ result.next_action_text }}</pre>
      </ResultSection>
    </div>
  </section>
</template>
