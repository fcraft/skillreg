<template>
  <QLayout>
    <template #sidebar>
      <div class="sidebar-section">
        <div class="sidebar-section-title">概览</div>
        <NavItem to="/skills" :icon="Zap" label="Skill 列表" />
        <NavItem to="/sync" :icon="RefreshCw" label="Sync 工具" />
        <NavItem to="/projects" :icon="FolderKanban" label="项目组" />
        <NavItem to="/repos" :icon="Package" label="仓库状态" />
        <NavItem to="/sources" :icon="PackageSearch" label="NPM 来源" />
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
        <button class="workspace-chip" :title="workspacePath || '未配置 workspace'" :disabled="workspaceLoading || onboardingRequired" @click="workspaceModalOpen = true">
          <span class="workspace-chip-label">Workspace</span>
          <span class="workspace-chip-value">{{ workspaceLabel }}</span>
        </button>
      </div>
      <div class="header-actions">
        <QButton type="ghost" size="small" :disabled="workspaceLoading || onboardingRequired || state.loading" @click="refresh"><RefreshCw :size="14" /> 刷新</QButton>
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
      <div v-if="workspaceLoading" class="loading">正在读取 Workspace...</div>
      <WorkspaceOnboarding
        v-else-if="onboardingRequired"
        @configured="handleWorkspaceConfigured"
        @continue="finishOnboarding"
      />
      <div v-else-if="state.loading" class="loading">加载中...</div>
      <div v-else-if="state.error" class="workspace-data-error" role="alert">
        <strong>无法读取当前 Workspace</strong>
        <span>{{ state.error }}</span>
        <QButton type="secondary" size="small" @click="workspaceModalOpen = true">切换 Workspace</QButton>
      </div>
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
      <QModal v-model="workspaceModalOpen" :title="workspaceCreateCandidate ? '创建新 Workspace' : '切换 Workspace'" width="560px">
        <div v-if="workspaceCreateCandidate" class="workspace-create-confirm">
          <div class="workspace-create-icon"><FolderPlus :size="22" /></div>
          <div class="workspace-create-copy">
            <strong>这个路径还不存在</strong>
            <span>是否在这里创建新的 Workspace？skillreg 将完成目录和 Git 初始化</span>
          </div>
          <code class="workspace-create-path">{{ workspaceCreateCandidate }}</code>
          <div class="workspace-create-details">
            <span>创建 skills/ 和 repos/</span>
            <span>初始化 Git 并生成首个提交</span>
            <span>设为当前 Workspace</span>
          </div>
          <div class="workspace-create-note">只创建本地提交，不会配置 remote 或自动 push</div>
          <div v-if="workspaceError" class="workspace-error">{{ workspaceError }}</div>
        </div>
        <div v-else class="workspace-modal-body">
          <div class="workspace-meta">
            <span class="workspace-meta-label">当前 Workspace</span>
            <code class="workspace-meta-value">{{ workspacePath || '未配置' }}</code>
          </div>
          <div class="workspace-path-row">
            <QInput
              v-model="workspaceDraft"
              class="workspace-path-input"
              label="Workspace 路径"
              placeholder="例如: ~/skills-workspace"
            />
            <QButton
              type="secondary"
              size="small"
              :disabled="workspaceSaving || workspacePicking"
              @click="chooseWorkspaceDirectory"
            >
              <FolderOpen :size="15" />
              {{ workspacePicking ? '选择中...' : '选择文件夹' }}
            </QButton>
          </div>
          <p class="workspace-path-hint">可通过系统文件夹选择器定位已有 Workspace，也可手动输入路径</p>
          <div v-if="workspaceError" class="workspace-error">{{ workspaceError }}</div>
        </div>
        <template #footer>
          <template v-if="workspaceCreateCandidate">
            <QButton type="secondary" size="small" :disabled="workspaceSaving" @click="cancelWorkspaceCreate">返回修改</QButton>
            <QButton type="primary" size="small" :disabled="workspaceSaving" @click="confirmWorkspaceCreate">
              {{ workspaceSaving ? '创建中...' : '确认创建' }}
            </QButton>
          </template>
          <template v-else>
            <QButton type="secondary" size="small" @click="workspaceModalOpen = false">取消</QButton>
            <QButton type="primary" size="small" :disabled="workspaceSaving || !workspaceDraft.trim()" @click="submitWorkspaceSwitch">
              {{ workspaceSaving ? '切换中...' : '确认切换' }}
            </QButton>
          </template>
        </template>
      </QModal>
    </template>
  </QLayout>
</template>

