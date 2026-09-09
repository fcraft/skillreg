<template>
  <section class="skill-ssh" aria-label="安装到 SSH">
    <div class="skill-ssh-heading">
      <p>选择远端目标后，再检查此 Skill 的安装状态</p>
      <QButton type="ghost" size="small" @click="$emit('manage')">管理连接</QButton>
    </div>
    <QLoadingState v-if="loading">正在加载连接配置…</QLoadingState>
    <div v-if="error" class="ssh-error" role="alert">
      {{ error }}
      <QButton type="text" size="small" @click="run ? refreshRun() : load()">重试</QButton>
    </div>
    <p v-if="!loading && !error && !connections.length">还没有 SSH 连接，先到「管理连接」添加开发机</p>
    <QDisclosure v-for="connection in connections" :id="`skill-ssh-${connection.id}`" :key="connection.id" class="skill-ssh-connection">
      <template #title><span class="skill-ssh-connection-title"><Server :size="16" /><strong>{{ connection.name }}</strong><span>{{ connection.host }}</span></span></template>
      <p v-if="!connectionTargets(connection.id).length">尚未配置安装目标，请到「管理连接」添加 Agent 或项目目录</p>
      <div v-for="target in connectionTargets(connection.id)" :key="target.id" class="skill-ssh-target" :aria-busy="Boolean(rows[target.id]?.loading)">
        <div class="skill-ssh-info">
          <strong>{{ target.name }}</strong>
          <code>{{ target.path }}</code>
          <QLoadingState v-if="rows[target.id]?.loading">正在连接并检查…</QLoadingState>
          <span v-else-if="rows[target.id]?.error" class="ssh-error" role="alert">{{ rows[target.id].error }}</span>
          <span v-else-if="rows[target.id]?.status">{{ statusLabel(rows[target.id].status) }}<small v-if="rows[target.id].observedAt"> · 上次检查 {{ rows[target.id].observedAt }}</small></span>
          <span v-else>尚未检查</span>
        </div>
        <QButton type="secondary" tint="brand" size="small" :disabled="rows[target.id]?.loading || busy || isActiveRun(run)" @click="inspect(target)">
          {{ rows[target.id]?.loading ? '检查中…' : rows[target.id] ? '重新检查' : '检查并安装' }}
        </QButton>
      </div>
    </QDisclosure>
    <QButton v-if="run" type="ghost" size="small" @click="showRun = true">{{ statusLabel(run.state) }} · 查看执行记录</QButton>
    <p class="skill-ssh-note">仅安装 {{ skillName }}，有差异时需确认覆盖；离开详情不会停止已启动的同步</p>
    <SyncPreview :preview="planned" :busy="busy" :error="error" @close="planned = null" @execute="execute" />
    <RunDetails :run="showRun ? run : null" :busy="busy" :error="error" @close="showRun = false" @retry="retry" @cancel="cancel" />
  </section>
</template>

<script setup>
import { Server } from 'lucide-vue-next'
import QButton from '../QButton.vue'
import QDisclosure from '../QDisclosure.vue'
import QLoadingState from '../QLoadingState.vue'
import SyncPreview from './SyncPreview.vue'
import RunDetails from './RunDetails.vue'
import { useSkillSshInstall } from '../../composables/useSkillSshInstall.js'
import { isActiveRun, statusLabel } from '../../sources/remoteSyncState.js'
import '../../styles/remote-sync.css'
const props = defineProps({ skillName: { type: String, required: true } })
defineEmits(['manage'])
const { connections, targets, rows, loading, error, busy, planned, run, showRun, load, inspect, execute, retry, cancel, refreshRun } = useSkillSshInstall(props.skillName)
const connectionTargets = id => targets.value.filter(target => target.connectionId === id)
</script>

<style scoped>
.skill-ssh { display: grid; gap: 16px; font-size: 13px; }
.skill-ssh p { margin: 0; color: var(--qqx-text-secondary); line-height: 1.6; }
.skill-ssh-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.skill-ssh-heading .qqx-btn { flex-shrink: 0; }
.skill-ssh-connection { border: 1px solid var(--qqx-border-color); border-radius: var(--qqx-radius-md); transition: background-color var(--qqx-transition), border-color var(--qqx-transition), transform 150ms ease-out; }
.skill-ssh-connection :deep(.q-disclosure__trigger) { padding: 22px 14px; border-radius: inherit; transform: none; outline-offset: -3px; }
.skill-ssh-connection :deep(.q-disclosure__trigger:hover) { background: transparent; }
.skill-ssh-connection:not(.q-disclosure--open):hover { background: var(--qqx-bg-hover); border-color: var(--qqx-brand); }
.skill-ssh-connection:not(.q-disclosure--open):has(> .q-disclosure__trigger:active) { transform: scale(0.99); transition-duration: 100ms; }
.skill-ssh-connection :deep(.q-disclosure__content) { padding: 0 14px; }
.skill-ssh-connection :deep(.q-disclosure__content > :last-child) { margin-bottom: 14px; }
.skill-ssh-connection-title { display: flex; gap: 8px; align-items: center; }
.skill-ssh-connection-title > span { margin-left: auto; color: var(--qqx-text-secondary); overflow-wrap: anywhere; }
.skill-ssh-target { display: flex; align-items: center; gap: 12px; padding-top: 16px; margin-top: 14px; border-top: 1px solid var(--qqx-border-color); }
.skill-ssh-info { display: grid; gap: 6px; flex: 1; min-width: 0; overflow-wrap: anywhere; }
.skill-ssh-info code, .skill-ssh-info span { font-size: 12px; color: var(--qqx-text-secondary); }
.skill-ssh-info .ssh-error { color: var(--qqx-danger-text, #e53e3e); }
.skill-ssh-note { font-size: 12px; }
@media (max-width: 600px) { .skill-ssh-target { flex-wrap: wrap; } .skill-ssh-info { flex-basis: 100%; } }
@media (prefers-reduced-motion: reduce) {
  .skill-ssh-connection, .skill-ssh-connection:not(.q-disclosure--open):has(> .q-disclosure__trigger:active) { transform: none; transition: background-color 80ms linear, border-color 80ms linear; }
}
</style>
