<template>
  <div class="ssh-sync-panel">
    <!-- Empty state -->
    <div v-if="!host" class="sync-panel-empty">
      <span class="sync-panel-empty-text">选择一台主机查看同步详情</span>
    </div>

    <template v-else>
      <!-- Toolbar -->
      <div class="sync-panel-toolbar">
        <div class="sync-panel-toolbar-left">
          <span class="sync-panel-host-id">{{ host.id }}</span>
          <span class="sync-panel-host-addr">· {{ host.hostname }}</span>
          <span class="sync-panel-meta">
            路径: {{ host.agentHubPath || '~/agent-hub' }}
            <span v-if="lastCheckTime"> · 最后检查: {{ lastCheckTime }}</span>
          </span>
        </div>
        <div class="sync-panel-toolbar-actions">
          <QButton type="ghost" size="small" :disabled="loading" @click="$emit('refresh')">
            <RefreshCw :size="14" :class="{ 'icon-spin': loading }" /> 刷新状态
          </QButton>
          <QButton type="primary" size="small" :disabled="loading || syncing" @click="$emit('sync')">
            <RefreshCw :size="14" /> {{ syncing ? '同步中...' : '同步' }}
          </QButton>
        </div>
      </div>

      <!-- No agent-hub: show install -->
      <div v-if="checkResult && checkResult.reason === 'no_agent_hub' && !installing" class="sync-panel-install">
        <div class="sync-panel-install-icon">📦</div>
        <div class="sync-panel-install-title">远程主机未安装 agent-hub</div>
        <div class="sync-panel-install-detail">{{ checkResult.detail }}</div>
        <div class="sync-panel-install-detail">仓库: {{ host.repoUrl || '(从本地 origin 获取)' }}</div>
        <QButton type="primary" size="medium" :disabled="installing" @click="$emit('install')">
          <Rocket :size="14" /> 一键安装 agent-hub
        </QButton>
        <div class="sync-panel-install-hint">将自动 clone 仓库并运行 bootstrap.sh</div>
      </div>

      <!-- Loading -->
      <div v-else-if="loading || installing" class="sync-panel-loading">
        {{ installing ? '正在安装 agent-hub...（clone + bootstrap，可能需要几分钟）' : '正在获取远程同步状态...' }}
      </div>

      <!-- Error -->
      <div v-else-if="error" class="sync-panel-error">
        <div class="sync-panel-error-title">连接失败</div>
        <div class="sync-panel-error-detail">{{ error }}</div>
        <QButton type="secondary" size="small" @click="$emit('refresh')">重试</QButton>
      </div>

      <!-- Content -->
      <template v-else-if="statusData">
        <!-- Target status -->
        <div v-if="targets.length" class="sync-section">
          <div class="sync-section-title">Target 同步状态</div>
          <div v-for="t in targets" :key="t.name" class="sync-target-row">
            <span :class="['sync-target-dot', targetDotClass(t.status)]" />
            <span class="sync-target-name">{{ t.name }}</span>
            <span class="sync-target-status">{{ targetStatusLabel(t) }}</span>
            <span class="sync-target-count">{{ t.skillCount || 0 }}/{{ t.totalCount || 0 }} skills</span>
          </div>
        </div>

        <!-- Skill list -->
        <div v-if="skills.length" class="sync-section">
          <div class="sync-section-title">Skill 清单</div>
          <div class="sync-skill-table">
            <div class="sync-skill-header">
              <span class="sync-skill-col sync-skill-col--name">skill</span>
              <span class="sync-skill-col sync-skill-col--version">版本</span>
              <span class="sync-skill-col sync-skill-col--source">来源</span>
              <span class="sync-skill-col sync-skill-col--status">状态</span>
            </div>
            <div v-for="s in skills" :key="s.name" class="sync-skill-row">
              <span class="sync-skill-col sync-skill-col--name">{{ s.name }}</span>
              <span class="sync-skill-col sync-skill-col--version">{{ s.version || '-' }}</span>
              <span class="sync-skill-col sync-skill-col--source">{{ s.source || '-' }}</span>
              <span class="sync-skill-col sync-skill-col--status">
                <span :class="['sync-skill-status', `sync-skill-status--${s.status || 'unknown'}`]">
                  {{ skillStatusLabel(s.status) }}
                </span>
              </span>
            </div>
          </div>
        </div>

        <!-- Raw output fallback -->
        <div v-if="rawOutput && !targets.length && !skills.length" class="sync-raw-output">
          <pre>{{ rawOutput }}</pre>
        </div>
      </template>

      <!-- No status data yet -->
      <div v-else class="sync-panel-empty">
        <span class="sync-panel-empty-text">点击「刷新状态」查看远程同步信息</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RefreshCw, Rocket } from 'lucide-vue-next'
