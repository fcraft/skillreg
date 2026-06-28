<template>
  <div class="remote-sync-view">
    <div class="rsv-header">
      <div class="rsv-header-left">
        <h2 class="rsv-title">远程 Sync 管理</h2>
        <span class="rsv-host">{{ activeHost?.id }}</span>
        <span class="rsv-path">{{ activeHost?.agentHubPath }}</span>
      </div>
      <div class="rsv-header-actions">
        <QButton type="ghost" size="small" :disabled="remoteLoading" @click="loadRemoteStatus()">
          <RefreshCw :size="14" :class="{ 'icon-spin': remoteLoading }" /> 刷新
        </QButton>
        <QButton type="primary" size="small" :disabled="remoteLoading || syncing" @click="handleSyncAll()">
          <RefreshCw :size="14" /> {{ syncing ? '同步中...' : '全部同步' }}
        </QButton>
      </div>
    </div>

    <div v-if="remoteLoading && !targets.length" class="rsv-loading">加载远程同步状态...</div>

    <div v-else-if="!targets.length" class="rsv-empty">
      <QCard empty>
        <div class="rsv-empty-content">
          <p>远程主机未配置同步目标</p>
          <p class="rsv-empty-hint">在远程 sync-skills.json 中添加 target 后即可管理</p>
        </div>
      </QCard>
    </div>

    <template v-else>
      <div class="rsv-target-tabs">
        <button
          v-for="t in targets"
          :key="t.name"
          :class="['rsv-target-tab', { 'rsv-target-tab--active': activeTarget === t.name }]"
          @click="activeTarget = t.name"
        >
          <span class="rsv-target-tab-name">{{ t.name }}</span>
          <span class="rsv-target-tab-path">{{ t.path }}</span>
          <span class="rsv-target-tab-count">{{ t.total }} skills</span>
          <span v-if="t.pending" class="rsv-target-tab-pending">{{ t.pending }}</span>
        </button>
      </div>

      <QCard v-if="activeTargetData" class="rsv-target-detail">
        <template #header>
          <div class="rsv-target-header">
            <span class="rsv-target-title">{{ activeTargetData.name }}</span>
            <span class="rsv-target-path">{{ activeTargetData.path }}</span>
            <QButton type="primary" size="small" :disabled="syncing" @click="syncTarget(activeTargetData.name)">
              <RefreshCw :size="14" /> 同步此 Target
            </QButton>
          </div>
        </template>

        <div v-if="activeTargetData.skills.length" class="rsv-skills-list">
          <div v-for="s in activeTargetData.skills" :key="s.name" class="rsv-skill-row">
            <span :class="['rsv-skill-dot', skillDotClass(s.status)]" />
            <span class="rsv-skill-name">{{ s.name }}</span>
            <span :class="['rsv-skill-status', skillStatusClass(s.status)]">
              {{ skillStatusLabel(s.status) }}
            </span>
            <QButton type="text" size="small" :disabled="syncing" @click="syncSingleSkill(s.name)" title="同步此 skill">
              <RefreshCw :size="12" :class="{ 'icon-spin': syncing }" />
            </QButton>
          </div>
        </div>
        <div v-else class="rsv-no-skills">此 target 下暂无已安装的 skill — 点击「全部同步」安装</div>
      </QCard>
      <div v-else class="rsv-no-target">选择上方 target 查看详情</div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import QCard from '../QCard.vue'
import QButton from '../QButton.vue'
import { useSshMode } from '../../composables/useSshMode.js'
import { useRemoteData } from '../../composables/useRemoteData.js'

const { activeHost } = useSshMode()
const { remoteLoading, targets, triggerRemoteSync, syncSkillToRemote, loadRemoteStatus } = useRemoteData()

const syncing = ref(false)
const activeTarget = ref(null)

const activeTargetData = computed(() => {
  if (!activeTarget.value) return null
  return targets.value.find(t => t.name === activeTarget.value) || null
})

function skillDotClass(s) {
  if (s === 'unchanged') return 'rsv-skill-dot--ok'
  if (s === 'updated' || s === 'new') return 'rsv-skill-dot--pending'
  return 'rsv-skill-dot--missing'
}
function skillStatusClass(s) {
  if (s === 'unchanged') return 'rsv-skill-status--ok'
  if (s === 'updated' || s === 'new') return 'rsv-skill-status--pending'
  return 'rsv-skill-status--missing'
}
function skillStatusLabel(s) {
  const m = { unchanged: 'unchanged', updated: '待同步', new: '新增', missing: '缺失', dirty: '有改动' }
  return m[s] || s || '未安装'
}

async function handleSyncAll() {
  syncing.value = true
  try { await triggerRemoteSync() } finally { syncing.value = false }
}
async function syncTarget(name) {
  syncing.value = true
  try { await triggerRemoteSync(null, name) } finally { syncing.value = false }
}
async function syncSingleSkill(skillName) {
  syncing.value = true
  try { await syncSkillToRemote(skillName, activeTarget.value) } finally { syncing.value = false }
}
</script>

