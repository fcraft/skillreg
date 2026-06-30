<template>
  <span v-if="summary" class="sync-badge" :class="badgeClass" @click.stop="navigate" :title="tooltip">
    <span class="sync-dot"></span>
    {{ text }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  summary: { type: Object, default: null },
  skillName: { type: String, default: '' },
  totalTargets: { type: Number, default: 0 },
  namedCount: { type: Number, default: 0 },
  projectCount: { type: Number, default: 0 },
})

const emit = defineEmits(['open'])

const badgeClass = computed(() => {
  if (!props.summary || !props.summary.installed) return 'sync-badge--none'
  if (props.summary.changed || props.summary.missing) return 'sync-badge--warn'
  return 'sync-badge--ok'
})

const text = computed(() => {
  if (!props.summary) return ''
  const { ok, changed, missing, installed, total } = props.summary
  const t = total ?? props.totalTargets ?? 0
  if (installed === 0) return `0/${t} 已安装`
  if (ok === installed) return `${installed}/${t} 已安装`
  return `${installed}/${t} 已安装, ${changed + missing} 待处理`
})

const tooltip = computed(() => {
  if (!props.summary) return ''
  const { ok, changed, missing, installed, namedOk, namedInstalled, projInstalled, total } = props.summary
  const t = total ?? props.totalTargets ?? 0
  if (installed === 0) return `未在任何 target 中安装（共 ${t} 个目标目录）`
  const parts = []
  if (ok) parts.push(`${ok} 已同步`)
  if (changed) parts.push(`${changed} 已变更`)
  if (missing) parts.push(`${missing} 缺失`)
  let breakdown = ''
  if (props.namedCount > 0 || props.projectCount > 0) {
    breakdown = `\n配置目标: ${namedInstalled ?? 0}/${props.namedCount} · 项目组目标: ${projInstalled ?? 0}/${props.projectCount}`
  }
  return `已安装 ${installed}/${t} 个目录 · ${parts.join(' · ')}${breakdown}`
})

function navigate() {
  if (props.skillName) {
    emit('open', props.skillName)
  }
}
</script>

<style scoped>
.sync-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: var(--qqx-radius-full);
  cursor: pointer;
  transition: filter 0.15s ease;
}
.sync-badge:hover { filter: brightness(0.92); }

.sync-badge--ok { background: var(--qqx-success-light); color: var(--qqx-success); }
.sync-badge--warn { background: var(--qqx-warning-light); color: var(--qqx-warning); }
.sync-badge--none { background: var(--qqx-bg-elevated); color: var(--qqx-text-tertiary); }

.sync-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.sync-badge--ok .sync-dot { background: var(--qqx-success); }
.sync-badge--warn .sync-dot { background: var(--qqx-warning); }
.sync-badge--none .sync-dot { background: var(--qqx-text-tertiary); }
</style>
