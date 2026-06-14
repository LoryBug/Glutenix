<template>
  <details class="help-box mb-2" open>
    <summary>{{ title }}</summary>
    <div class="help-content">
      <slot />
    </div>
  </details>
</template>

<script setup>
defineProps({
  title: { type: String, default: 'Aiuto' },
})
</script>

<style scoped>
.help-box {
  background: #eef6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: .85rem 1rem;
}
.help-box summary {
  cursor: pointer;
  font-weight: 700;
  color: #1e3a8a;
}
.help-content {
  margin-top: .5rem;
  color: #334155;
  font-size: .875rem;
  line-height: 1.45;
}
.help-content p + p { margin-top: .45rem; }
</style>
