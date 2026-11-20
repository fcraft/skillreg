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
  gap: 5px;
  min-height: 22px;
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.sync-badge--ok { background: var(--sr-role-sage-surface); color: var(--sr-role-sage-ink); }
.sync-badge--warn { background: var(--sr-role-amber-surface); color: var(--sr-role-amber-ink); }
.sync-badge--none { background: var(--sr-content-bg); color: var(--sr-text-secondary); }

.sync-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--sr-radius-pill);
  flex-shrink: 0;
  background: currentColor;
}
</style>