import QButton from '../QButton.vue'

const props = defineProps({
  host: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  syncing: { type: Boolean, default: false },
  installing: { type: Boolean, default: false },
  error: { type: String, default: '' },
  statusData: { type: Object, default: null },
  checkResult: { type: Object, default: null },  // { ok, reason, detail }
})

defineEmits(['refresh', 'sync', 'install'])

const lastCheckTime = computed(() => {
  return props.statusData ? '刚刚' : null
})

// Parse sync-skills.py --status output
const targets = computed(() => {
  if (!props.statusData?.output) return []
  const lines = props.statusData.output.split('\n')
  const result = []
  let currentTarget = null

  for (const line of lines) {
    const targetMatch = line.match(/^(?:Target:\s*)?(\.\S+?\/\S+)/)
    if (targetMatch) {
      if (currentTarget) result.push(currentTarget)
      currentTarget = { name: targetMatch[1], status: 'ok', skillCount: 0, totalCount: 0 }
      continue
    }
    if (currentTarget) {
      const skillMatch = line.match(/^\s*\[(\w+)\]/)
      if (skillMatch) {
        currentTarget.totalCount++
        if (skillMatch[1] === 'unchanged') currentTarget.skillCount++
      }
    }
  }
  if (currentTarget) result.push(currentTarget)
  return result
})

const skills = computed(() => {
  if (!props.statusData?.output) return []
  const lines = props.statusData.output.split('\n')
  const result = []

  for (const line of lines) {
    const match = line.match(/^\s*\[(\w+)\]\s+(.+?)(?:\s+)?$/)
    if (match) {
      const status = match[1]
      let name = match[2].trim()
      let version = ''
      let source = ''

      const versionMatch = name.match(/^(.+?)\s+\(v([\d.]+)\)/)
      if (versionMatch) {
        name = versionMatch[1]
        version = versionMatch[2]
      }

      const sourceMatch = line.match(/from\s+(\S+)/)
      if (sourceMatch) source = sourceMatch[1]

      result.push({ name, version, source, status })
    }
  }

  return result
})

const rawOutput = computed(() => {
  return props.statusData?.output || ''
})

function targetDotClass(status) {
  if (status === 'ok') return 'sync-target-dot--ok'
  if (status === 'pending' || status === 'updated') return 'sync-target-dot--pending'
  return 'sync-target-dot--error'
}

function targetStatusLabel(t) {
  if (t.status === 'ok' && t.skillCount === t.totalCount) return '已同步'
  if (t.skillCount < t.totalCount) return `${t.totalCount - t.skillCount} 待同步`
  return t.status
}

function skillStatusLabel(status) {
  const map = { unchanged: 'unchanged', updated: 'updated', new: 'new', missing: 'missing', dirty: 'dirty' }
  return map[status] || status || 'unknown'
}
</script>

