<template>
  <div class="ssh-page">
    <header class="ssh-row ssh-header"><h2>SSH Skills</h2><div class="ssh-actions"><QButton type="ghost" @click="showHistory">执行记录{{ activeRuns ? ' · ' + activeRuns + ' 进行中' : '' }}</QButton><QButton v-if="activeConnection" type="secondary" @click="settingsOpen = true">设置</QButton></div></header>
    <p v-if="error" class="ssh-error" role="alert">{{ error }}</p><QLoadingState v-if="loading">加载连接和目标…</QLoadingState>
    <div v-else-if="loadError"><p class="ssh-error" role="alert">{{ loadError }}</p><QButton type="secondary" @click="load">重新加载</QButton></div>
    <QCard v-else-if="!connections.length" class="ssh-empty"><Server :size="28" /><h3>连接你的开发机</h3><p class="ssh-muted">使用已有的 SSH Host 别名，选择全局 Agent 或项目内安装目录</p><QButton type="primary" @click="editConnection(null)">添加第一个连接</QButton></QCard>
    <div v-else class="ssh-layout">
      <SshNavigation :connections="connections" :targets="targets" :selected-connection="selectedConnection" :active-target-id="inventory.activeTargetId.value" @connection="selectedConnection = $event" @target="selectTarget" @add="editConnection(null)" />
      <section v-if="activeConnection" class="ssh-workspace">
        <div class="ssh-context"><strong>{{ activeConnection.name }}</strong><code :title="inventoryTarget?.path">{{ inventoryTarget?.path || '选择左侧目录以查看远端 Skills' }}</code><QButton type="text" size="small" @click="addTarget">添加目标</QButton></div>
        <nav class="ssh-view-tabs" aria-label="Skill 管理视图"><button class="q-press" :aria-pressed="view === 'remote'" @click="view = 'remote'">远端 Skills</button><button class="q-press" :aria-pressed="view === 'install'" @click="view = 'install'">从 workspace 安装</button></nav>
        <div v-show="view === 'remote'" class="ssh-remote-panel">
          <TargetInventory v-if="inventoryTarget" :key="inventoryTarget.id" :target="inventoryTarget" :state="inventory.entries.value[inventoryTarget.id]" :source-names="sourceNames" :busy="busy" @refresh="inventory.scan(inventoryTarget)" @preview="previewInventorySkill" />
          <div v-else class="ssh-directory-empty"><Server :size="28" /><h3>{{ connectionTargets.length ? '选择一个目录' : '添加第一个安装目录' }}</h3><p class="ssh-muted">{{ connectionTargets.length ? '按需探测其中的 Skills，读取说明或与 workspace 来源对比' : '发现已有的 Agent 目录，或指定项目内的安装目标' }}</p><QButton v-if="!connectionTargets.length" type="primary" @click="addTarget">添加目标</QButton></div>
        </div>
        <SshInstallPanel v-show="view === 'install'" :skills="state.skills || []" v-model:selected-skills="selectedSkills" :selected-targets="selectedTargets" :targets="connectionTargets" :busy="busy" @targets="installTargetsOpen = true" @preview="preview" />
      </section>
    </div>
    <SshSettings v-model="settingsOpen" :connection="activeConnection" :targets="connectionTargets" :observation-for="observationFor" :busy="busy" :error="actionError" @check="check" @edit="editConnection(activeConnection)" @remove="askRemove" @add-target="addTarget" @add-connection="editConnection(null)" />
    <SshHistory v-model="historyOpen" :runs="runs" :error="error" @refresh="loadHistory" @open="showRun" />
    <InstallTargetSelect v-model="installTargetsOpen" :targets="connectionTargets" :selected="selectedTargets" @apply="selectedTargets = $event" />
    <ConnectionForm v-model="connectionOpen" :connection="editing" @saved="connectionSaved" />
    <TargetPicker v-model="targetOpen" :connection="activeConnection" @saved="targetsSaved" />
    <SyncPreview :preview="planned" :busy="busy" :error="actionError" @close="planned = null" @execute="execute" />
    <p v-if="pollError && !currentRun" class="ssh-error" role="alert">{{ pollError }} · 正在重新获取进度，上次结果会保留</p>
    <RunDetails :run="currentRun" :busy="busy" :error="actionError || pollError" @close="currentRun = null" @retry="retry" @cancel="cancel" />
    <QModal :model-value="Boolean(removing)" title="移除配置" @update:model-value="!$event && (removing = null)"><p>移除 {{ removing?.item.name }} 的配置，已安装的远端文件会保留</p><template #footer><QButton type="secondary" @click="removing = null">取消</QButton><QButton type="primary" :disabled="busy" @click="remove">确认移除</QButton></template></QModal>
  </div>
