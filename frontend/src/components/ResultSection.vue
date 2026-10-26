<script setup>
defineProps({
  title: { type: String, required: true },
})
</script>

<template>
  <section class="result-section">
    <h4>{{ title }}</h4>
    <div class="result-body">
      <slot />
    </div>
  </section>
</template>
