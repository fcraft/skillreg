<template>
  <span class="status-badge" :class="status">
    <span class="dot"></span>
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'active',
    validator: v => ['active', 'stale', 'unknown'].includes(v)
  }
})

const label = computed(() => {
  const map = { active: '活跃', stale: '久未更新', unknown: '未知' }
  return map[props.status] || props.status
})
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 22px;
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  background: var(--sr-content-bg);
  color: var(--sr-text-secondary);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: var(--sr-radius-pill);
  background: currentColor;
}

.status-badge.active {
  color: var(--sr-role-sage-ink);
  background: var(--sr-role-sage-surface);
}

.status-badge.stale {
  color: var(--sr-role-amber-ink);
  background: var(--sr-role-amber-surface);
}

.status-badge.unknown {
  color: var(--sr-text-tertiary);
}
</style>