<style scoped>
.ssh-sync-panel {
  margin-top: 24px;
  background: var(--qqx-bg-card, #fff);
  border: 1px solid var(--qqx-border-color, #e7eaee);
  border-radius: 12px;
  overflow: hidden;
}

.sync-panel-empty {
  text-align: center;
  padding: 40px 20px;
}

.sync-panel-empty-text {
  font-size: 14px;
  color: var(--qqx-text-secondary);
}

/* Toolbar */
.sync-panel-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--qqx-border-color, #e7eaee);
  flex-wrap: wrap;
  gap: 8px;
}

.sync-panel-toolbar-left {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.sync-panel-host-id {
  font-size: 18px;
  font-weight: 600;
  color: var(--qqx-text-primary);
  font-family: Inter, system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.sync-panel-host-addr {
  font-size: 12px;
  color: var(--qqx-text-secondary);
}

.sync-panel-meta {
  font-size: 12px;
  color: var(--qqx-text-secondary);
}

.sync-panel-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Loading / Error */
/* Install state */
.sync-panel-install {
  text-align: center;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.sync-panel-install-icon {
  font-size: 36px;
  margin-bottom: 4px;
}

.sync-panel-install-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--qqx-text-primary);
}

.sync-panel-install-detail {
  font-size: 13px;
  color: var(--qqx-text-secondary);
  max-width: 420px;
}

.sync-panel-install-hint {
  font-size: 11px;
  color: var(--qqx-text-secondary);
  margin-top: 4px;
}

.sync-panel-loading {
  text-align: center;
  padding: 40px 20px;
  font-size: 14px;
  color: var(--qqx-text-secondary);
}

.sync-panel-error {
  text-align: center;
  padding: 24px;
}

.sync-panel-error-title {
  font-size: 14px;
  font-weight: 600;
  color: #e53e3e;
  margin-bottom: 4px;
}

.sync-panel-error-detail {
  font-size: 12px;
  color: var(--qqx-text-secondary);
  margin-bottom: 12px;
}

/* Section */
.sync-section {
  padding: var(--qqx-space-lg) var(--qqx-space-xl);
}

.sync-section + .sync-section {
  border-top: 1px solid var(--qqx-border-color, #e7eaee);
}

.sync-section-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--qqx-text-primary);
  margin-bottom: 10px;
  font-family: Inter, system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
}

/* Target row */
.sync-target-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid var(--qqx-border-color);
  border-radius: 8px;
  margin-bottom: 6px;
  font-size: 13px;
}

.sync-target-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--qqx-text-secondary);
}
.sync-target-dot--ok { background: #22c55e; }
.sync-target-dot--pending { background: #f59e0b; }
.sync-target-dot--error { background: #e53e3e; }

.sync-target-name {
  color: var(--qqx-text-primary);
  font-weight: 500;
  font-family: monospace;
  font-size: 12px;
}

.sync-target-status {
  color: var(--qqx-text-secondary);
  margin-left: auto;
}

.sync-target-count {
  color: var(--qqx-text-secondary);
  font-size: 12px;
}

/* Skill table */
.sync-skill-table {
  border: 1px solid var(--qqx-border-color);
  border-radius: 8px;
  overflow: hidden;
}

.sync-skill-header,
.sync-skill-row {
  display: grid;
  grid-template-columns: 2fr 0.8fr 1fr 1fr;
  gap: 8px;
  padding: 8px 12px;
  font-size: 12px;
  align-items: center;
}

.sync-skill-header {
  background: var(--qqx-bg-subtle, #f8f9fa);
  font-weight: 500;
  color: var(--qqx-text-secondary);
  border-bottom: 1px solid var(--qqx-border-color);
}

.sync-skill-row {
  border-bottom: 1px solid var(--qqx-border-color);
  color: var(--qqx-text-primary);
  font-family: Inter, system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.sync-skill-row:last-child { border-bottom: none; }

.sync-skill-col--name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sync-skill-status { font-weight: 500; }
.sync-skill-status--unchanged { color: #22c55e; }
.sync-skill-status--updated { color: #f59e0b; }
.sync-skill-status--new { color: #0099ff; }
.sync-skill-status--missing { color: #e53e3e; }
.sync-skill-status--dirty { color: #f59e0b; }
.sync-skill-status--unknown { color: var(--qqx-text-secondary); }

/* Raw output */
.sync-raw-output {
  padding: 16px 20px;
}
.sync-raw-output pre {
  font-size: 12px;
  color: var(--qqx-text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

/* Spin animation */
.icon-spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
