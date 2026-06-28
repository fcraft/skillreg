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
  gap: var(--qqx-space-xs);
  padding: 2px var(--qqx-space-sm);
  border-radius: var(--qqx-radius-full);
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
  background: var(--qqx-bg-elevated);
  color: var(--qqx-text-secondary);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.status-badge.active {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

.status-badge.stale {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}

.status-badge.unknown {
  color: var(--qqx-text-tertiary);
}
</style>