<script setup>
import { onMounted, watch, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Zap, Package, PackageSearch, RefreshCw, GitGraph, GitCommit, FolderKanban, Palette, FolderPlus, FolderOpen } from 'lucide-vue-next'
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
import WorkspaceOnboarding from './components/WorkspaceOnboarding.vue'
import { useToast } from './composables/useToast.js'
import { useData } from './composables/useData.js'
import { useSyncBridge } from './composables/useSyncBridge.js'
import { useCommands } from './composables/useCommands.js'
import { useServerHealth } from './composables/useServerHealth.js'
import { createWorkspace, fetchCurrentWorkspace, selectWorkspaceDirectory, switchWorkspace } from './api/index.js'

const toast = useToast()
const { state, loadData, loadExtended, refresh } = useData()
const { isServerDown } = useServerHealth()
const bannerDismissed = ref(false)
const workspaceModalOpen = ref(false)
const workspacePath = ref('')
const workspaceDraft = ref('')
const workspaceSaving = ref(false)
const workspacePicking = ref(false)
const workspaceError = ref('')
const workspaceCreateCandidate = ref('')
const workspaceLoading = ref(true)
const onboardingRequired = ref(false)

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
const { registerCommand, replaceCommandsBySection } = useCommands()

const navigationCommands = [
  { id: 'nav-skills', title: 'Skill 列表', description: '查看所有 Skills', keywords: ['skill', '技能', '浏览'], icon: Zap, path: '/skills' },
  { id: 'nav-repos', title: '仓库状态', description: '查看子模块状态', keywords: ['repo', 'repository', 'submodule', '子模块'], icon: Package, path: '/repos' },
  { id: 'nav-sources', title: 'NPM 来源', description: '检查和更新 NPM 来源', keywords: ['npm', 'source', '来源', '更新'], icon: PackageSearch, path: '/sources' },
  { id: 'nav-sync', title: 'Sync 工具', description: '管理同步目标与状态', keywords: ['同步', '安装', 'target', '目标'], icon: RefreshCw, path: '/sync' },
  { id: 'nav-projects', title: '项目组', description: '管理项目组', keywords: ['project', '分组'], icon: FolderKanban, path: '/projects' },
  { id: 'nav-graph', title: '依赖关系图', description: '查看 Skill 依赖图', keywords: ['graph', '依赖', '关系', '拓扑'], icon: GitGraph, path: '/graph' },
  { id: 'nav-logs', title: '提交记录', description: '查看 Git 提交历史', keywords: ['git', 'log', 'history', '历史'], icon: GitCommit, path: '/logs' },
  { id: 'nav-playground', title: '组件实验室', description: '浏览所有 UI 组件状态与交互', keywords: ['playground', 'ui', '组件'], icon: Palette, path: '/playground' },
]

for (const command of navigationCommands) {
  const { path, ...definition } = command
  registerCommand({
    ...definition,
    section: 'navigation',
    action: () => router.push(path),
  })
}

registerCommand({
  id: 'action-refresh',
  title: '刷新数据',
  description: '刷新所有 Skill 和状态数据',
  keywords: ['refresh', 'reload', '重新加载'],
  icon: RefreshCw,
  section: 'action',
  shortcut: '⌘R',
  action: () => { refresh(); forceRefresh() },
})

