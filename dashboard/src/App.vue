<template>
  <QLayout>
    <template #sidebar>
      <div class="sidebar-section">
        <div class="sidebar-section-title">概览</div>
        <NavItem to="/skills" :icon="Zap" label="Skill 列表" />
        <NavItem to="/sync" :icon="RefreshCw" label="Sync 工具" />
        <NavItem to="/projects" :icon="FolderKanban" label="项目组" />
        <NavItem to="/repos" :icon="Package" label="仓库状态" />
      </div>
      <div class="sidebar-divider"></div>
      <div class="sidebar-section">
        <div class="sidebar-section-title">分析</div>
        <NavItem to="/graph" :icon="GitGraph" label="依赖关系图" />
        <NavItem to="/logs" :icon="GitCommit" label="提交记录" />
      </div>
      <div class="sidebar-divider"></div>
      <div class="sidebar-section">
        <div class="sidebar-section-title">开发</div>
        <NavItem to="/playground" :icon="Palette" label="组件实验室" />
      </div>
    </template>

    <template #header>
      <div class="header-content">
        <h1 class="header-title">Agent Skills Dashboard</h1>
        <button class="workspace-chip" :title="workspacePath || '未配置 workspace'" @click="workspaceModalOpen = true">
          <span class="workspace-chip-label">Workspace</span>
          <span class="workspace-chip-value">{{ workspaceLabel }}</span>
        </button>
      </div>
      <div class="header-actions">
        <QButton type="ghost" size="small" :disabled="state.loading" @click="refresh"><RefreshCw :size="14" /> 刷新</QButton>
        <QThemeSwitch />
      </div>
    </template>

    <template #default>
      <CommandPanel />
      <div v-if="isServerDown && !bannerDismissed" class="server-down-banner">
        <div class="server-down-banner-content">
          <span class="server-down-text">后端服务已断开，页面数据可能无法更新。</span>
          <QButton type="ghost" size="small" @click="dismissBanner">忽略</QButton>
        </div>
      </div>
      <div v-if="state.loading" class="loading">加载中...</div>
      <div v-else class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="qqx-page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
        <SkillContextPanel />
        <SkillDetailModal />
        <QToast
          :model-value="toast.state.visible"
          :message="toast.state.message"
          :tint="toast.state.tint"
          :position="toast.state.position"
          :duration="toast.state.duration"
          :action-label="toast.state.actionLabel"
          :closable="true"
          @update:model-value="toast.state.visible = $event"
          @action="toast.onAction()"
        />
      </div>
      <QModal v-model="workspaceModalOpen" title="切换 Workspace" width="560px">
        <div class="workspace-modal-body">
          <div class="workspace-meta">
            <span class="workspace-meta-label">当前 Workspace</span>
            <code class="workspace-meta-value">{{ workspacePath || '未配置' }}</code>
          </div>
          <QInput v-model="workspaceDraft" label="Workspace 路径" placeholder="例如: ~/Code/project_kex/agent-hub-kex" />
          <div v-if="workspaceError" class="workspace-error">{{ workspaceError }}</div>
        </div>
        <template #footer>
          <QButton type="secondary" size="small" @click="workspaceModalOpen = false">取消</QButton>
          <QButton type="primary" size="small" :disabled="workspaceSaving || !workspaceDraft.trim()" @click="submitWorkspaceSwitch">
            {{ workspaceSaving ? '切换中...' : '确认切换' }}
          </QButton>
        </template>
      </QModal>
    </template>
  </QLayout>
</template>

<script setup>
import { onMounted, watch, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Zap, Package, RefreshCw, GitGraph, GitCommit, FolderKanban, Palette } from 'lucide-vue-next'
import QLayout from './components/QLayout.vue'
import QButton from './components/QButton.vue'
import QThemeSwitch from './components/QThemeSwitch.vue'
import NavItem from './components/NavItem.vue'
import SkillContextPanel from './components/SkillContextPanel.vue'
import SkillDetailModal from './components/SkillDetailModal.vue'
import QToast from './components/QToast.vue'
import QModal from './components/QModal.vue'
import QInput from './components/QInput.vue'
import CommandPanel from './components/CommandPanel.vue'
import { useToast } from './composables/useToast.js'
import { useData } from './composables/useData.js'
import { useSyncBridge } from './composables/useSyncBridge.js'
import { useCommands } from './composables/useCommands.js'
import { useServerHealth } from './composables/useServerHealth.js'
import { fetchCurrentWorkspace, switchWorkspace } from './api/index.js'

const toast = useToast()
const { state, loadData, loadExtended, refresh } = useData()
const { isServerDown } = useServerHealth()
const bannerDismissed = ref(false)
const workspaceModalOpen = ref(false)
const workspacePath = ref('')
const workspaceDraft = ref('')
const workspaceSaving = ref(false)
const workspaceError = ref('')

const workspaceLabel = computed(() => {
  if (!workspacePath.value) return '未配置'
  return workspacePath.value.replace(/^\/Users\/[^/]+/i, '~').replace(/^\/home\/[^/]+/i, '~').replace(/^[A-Za-z]:[\\/]+Users[\\/]+[^\\/]+/i, '~')
})

