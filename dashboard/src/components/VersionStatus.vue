<template>
  <div class="version-status" :title="statusTitle">
    <div class="version-status__summary">
      <span class="version-status__dot" :class="`version-status__dot--${status}`"></span>
      <span>{{ statusLabel }}</span>
    </div>
    <div class="version-status__versions">
      <span>前端 v{{ frontendVersion }}</span>
      <span>后端 {{ backendVersion ? `v${backendVersion}` : '不可用' }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  backendVersion: { type: String, default: null },
  serverDown: { type: Boolean, default: false },
})

const frontendVersion = __SKILLREG_DASHBOARD_VERSION__

const status = computed(() => {
  if (props.serverDown) return 'offline'
  if (!props.backendVersion) return 'checking'
  return props.backendVersion === frontendVersion ? 'synced' : 'mismatch'
})

const statusLabel = computed(() => ({
  synced: '版本一致',
  mismatch: '版本不一致',
  checking: '正在检测版本',
  offline: '后端已断开',
})[status.value])

const statusTitle = computed(() => ({
  synced: '前端构建版本与后端运行版本一致',
  mismatch: '前端构建版本与后端运行版本不一致，建议刷新或重启 Dashboard',
  checking: '正在读取后端运行版本',
  offline: '无法连接后端服务',
})[status.value])
</script>

<style scoped>
.version-status {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
  line-height: 1.35;
}

.version-status__summary {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--qqx-text-secondary);
  font-weight: var(--qqx-font-medium);
}

.version-status__dot {
  width: 7px;
  height: 7px;
  flex: 0 0 7px;
  border-radius: 9999px;
  background: var(--qqx-text-tertiary);
}

.version-status__dot--synced {
  background: var(--qqx-success, #22c55e);
}

.version-status__dot--mismatch {
  background: var(--qqx-warning, #f59e0b);
}

.version-status__dot--offline {
  background: var(--qqx-danger, #ef4444);
}

.version-status__versions {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 14px;
}
</style>