</template>
<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { Server } from 'lucide-vue-next'
import QButton from '../components/QButton.vue'
import QCard from '../components/QCard.vue'
import QModal from '../components/QModal.vue'
import QLoadingState from '../components/QLoadingState.vue'
import ConnectionForm from '../components/ssh/ConnectionForm.vue'
import TargetPicker from '../components/ssh/TargetPicker.vue'
import SyncPreview from '../components/ssh/SyncPreview.vue'
import RunDetails from '../components/ssh/RunDetails.vue'
import TargetInventory from '../components/ssh/TargetInventory.vue'
import SshNavigation from '../components/ssh/SshNavigation.vue'
import SshInstallPanel from '../components/ssh/SshInstallPanel.vue'
import InstallTargetSelect from '../components/ssh/InstallTargetSelect.vue'
import SshSettings from '../components/ssh/SshSettings.vue'
import SshHistory from '../components/ssh/SshHistory.vue'
import { useRemoteInventory } from '../composables/useRemoteInventory.js'
import { useData } from '../composables/useData.js'
import { useRemoteSync } from '../composables/useRemoteSync.js'
import * as api from '../api/remoteSync.js'
import { isActiveRun } from '../sources/remoteSyncState.js'
import '../styles/remote-sync.css'
import '../styles/ssh-workspace.css'
const { state } = useData()
const { connections, targets, runs, selectedConnection, selectedTargets, selectedSkills, loading, busy, error, actionError, loadError, pollError, load, planned, currentRun, activeConnection, connectionTargets, observationFor, connectionSaved, loadTargets, loadHistory, action, check, preview, previewFor, execute, openRun, retry, cancel } = useRemoteSync()
const connectionOpen = ref(false), editing = ref(null), targetOpen = ref(false), removing = ref(null)
const settingsOpen = ref(false), historyOpen = ref(false), installTargetsOpen = ref(false), view = ref('remote')
const inventory = useRemoteInventory()
const inventoryTarget = computed(() => connectionTargets.value.find(target => target.id === inventory.activeTargetId.value))
const sourceNames = computed(() => new Set((state.skills || []).map(skill => skill.name)))
const activeRuns = computed(() => runs.value.filter(isActiveRun).length)
watch(selectedConnection, () => { inventory.activeTargetId.value = null })
async function selectTarget(target) {
  selectedConnection.value = target.connectionId
  await nextTick()
  selectedTargets.value = [target.id]
  inventory.open(target)
}
async function targetsSaved(added = []) {
  await loadTargets()
  if (added.length) { selectedTargets.value = [added[0].id]; view.value = 'remote'; inventory.added(added) }
}
function previewInventorySkill(name) { if (inventoryTarget.value) previewFor([inventoryTarget.value.id], [name]) }
function editConnection(connection) { settingsOpen.value = false; editing.value = connection; connectionOpen.value = true }
function addTarget() { settingsOpen.value = false; targetOpen.value = true }
function askRemove(kind, item) { settingsOpen.value = false; removing.value = { kind, item } }
function showHistory() { historyOpen.value = true; loadHistory() }
function showRun(run) { historyOpen.value = false; openRun(run) }
async function remove() {
  await action(async () => {
    if (removing.value.kind === 'connection') { await api.removeConnection(removing.value.item.id); connections.value = await api.fetchConnections(); selectedConnection.value = connections.value[0]?.id || '' }
    else { await api.removeTarget(removing.value.item.id); selectedTargets.value = selectedTargets.value.filter(id => id !== removing.value.item.id); await loadTargets() }
    removing.value = null
  })
}
</script>