function dismissBanner() {
  bannerDismissed.value = true
}

// Reset dismissed state when server comes back
watch(isServerDown, (down) => {
  if (!down) bannerDismissed.value = false
})
const { loadSyncStatus, forceRefresh } = useSyncBridge()
const router = useRouter()
const { registerCommand, unregisterCommandsBySection } = useCommands()

// Register page navigation commands
registerCommand({ id: 'nav-skills', title: 'Skill 列表', description: '查看所有 Skills', icon: Zap, section: 'navigation', action: () => router.push('/skills') })
registerCommand({ id: 'nav-repos', title: '仓库状态', description: '查看子模块状态', icon: Package, section: 'navigation', action: () => router.push('/repos') })
registerCommand({ id: 'nav-sync', title: 'Sync 工具', description: '管理同步目标与状态', icon: RefreshCw, section: 'navigation', action: () => router.push('/sync') })
registerCommand({ id: 'nav-projects', title: '项目组', description: '管理项目组', icon: FolderKanban, section: 'navigation', action: () => router.push('/projects') })
registerCommand({ id: 'nav-graph', title: '依赖关系图', description: '查看 Skill 依赖图', icon: GitGraph, section: 'navigation', action: () => router.push('/graph') })
registerCommand({ id: 'nav-logs', title: '提交记录', description: '查看 Git 提交历史', icon: GitCommit, section: 'navigation', action: () => router.push('/logs') })
registerCommand({ id: 'nav-playground', title: '组件实验室', description: '浏览所有 UI 组件状态与交互', icon: Palette, section: 'navigation', action: () => router.push('/playground') })

// Register quick action commands
registerCommand({ id: 'action-refresh', title: '刷新数据', description: '刷新所有 Skill 和状态数据', icon: RefreshCw, section: 'action', shortcut: '⌘R', action: () => { refresh(); forceRefresh() } })

// Dynamically register skill search commands
function registerSkillCommands() {
  unregisterCommandsBySection('skill')
  for (const skill of state.skills) {
    const skillName = skill.name
    registerCommand({
      id: `skill-${skillName}`,
      title: skillName,
      description: `${skill.type} - ${(skill.description || '').slice(0, 60)}`,
      icon: Zap,
      section: 'skill',
      action: () => {
        router.push({ path: '/skills', query: { skill: skillName } })
      }
    })
  }
}

// Watch skills data and re-register commands when loaded
watch(() => state.skills.length, () => {
  if (state.skills.length > 0) {
    registerSkillCommands()
  }
})

watch(workspaceModalOpen, (open) => {
  if (open) {
    workspaceDraft.value = workspacePath.value || ''
    workspaceError.value = ''
  }
})

async function loadWorkspace() {
  try {
    const data = await fetchCurrentWorkspace()
    workspacePath.value = data.workspace_path || ''
  } catch {
    workspacePath.value = ''
  }
}

async function submitWorkspaceSwitch() {
  workspaceSaving.value = true
  workspaceError.value = ''
  try {
    const result = await switchWorkspace(workspaceDraft.value.trim())
    workspacePath.value = result.workspace_path || workspaceDraft.value.trim()
    workspaceModalOpen.value = false
    toast.success('Workspace 已切换，正在刷新页面')
    window.location.reload()
  } catch (err) {
    workspaceError.value = err.message || '切换失败'
  } finally {
    workspaceSaving.value = false
  }
}

onMounted(() => {
  loadData().then(() => loadExtended())
  loadSyncStatus() // non-blocking background load for sync badges
  loadWorkspace()
})
</script>

<style>
/* Page transition */
.qqx-page-enter-active,
.qqx-page-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.qqx-page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.qqx-page-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>

<style scoped>
.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-section-title {
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-tertiary);
  padding: var(--qqx-space-md) var(--qqx-space-md) var(--qqx-space-xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sidebar-divider {
  height: 1px;
  background: var(--qqx-border-color);
  margin: var(--qqx-space-sm) var(--qqx-space-md);
}

.header-content {
  display: flex;
  align-items: baseline;
  gap: var(--qqx-space-md);
}

.header-title {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
}

.workspace-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 420px;
  padding: 4px 10px;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-subtle);
  color: var(--qqx-text-primary);
  cursor: pointer;
}

.workspace-chip-label {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
}

.workspace-chip-value {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-modal-body {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-lg);
}

.workspace-meta {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-xs);
}

.workspace-meta-label {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
}

.workspace-meta-value {
  padding: 10px 12px;
  border-radius: var(--qqx-radius-xs);
  background: var(--qqx-bg-subtle);
  color: var(--qqx-text-primary);
  overflow-wrap: anywhere;
}

.workspace-error {
  color: #ef4444;
  font-size: var(--qqx-font-size-small);
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 40vh;
  color: var(--qqx-text-tertiary);
}

.main-content {
  display: flex;
  flex: 1;
  min-height: 0;
}

.main-content > *:first-child {
  flex: 1;
  min-width: 0;
}

.server-down-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  background: var(--qqx-warning-bg, #fff3cd);
  border-bottom: 1px solid var(--qqx-warning-border, #ffc107);
}

.server-down-banner-content {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
}

.server-down-text {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-primary);
}
</style>
