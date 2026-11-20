<template>
  <QCard
    :class="['ssh-host-card', { 'ssh-host-card--selected': selected, 'ssh-host-card--online': isOnline, 'ssh-host-card--offline': checked && !isOnline }]"
    :hoverable="true"
    @click="$emit('select')"
  >
    <div class="host-card-body">
      <!-- Header: status dot + host id -->
      <div class="host-card-header">
        <span :class="['host-status-dot', statusDotClass]" :title="statusTitle" />
        <span class="host-id">{{ host.id }}</span>
        <button class="host-more-btn" @click.stop="showMenu = !showMenu" title="更多操作">
          <MoreHorizontal :size="14" />
        </button>
        <div v-if="showMenu" class="host-menu" @click.stop>
          <button class="host-menu-item" @click="$emit('edit'); showMenu = false">
            <Pencil :size="13" /> 编辑
          </button>
          <button class="host-menu-item host-menu-item--danger" @click="$emit('delete'); showMenu = false">
            <Trash2 :size="13" /> 删除
          </button>
          <button class="host-menu-item" @click="$emit('check'); showMenu = false">
            <RefreshCw :size="13" /> 重新检查
          </button>
        </div>
      </div>

      <!-- Label -->
      <div v-if="host.label" class="host-label">{{ host.label }}</div>

      <!-- Connection info -->
      <div class="host-address">{{ host.hostname }}{{ host.port && host.port !== 22 ? ':' + host.port : '' }}</div>
      <div class="host-user">{{ host.user ? host.user + '@' : '' }}{{ host.hostname }}</div>
      <div class="host-path" :title="host.agentHubPath">{{ host.agentHubPath }}</div>

      <!-- Status section -->
      <div class="host-status-section">
        <!-- Loading -->
        <div v-if="checkLoading" class="host-status-loading">检查中...</div>

        <!-- Error state -->
        <div v-else-if="checked && !isOnline" class="host-status-error">
          {{ reasonText }}
        </div>

        <!-- Online: show skill counts when we have status -->
        <template v-else-if="isOnline && statusText">
          <div class="host-status-sync" :class="syncStatusClass">{{ statusText }}</div>
        </template>

        <!-- Online but no status yet -->
        <div v-else-if="isOnline" class="host-status-online">● 在线</div>

        <!-- Not checked yet -->
        <div v-else class="host-status-unknown">点击查看详情</div>
      </div>

      <!-- Action -->
      <div class="host-card-actions">
        <QButton v-if="isOnline" type="primary" size="small" @click.stop="$emit('select')">
          管理此主机
        </QButton>
        <QButton v-else type="text" size="small" @click.stop="$emit('check')">
          检查连接
        </QButton>
      </div>
    </div>
  </QCard>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { MoreHorizontal, Pencil, Trash2, RefreshCw } from 'lucide-vue-next'
import QCard from '../QCard.vue'
import QButton from '../QButton.vue'

const props = defineProps({
  host: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  checkResult: { type: Object, default: null },   // { ok, reason, detail, loading }
  statusText: { type: String, default: '' },       // pre-formatted status summary
})

defineEmits(['select', 'edit', 'delete', 'check'])

const showMenu = ref(false)

// Click outside to close menu
function onDocClick() { showMenu.value = false }
onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))

const checked = computed(() => props.checkResult && !props.checkResult.loading)
const checkLoading = computed(() => props.checkResult?.loading)
const isOnline = computed(() => props.checkResult?.ok === true)

const statusDotClass = computed(() => {
  if (checkLoading.value) return 'host-status-dot--loading'
  if (!checked.value) return 'host-status-dot--unknown'
  return isOnline.value ? 'host-status-dot--online' : 'host-status-dot--offline'
})

const statusTitle = computed(() => {
  if (checkLoading.value) return '检查中...'
  if (!checked.value) return '未检查'
  return isOnline.value ? '在线' : '离线'
})

const reasonText = computed(() => {
  if (!props.checkResult) return ''
  const { reason, detail } = props.checkResult
  if (reason === 'unreachable') return '连接失败'
  if (reason === 'auth_failed') return '认证失败'
  if (reason === 'no_agent_hub') return '未找到远程 workspace'
  if (reason === 'error') return detail || '未知错误'
  return detail || '未知错误'
})

const syncStatusClass = computed(() => {
  if (!props.statusText) return ''
  if (props.statusText.includes('待同步') || props.statusText.includes('updated')) return 'host-status-sync--pending'
  return 'host-status-sync--ok'
})
</script>

<style scoped>
.ssh-host-card {
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
  cursor: pointer;
}

.ssh-host-card--selected {
  box-shadow: inset 0 0 0 2px var(--sr-accent);
}

.host-card-body {
  padding: 2px 0;
}

.host-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.host-status-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--sr-radius-pill);
  flex-shrink: 0;
  background: var(--sr-text-tertiary);
}

.host-status-dot--online {
  background: var(--sr-role-sage-solid);
}

.host-status-dot--offline {
  background: var(--sr-text-tertiary);
}

.host-status-dot--loading {
  background: var(--sr-text-tertiary);
  animation: dot-pulse 1.2s ease-in-out infinite;
}

.host-status-dot--unknown {
  background: transparent;
  border: 1.5px solid var(--sr-text-tertiary);
}

@keyframes dot-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

.host-id {
  font-size: var(--sr-text-body);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
  font-family: var(--sr-font-sans);
}

.host-more-btn {
  margin-left: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--sr-text-secondary);
  border-radius: var(--sr-radius-sm);
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
}

.host-more-btn:hover {
  background: var(--sr-action-bg-hover);
  color: var(--sr-text-primary);
}

.host-menu {
  position: absolute;
  right: 20px;
  top: 40px;
  z-index: var(--sr-z-popover);
  background: var(--sr-glass-bg);
  backdrop-filter: var(--sr-glass-filter);
  -webkit-backdrop-filter: var(--sr-glass-filter);
  border: none;
  border-radius: var(--sr-radius-md);
  padding: 5px;
  min-width: 132px;
  box-shadow: var(--sr-shadow-md);
}

.host-menu-item {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  width: 100%;
  min-height: 32px;
  padding: 5px 8px;
  border: none;
  background: transparent;
  color: var(--sr-text-primary);
  font-size: var(--sr-text-compact);
  border-radius: var(--sr-radius-menu-item);
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.host-menu-item:hover {
  background: var(--sr-bg-hover);
}

.host-menu-item--danger {
  color: var(--sr-role-rose-ink);
}

.host-menu-item--danger:hover {
  background: var(--sr-role-rose-surface);
}

.host-label {
  font-size: var(--sr-text-body);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
  margin-bottom: 4px;
  font-family: var(--sr-font-sans);
}

.host-address,
.host-user,
.host-path {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-secondary);
  line-height: 1.6;
  font-family: var(--sr-font-sans);
}

.host-path {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 8px;
  font-family: var(--sr-font-mono);
}

.host-status-section {
  margin: 8px 0;
  min-height: 20px;
}

.host-status-loading {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-secondary);
}

.host-status-error {
  font-size: var(--sr-text-compact);
  color: var(--sr-role-rose-ink);
}

.host-status-online {
  font-size: var(--sr-text-compact);
  color: var(--sr-role-sage-ink);
}

.host-status-unknown {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-secondary);
}

.host-status-sync {
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-semibold);
}

.host-status-sync--ok {
  color: var(--sr-role-sage-ink);
}

.host-status-sync--pending {
  color: var(--sr-role-amber-ink);
}

.host-card-actions {
  margin-top: 8px;
  padding-top: 8px;
}
</style>
