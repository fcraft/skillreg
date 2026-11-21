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
  gap: 4px;
  padding: 10px 12px;
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-meta);
  line-height: 1.4;
}

.version-status__summary {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--sr-text-secondary);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-semibold);
}

.version-status__dot {
  width: 7px;
  height: 7px;
  flex: 0 0 7px;
  border-radius: var(--sr-radius-pill);
  background: var(--sr-text-tertiary);
}

.version-status__dot--synced {
  background: var(--sr-role-sage-solid);
}

.version-status__dot--mismatch {
  background: var(--sr-role-amber-solid);
}

.version-status__dot--offline {
  background: var(--sr-role-rose-solid);
}

.version-status__versions {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding-left: 14px;
  font-family: var(--sr-font-mono);
}
</style>