function registerSkillCommands() {
  const skillCommands = state.skills.map((skill) => {
    const skillName = skill.name
    const summary = (skill.description || '').slice(0, 100)
    const repository = (skill.submodulePath || '').replace(/^repos\//, '')
    return {
      id: `skill-${skillName}`,
      title: skillName,
      description: summary ? `${skill.type} · ${summary}` : skill.type,
      keywords: [
        skill.type,
        skill.path,
        repository,
        skill.type === 'CLI' ? '命令行 工具' : '参考 文档',
      ],
      icon: Zap,
      action: () => {
        router.push({ path: '/skills', query: { skill: skillName } })
      },
    }
  })
  replaceCommandsBySection('skill', skillCommands)
}

watch(() => state.skills, registerSkillCommands, { immediate: true })

watch(workspaceModalOpen, (open) => {
  if (open) {
    workspaceDraft.value = workspacePath.value || ''
    workspaceError.value = ''
    workspaceCreateCandidate.value = ''
    workspacePicking.value = false
  }
})

async function loadWorkspace() {
  try {
    const data = await fetchCurrentWorkspace()
    workspacePath.value = data.workspace_path || ''
    onboardingRequired.value = !data.configured
    if (data.configured) {
      await loadData()
      await loadExtended()
      loadSyncStatus()
    } else {
      state.loading = false
    }
  } catch {
    workspacePath.value = ''
    onboardingRequired.value = true
    state.loading = false
  } finally {
    workspaceLoading.value = false
  }
}

function handleWorkspaceConfigured(result) {
  workspacePath.value = result.workspace_path || ''
}

async function finishOnboarding(destination) {
  onboardingRequired.value = false
  await loadData()
  await loadExtended()
  loadSyncStatus()
  if (destination === 'import') {
    await router.push({ path: '/skills', query: { onboarding: 'import' } })
  } else if (destination === 'target') {
    await router.push({ path: '/sync', query: { onboarding: 'target' } })
  } else {
    await router.push('/skills')
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
    if (
      err.code === 'workspace_not_found'
      || err.status === 404
      || String(err.message).startsWith('Workspace does not exist:')
    ) {
      workspaceCreateCandidate.value = workspaceDraft.value.trim()
      return
    }
    workspaceError.value = err.message || '切换失败'
  } finally {
    workspaceSaving.value = false
  }
}

async function chooseWorkspaceDirectory() {
  workspacePicking.value = true
  workspaceError.value = ''
  try {
    const result = await selectWorkspaceDirectory(workspaceDraft.value.trim() || workspacePath.value)
    if (!result.cancelled && result.path) {
      workspaceDraft.value = result.path
    }
  } catch (err) {
    workspaceError.value = err.code === 'directory_picker_unavailable'
      ? '当前环境无法打开系统文件夹选择器，请手动输入路径'
      : (err.message || '文件夹选择器打开失败')
  } finally {
    workspacePicking.value = false
  }
}

function cancelWorkspaceCreate() {
  workspaceCreateCandidate.value = ''
  workspaceError.value = ''
}

async function confirmWorkspaceCreate() {
  const candidate = workspaceCreateCandidate.value
  if (!candidate) return
  workspaceSaving.value = true
  workspaceError.value = ''
  try {
    const result = await createWorkspace(candidate)
    workspacePath.value = result.workspace_path || candidate
    workspaceModalOpen.value = false
    toast.success(`Workspace 已创建 · 初始提交 ${result.initial_commit || '已完成'}`)
    window.location.reload()
  } catch (err) {
    workspaceError.value = err.message || '创建失败'
  } finally {
    workspaceSaving.value = false
  }
}

onMounted(() => {
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

.workspace-chip:disabled {
  cursor: default;
  opacity: 0.7;
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

.workspace-path-row {
  display: flex;
  align-items: flex-end;
  gap: var(--qqx-space-sm);
}

.workspace-path-input {
  flex: 1;
  min-width: 0;
}

.workspace-path-hint {
  margin: calc(var(--qqx-space-lg) * -0.5) 0 0;
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
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
  color: var(--qqx-error);
  font-size: var(--qqx-font-size-small);
}

@media (max-width: 600px) {
  .workspace-path-row {
    align-items: stretch;
    flex-wrap: wrap;
  }

  .workspace-path-input {
    flex-basis: 100%;
  }
}

.workspace-create-confirm {
  display: grid;
  justify-items: center;
  gap: var(--qqx-space-lg);
  text-align: center;
}

.workspace-create-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
}

.workspace-create-copy {
  display: grid;
  gap: var(--qqx-space-xs);
}

.workspace-create-copy strong {
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-title);
}

.workspace-create-copy span,
.workspace-create-note {
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-caption);
  line-height: 1.6;
}

.workspace-create-path {
  width: 100%;
  padding: var(--qqx-space-md);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  background: var(--qqx-bg-subtle);
  color: var(--qqx-text-primary);
  overflow-wrap: anywhere;
  text-align: left;
}

.workspace-create-details {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  width: 100%;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  overflow: hidden;
}

.workspace-create-details span {
  padding: var(--qqx-space-md);
  border-right: 1px solid var(--qqx-border-color);
  background: var(--qqx-bg-surface);
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  line-height: 1.5;
}

.workspace-create-details span:last-child {
  border-right: 0;
}

@media (max-width: 767px) {
  .workspace-create-details {
    grid-template-columns: 1fr;
  }

  .workspace-create-details span {
    border-right: 0;
    border-bottom: 1px solid var(--qqx-border-color);
  }

  .workspace-create-details span:last-child {
    border-bottom: 0;
  }
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

.workspace-data-error {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--qqx-space-md);
  max-width: 640px;
  margin: var(--qqx-space-3xl) auto;
  padding: var(--qqx-space-xl);
  border: 1px solid color-mix(in srgb, var(--qqx-error) 30%, transparent);
  border-radius: var(--qqx-radius-lg);
  background: var(--qqx-error-light);
  color: var(--qqx-text-primary);
}

.workspace-data-error span {
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-caption);
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
