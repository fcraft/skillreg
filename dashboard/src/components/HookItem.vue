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
.hook-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: var(--qqx-space-lg);
  background: var(--qqx-bg-card);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  transition: border-color var(--qqx-transition);
}

.hook-item:hover {
  border-color: var(--qqx-brand);
}

.hook-item--installed {
  border-left: 3px solid var(--qqx-success, #52c41a);
}

.hook-item-main {
  flex: 1;
  min-width: 0;
}

.hook-item-header {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
}

.hook-item-icon {
  color: var(--qqx-text-tertiary);
  flex-shrink: 0;
}

.hook-item-name {
  font-weight: var(--qqx-font-semibold);
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-primary);
}

.hook-installed-badge {
  display: inline-block;
  padding: 1px 8px;
  background: var(--qqx-success-bg, #f6ffed);
  color: var(--qqx-success, #52c41a);
  border: 1px solid var(--qqx-success-border, #b7eb8f);
  border-radius: var(--qqx-radius-full);
  font-size: var(--qqx-font-size-mini, 11px);
}

.hook-available-badge {
  display: inline-block;
  padding: 1px 8px;
  background: var(--qqx-bg-subtle);
  color: var(--qqx-text-tertiary);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  font-size: var(--qqx-font-size-mini, 11px);
}

.hook-item-desc {
  margin: var(--qqx-space-xs) 0 0 0;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  line-height: 1.5;
}

.hook-item-meta {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  margin-top: var(--qqx-space-sm);
}

.hook-meta-tag {
  display: inline-block;
  padding: 1px 8px;
  background: var(--qqx-bg-subtle);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  font-size: var(--qqx-font-size-mini, 11px);
  color: var(--qqx-text-tertiary);
  font-family: var(--qqx-font-mono, monospace);
}

.hook-meta-path {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  font-family: var(--qqx-font-mono, monospace);
}

.hook-item-actions {
  flex-shrink: 0;
  margin-left: var(--qqx-space-lg);
}
</style>
