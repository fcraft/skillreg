<template>
  <div class="hook-item" :class="{ 'hook-item--installed': hook.installed }">
    <div class="hook-item-main">
      <div class="hook-item-header">
        <Link :size="16" class="hook-item-icon" />
        <span class="hook-item-name">{{ hook.id }}</span>
        <span v-if="hook.installed" class="hook-installed-badge">已安装</span>
        <span v-else class="hook-available-badge">可用</span>
      </div>
      <p v-if="hook.description" class="hook-item-desc">{{ hook.description }}</p>
      <div class="hook-item-meta">
        <span class="hook-meta-tag">{{ hook.matcher || 'unknown' }}</span>
        <span v-if="hook.event" class="hook-meta-tag">{{ hook.event }}</span>
        <span class="hook-meta-path">{{ hook.path }}</span>
      </div>
    </div>
    <div class="hook-item-actions">
      <QButton
        v-if="hook.installed"
        type="ghost"
        size="small"
        tint="danger"
        :disabled="actionLoading"
        @click="$emit('toggle', hook, false)"
      >
        卸载
      </QButton>
      <QButton
        v-else
        type="secondary"
        size="small"
        tint="brand"
        :disabled="actionLoading"
        @click="$emit('toggle', hook, true)"
      >
        安装
      </QButton>
    </div>
  </div>
</template>

<script setup>
import { Link } from 'lucide-vue-next'
import QButton from './QButton.vue'

defineProps({
  hook: { type: Object, required: true },
  actionLoading: { type: Boolean, default: false },
})

defineEmits(['toggle'])
</script>

<style scoped>
/* Uniform borderless Workbench card — zero left stripe, zero border */
.hook-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: var(--sr-space-4);
  background: var(--sr-content-bg);
  border: none;
  border-radius: var(--sr-radius-md);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.hook-item:hover {
  background: var(--sr-content-bg-hover);
}

.hook-item-main {
  flex: 1;
  min-width: 0;
}

.hook-item-header {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
}

.hook-item-icon {
  color: var(--sr-text-tertiary);
  flex-shrink: 0;
}

.hook-item-name {
  font-weight: var(--sr-weight-semibold);
  font-size: var(--sr-text-body);
  color: var(--sr-text-primary);
}

.hook-installed-badge {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  background: var(--sr-role-sage-surface);
  color: var(--sr-role-sage-ink);
  border: none;
  border-radius: var(--sr-radius-badge);
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
}

.hook-available-badge {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  background: var(--sr-bg-panel);
  color: var(--sr-text-secondary);
  border: none;
  border-radius: var(--sr-radius-badge);
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
}

.hook-item-desc {
  margin: var(--sr-space-1) 0 0 0;
  font-size: var(--sr-text-card-title);
  color: var(--sr-text-secondary);
  line-height: 1.55;
}

.hook-item-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--sr-space-2);
  margin-top: var(--sr-space-2);
}

.hook-meta-tag {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  background: var(--sr-bg-panel);
  border: none;
  border-radius: var(--sr-radius-badge);
  font-size: var(--sr-text-meta);
  color: var(--sr-text-secondary);
  font-family: var(--sr-font-mono);
}

.hook-meta-path {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
  font-family: var(--sr-font-mono);
}

.hook-item-actions {
  flex-shrink: 0;
  margin-left: var(--sr-space-4);
}
</style>