<style scoped>
.remote-sync-view { margin: 0 auto; }
.rsv-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--qqx-space-xl); }
.rsv-header-left { display: flex; align-items: baseline; gap: var(--qqx-space-md); }
.rsv-title { font-size: var(--qqx-font-size-title); font-weight: var(--qqx-font-semibold); color: var(--qqx-text-primary); margin: 0; }
.rsv-host { font-size: var(--qqx-font-size-label); font-weight: var(--qqx-font-medium); color: var(--qqx-brand); }
.rsv-path { font-size: var(--qqx-font-size-small); color: var(--qqx-text-secondary); font-family: monospace; }
.rsv-header-actions { display: flex; gap: var(--qqx-space-sm); }
.rsv-loading { text-align: center; padding: var(--qqx-space-xl); color: var(--qqx-text-secondary); }
.rsv-empty-content { text-align: center; padding: var(--qqx-space-xl); }
.rsv-empty-content p { font-size: var(--qqx-font-size-body); color: var(--qqx-text-primary); margin: 0 0 var(--qqx-space-sm); }
.rsv-empty-hint { font-size: var(--qqx-font-size-small); color: var(--qqx-text-secondary); }
.rsv-target-tabs { display: flex; gap: 4px; margin-bottom: var(--qqx-space-lg); flex-wrap: wrap; }
.rsv-target-tab { display: flex; align-items: center; gap: var(--qqx-space-sm); padding: var(--qqx-space-sm) var(--qqx-space-md); border: 1px solid var(--qqx-border-color); border-radius: var(--qqx-radius-sm); background: var(--qqx-bg-card); cursor: pointer; transition: all var(--qqx-transition); }
.rsv-target-tab:not(.rsv-target-tab--active):hover { border-color: var(--qqx-brand); }
.rsv-target-tab--active { border-color: var(--qqx-brand); background: color-mix(in srgb, var(--qqx-brand) 6%, transparent); }
.rsv-target-tab-name { font-size: var(--qqx-font-size-label); font-weight: var(--qqx-font-medium); color: var(--qqx-text-primary); }
.rsv-target-tab-path { font-size: var(--qqx-font-size-small); color: var(--qqx-text-secondary); font-family: monospace; }
.rsv-target-tab-count { font-size: var(--qqx-font-size-small); color: var(--qqx-text-secondary); }
.rsv-target-tab-pending { font-size: var(--qqx-font-size-small); font-weight: var(--qqx-font-semibold); color: var(--qqx-text-primary); background: var(--qqx-warning, #f59e0b); border-radius: var(--qqx-radius-full); padding: 1px 7px; min-width: 18px; text-align: center; }
.rsv-target-header { display: flex; align-items: center; gap: var(--qqx-space-md); width: 100%; }
.rsv-target-title { font-size: var(--qqx-font-size-label); font-weight: var(--qqx-font-medium); color: var(--qqx-text-primary); }
.rsv-target-path { font-size: var(--qqx-font-size-small); color: var(--qqx-text-secondary); font-family: monospace; margin-right: auto; }
.rsv-no-target { text-align: center; padding: var(--qqx-space-xl); color: var(--qqx-text-secondary); font-size: var(--qqx-font-size-label); }
.rsv-skills-list { display: flex; flex-direction: column; gap: 2px; }
.rsv-skill-row { display: flex; align-items: center; gap: var(--qqx-space-sm); padding: var(--qqx-space-sm) var(--qqx-space-md); border-bottom: 1px solid var(--qqx-border-color); font-size: var(--qqx-font-size-label); }
.rsv-skill-row:last-child { border-bottom: none; }
.rsv-skill-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.rsv-skill-dot--ok { background: var(--qqx-success, #22c55e); }
.rsv-skill-dot--pending { background: var(--qqx-warning, #f59e0b); }
.rsv-skill-dot--missing { background: var(--qqx-text-secondary); opacity: 0.4; }
.rsv-skill-name { color: var(--qqx-text-primary); flex: 1; }
.rsv-skill-status { font-size: var(--qqx-font-size-small); font-weight: var(--qqx-font-medium); }
.rsv-skill-status--ok { color: var(--qqx-success, #22c55e); }
.rsv-skill-status--pending { color: var(--qqx-warning, #f59e0b); }
.rsv-skill-status--missing { color: var(--qqx-text-secondary); }
.rsv-no-skills { text-align: center; padding: var(--qqx-space-lg); color: var(--qqx-text-secondary); font-size: var(--qqx-font-size-label); }
.icon-spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@media (max-width: 767px) {
  .rsv-header { flex-direction: column; align-items: flex-start; gap: var(--qqx-space-sm); }
  .rsv-header-left { flex-wrap: wrap; }
  .rsv-skill-row { flex-wrap: wrap; }
}
</style>
