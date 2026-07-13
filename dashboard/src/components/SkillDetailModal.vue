<template>
  <QModal v-model="open" width="820px" class="sdm-modal">
    <template #title>
      <div class="sdm-header-row">
        <h2 class="sdm-header-title">{{ skill?.name || 'Skill 详情' }}</h2>
        <QButton v-if="skill" type="ghost" tint="brand" size="small" @click="openFileDrawer()"><FolderOpen :size="14" /> 查看文件</QButton>
        <QButton v-if="skill" type="ghost" tint="brand" size="small" muted :disabled="exporting" @click="handleExport"><Download :size="14" /> 导出</QButton>
      </div>
    </template>
    <div v-if="skill" class="sdm-root">
      <!-- Sidebar tabs (desktop) + Top tabs (tablet/mobile) -->
      <div class="sdm-layout">
        <nav class="sdm-sidebar">
          <button v-for="tab in tabs" :key="tab.key"
            :class="['sdm-sidebar-item', { 'sdm-sidebar-item--active': activeTab === tab.key }]"
            @click="activeTab = tab.key">
            {{ tab.label }}
          </button>
        </nav>
        <div class="sdm-content">
          <QTabs v-model="activeTab" :tabs="tabs" class="sdm-top-tabs" />

      <div class="sdm-tab-panels">
        <Transition name="sdm-tab-fade" mode="out-in">
      <!-- Tab: 详情 -->
      <div v-if="activeTab === 'details'" key="details" class="sdm-tab-content">
        <div class="detail-content">
          <div class="detail-row">
            <span class="detail-label">路径</span>
            <code>{{ skill.path.replace(/^(skills|repos)\//, '') }}</code>
          </div>
          <div class="detail-row">
            <span class="detail-label">类型</span>
            <span class="category-tag">{{ skill.type }}</span>
          </div>
          <div v-if="skill.fileCount" class="detail-row">
            <span class="detail-label">文件数</span>
            <span>{{ skill.fileCount }}</span>
          </div>
          <div v-if="skill.parentSkill" class="detail-row">
            <span class="detail-label">父技能</span>
            <span>{{ skill.parentSkill }}</span>
          </div>
          <div v-if="skill.isSubmodule" class="detail-row">
            <span class="detail-label">子模块</span>
            <code>{{ skill.submodulePath }}</code>
          </div>
          <p v-if="skill.description" class="detail-desc">{{ skill.description }}</p>
        </div>
      </div>

      <!-- Tab: 安装 -->
      <div v-else-if="activeTab === 'install'" key="install" class="sdm-tab-content">
        <div class="im-tabs">
          <button :class="['im-tab', { 'im-tab--active': installSubTab === 'targets' }]" @click="installSubTab = 'targets'">目标</button>
          <button :class="['im-tab', { 'im-tab--active': installSubTab === 'projects' }]" @click="installSubTab = 'projects'">项目组</button>
        </div>

        <!-- Sub Tab: 目标 -->
        <div v-if="installSubTab === 'targets'" class="im-body">
          <div v-if="!targets.length" class="im-empty">暂无配置的目标目录</div>
          <div v-for="t in targets" :key="t.name" class="im-row">
            <div class="im-row-info">
              <span class="im-row-name">{{ t.name }}</span>
              <span class="im-row-path">→ {{ t.path }}/{{ skill.name }}</span>
            </div>
            <QButton v-if="isInstalled(t.path)" type="ghost" size="small" disabled>已安装</QButton>
              <QButton v-else type="secondary" tint="brand" size="small" :disabled="installing" @click="doInstall(t.name)">安装</QButton>
          </div>
        </div>

        <!-- Sub Tab: 项目组 -->
        <div v-if="installSubTab === 'projects'" class="im-body">
          <div v-if="!projects.length" class="im-empty">暂无项目组，在「项目组」页面创建</div>
          <div v-for="p in projects" :key="p.id" class="im-project">
            <div class="im-project-header" @click="expandedProject = expandedProject === p.id ? null : p.id">
              <span class="im-chevron" :class="{ 'im-chevron--open': expandedProject === p.id }">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
              </span>
              <span class="im-project-name">{{ p.name }}</span>
              <span class="im-project-count">{{ p.targets?.length || 0 }} 个目标</span>
              <span v-if="installingProject === p.id" class="im-project-installing">安装中...</span>
            </div>
            <div v-if="expandedProject === p.id" class="im-project-body">
              <div v-for="t in p.targets" :key="t" class="im-target-block">
                <div class="im-target-path" :title="t">{{ t }}</div>
                <div v-if="discoveredMap[t]?.agent_dirs?.length" class="im-agent-list">
                  <div v-for="d in discoveredMap[t].agent_dirs" :key="d.agent" class="im-agent-row">
                    <span class="im-agent-badge">{{ d.agent }}</span>
                    <span class="im-agent-path">→ {{ d.path }}/{{ skill.name }}</span>
                    <QButton v-if="isInstalled(d.path)" type="ghost" size="small" disabled>已安装</QButton>
                      <QButton v-else type="secondary" tint="brand" size="small" :disabled="installing" @click="doInstall(d.path)">安装</QButton>
                  </div>
                </div>
                <div v-else class="im-agent-warn">
                  <TriangleAlert :size="14" />
                  <span>未发现 agent 目录，将安装到根目录: {{ t }}/{{ skill.name }}</span>
                  <QButton v-if="isInstalled(t)" type="ghost" size="small" disabled>已安装</QButton>
                  <QButton v-else type="secondary" tint="brand" size="small" :disabled="installing" @click="doInstall(t)">安装</QButton>
                </div>
              </div>
              <QButton type="primary" size="small" :disabled="installing" @click="doInstallProject(p)" class="im-project-install-all">
                一键安装到全部目标
              </QButton>
            </div>
          </div>
        </div>

        <!-- Custom path -->
        <div class="im-custom">
          <div class="im-custom-label">自定义目录</div>
          <div class="im-custom-row">
            <input v-model="customPath" class="im-custom-input" placeholder="输入目录路径..." @keydown.enter="doInstallCustom" />
            <QButton type="primary" size="small" :disabled="!customPath.trim() || installing" @click="doInstallCustom">安装</QButton>
          </div>
          <div v-if="customPath.trim()" class="im-custom-preview">→ {{ customPath.trim() }}/{{ skill.name }}</div>
        </div>

        <div v-if="installError" class="im-error">{{ installError }}</div>
        <div v-if="installOk" class="im-ok">{{ installOk }}</div>
      </div>

      <!-- Tab: 同步状态 -->
      <div v-else-if="activeTab === 'sync'" key="sync" class="sdm-tab-content">
        <div v-if="!syncState.loaded" class="sync-loading">加载同步状态...</div>
        <div v-else-if="!allTargetsWithStatus.length" class="sync-empty">暂无可用的同步目标</div>
        <div v-else class="sync-list">
          <div v-for="item in allTargetsWithStatus" :key="item.key" class="sync-card">
            <div class="sync-card-header">
              <div class="sync-card-info">
                <span class="sync-card-name">{{ item.label }}</span>
                <span v-if="item._projectName" class="sync-card-project">{{ item._projectName }}</span>
              </div>
              <span class="sync-badge" :class="'sync-badge--' + item.status">{{ statusLabel(item.status) }}</span>
            </div>
            <div class="sync-card-path" :title="item.path">{{ item.path }}</div>
            <div class="sync-card-actions">
              <QButton
                v-if="item.status === 'changed' || item.status === 'missing'"
                type="secondary" tint="brand" size="small"
                :disabled="syncingTarget === item.key"
                @click="doSyncTarget(item)"
              >
                {{ syncingTarget === item.key ? '同步中...' : '同步' }}
              </QButton>
              <QButton
                v-if="item.status === 'not-installed'"
                type="secondary" tint="brand" size="small"
                :disabled="syncingTarget === item.key"
                @click="doSyncTarget(item)"
              >
                {{ syncingTarget === item.key ? '安装中...' : '安装' }}
              </QButton>
              <QButton
                v-if="item.status === 'changed' || item.status === 'unchanged'"
                type="ghost" size="small"
                @click="openDiff(item)"
              >Diff</QButton>
            </div>
          </div>
        </div>

        <!-- Diff Modal (nested) -->
        <QModal v-model="showDiff" :title="`${diffSkill} → ${diffTargetLabel}`" width="900px">
          <div v-if="diffLoading" class="sync-loading">加载差异...</div>
          <div v-else-if="diffError" class="im-error">{{ diffError }}</div>
          <div v-else>
            <template v-if="selectedDiffFile">
              <div class="diff-file-nav">
                <QButton type="text" size="small" @click="closeFilePreview">返回文件列表</QButton>
                <code class="diff-file-nav-path">{{ selectedDiffFile }}</code>
              </div>
              <div v-if="previewLoading" class="sync-loading">加载文件内容...</div>
              <div v-else-if="previewError" class="im-error">{{ previewError }}</div>
              <QDiffViewer v-else
                :repo-content="previewSource"
                :target-content="previewTarget"
                :file-path="selectedDiffFile" />
            </template>
            <template v-else>
              <div class="diff-summary">
                <span v-if="diffSummary.unchanged" class="diff-stat unchanged">{{ diffSummary.unchanged }} unchanged</span>
                <span v-if="diffSummary.added" class="diff-stat added">{{ diffSummary.added }} added</span>
                <span v-if="diffSummary.modified" class="diff-stat modified">{{ diffSummary.modified }} modified</span>
                <span v-if="diffSummary.removed" class="diff-stat removed">{{ diffSummary.removed }} removed</span>
              </div>
              <div v-if="diffHasChanges" class="diff-file-list">
                <div v-for="file in diffChangedFiles" :key="file.path"
                  class="diff-file-row" :class="file.status"
                  @click="openFilePreview(file)">
                  <span class="diff-file-status">{{ file.status }}</span>
                  <code class="diff-file-path">{{ file.path }}</code>
                </div>
              </div>
              <div v-else-if="diffFiles.length" class="diff-all-unchanged">
                所有 {{ diffSummary.unchanged }} 个文件内容一致，无差异
              </div>
              <div v-else class="sync-empty">目标目录中无此 skill</div>
            </template>
          </div>
        </QModal>
        </div>
        </Transition>
      </div>
    </div>
    </div>
    </div>

    <div v-if="!skill" class="sync-empty">未找到 Skill 信息</div>

    <SkillDetailDrawer
      :skill="skill"
      :open="state.fileDrawerOpen"
      @close="closeFileDrawer()"
    />
  </QModal>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { FolderOpen, TriangleAlert, Download } from 'lucide-vue-next'
import QModal from './QModal.vue'
import QButton from './QButton.vue'
import QDiffViewer from './QDiffViewer.vue'
import SkillDetailDrawer from './SkillDetailDrawer.vue'
import { useSkillDetail } from '../composables/useSkillDetail.js'
import { useSyncBridge } from '../composables/useSyncBridge.js'
import { useToast } from '../composables/useToast.js'
import {
  executeSync, fetchProjects, fetchDiscover,
  fetchSkillDiff, fetchSkillFile, fetchTargetFile,
  exportSkill,
} from '../api/index.js'

const { state, close, openFileDrawer, closeFileDrawer } = useSkillDetail()
const { state: syncState, loadSyncStatus, getSkillTargetStatus, refreshSkill } = useSyncBridge()
const toast = useToast()

const skill = computed(() => state.skill)
const activeTab = computed({
  get: () => state.activeTab,
  set: (v) => { state.activeTab = v },
})

const open = computed({
  get: () => state.open,
  set: (v) => { if (!v) close() },
})

const tabs = [
  { key: 'details', label: '详情' },
  { key: 'install', label: '安装' },
  { key: 'sync', label: '同步状态' },
]

// ── Install state ──
const installing = ref(false)
const syncingTarget = ref(null)
const installError = ref('')
const installOk = ref('')
const customPath = ref('')
const installSubTab = ref('targets')
const projects = ref([])
const expandedProject = ref(null)
const installingProject = ref(null)
const discoveredMap = ref({})

// ── Install: computed from sync bridge ──
const targets = computed(() => syncState.targets || [])

// ── Sync status computed ──
const targetStatusMap = computed(() => {
  if (!skill.value) return {}
  return getSkillTargetStatus(skill.value.name)
})

const allTargetsWithStatus = computed(() => {
  const result = []
  const statusMap = targetStatusMap.value
  // Named targets
  for (const t of syncState.targets) {
    result.push({
      key: t.name,
      label: t.name,
      path: t.path,
      _project: false,
      status: statusMap[t.path] || 'not-installed',
    })
  }
  // Project targets
  for (const t of syncState.projectTargets) {
    result.push({
      key: t.name,
      label: t.name.split('/').pop() || t.name,
      path: t.path || t.name,
      _project: true,
      _projectName: t._projectName,
      status: statusMap[t.name] || 'not-installed',
    })
  }
  return result
})

function isInstalled(targetKey) {
  const s = targetStatusMap.value[targetKey]
  return s === 'unchanged' || s === 'changed'
}

function statusLabel(status) {
  const map = {
    'unchanged': '已同步',
    'changed': '有变更',
    'missing': '缺失',
    'not-installed': '未安装',
    'configured': '已配置',
  }
  return map[status] || status
}

// ── Install: watch for tab switch to lazy-load ──
watch(() => state.activeTab, async (tab) => {
  if (tab === 'install' || tab === 'sync') {
    if (!syncState.loaded) {
      await loadSyncStatus()
    }
  }
  if (tab === 'install') {
    // Reset install state
    installError.value = ''
    installOk.value = ''
    installSubTab.value = 'targets'
    expandedProject.value = null
    customPath.value = ''
    discoveredMap.value = {}
    loadProjects()
  }
  if (tab === 'sync') {
    // Lightweight per-skill refresh — only updates this skill's status entries
    refreshSkill(skill.value.name)
  }
})

// ── Install: project loading ──
async function loadProjects() {
  try {
    projects.value = await fetchProjects()
    const allTargets = projects.value.flatMap(p => p.targets || [])
    await Promise.allSettled(allTargets.map(t => fetchDiscoverForTarget(t)))
  } catch { /* silently ignore */ }
}

async function fetchDiscoverForTarget(targetPath) {
  try {
    const data = await fetchDiscover(targetPath)
    discoveredMap.value[targetPath] = data
  } catch { /* silently ignore */ }
}

// ── Export state ──
const exporting = ref(false)

async function handleExport() {
  if (exporting.value) return
  exporting.value = true
  try { await exportSkill(skill.value.name) } catch (e) { console.error('Export failed:', e) }
  finally { exporting.value = false }
}

// ── Install: actions ──
async function doInstall(target) {
  installing.value = true
  installError.value = ''
  installOk.value = ''
  try {
    await executeSync(target, { skills: [skill.value.name] })
    installOk.value = `已安装到 ${target}`
    setTimeout(() => { installOk.value = '' }, 2000)
    refreshSkill(skill.value.name)
    toast.success(`已安装 ${skill.value.name} → ${target}`)
  } catch (e) {
    installError.value = e.message || '安装失败'
  } finally {
    installing.value = false
  }
}

async function doSyncTarget(item) {
  syncingTarget.value = item.key
  installError.value = ''
  try {
    await executeSync(item.key, { skills: [skill.value.name] })
    refreshSkill(skill.value.name)
    toast.success(`${skill.value.name} → ${item.label} 同步完成`)
  } catch (e) {
    installError.value = e.message || '同步失败'
  } finally {
    syncingTarget.value = null
  }
}

async function doInstallProject(proj) {
  const targets = proj.targets || []
  if (!targets.length) return
  installing.value = true
  installingProject.value = proj.id
  installError.value = ''
  installOk.value = ''
  const errors = []
  for (const t of targets) {
    try {
      await executeSync(t, { skills: [skill.value.name] })
    } catch (e) {
      errors.push(`${t}: ${e.message || '失败'}`)
    }
  }
  if (errors.length) {
    installError.value = `${errors.length}/${targets.length} 个目标失败: ${errors.join('; ')}`
  } else {
    installOk.value = `已安装到 ${proj.name}（${targets.length} 个目标）`
    setTimeout(() => { installOk.value = '' }, 2000)
    toast.success(`已安装 ${skill.value.name} → ${proj.name}（${targets.length} 个目标）`)
  }
  installing.value = false
  installingProject.value = null
  refreshSkill(skill.value.name)
}

async function doInstallCustom() {
  const path = customPath.value.trim()
  if (!path) return
  installing.value = true
  installError.value = ''
  installOk.value = ''
  try {
    await executeSync(path, { skills: [skill.value.name] })
    installOk.value = `已安装到 ${path}`
    setTimeout(() => { installOk.value = ''; customPath.value = '' }, 2000)
    refreshSkill(skill.value.name)
    toast.success(`已安装 ${skill.value.name} → ${path}`)
  } catch (e) {
    installError.value = e.message || '安装失败'
  } finally {
    installing.value = false
  }
}

// ── Diff state ──
const showDiff = ref(false)
const diffSkill = ref('')
const diffTarget = ref('')
const diffTargetLabel = ref('')
const diffFiles = ref([])
const diffSummary = ref({})
const diffLoading = ref(false)
const diffError = ref(null)
const selectedDiffFile = ref(null)
const previewSource = ref('')
const previewTarget = ref('')
const previewLoading = ref(false)
const previewError = ref('')

const diffHasChanges = computed(() => {
  return diffSummary.value.added > 0 || diffSummary.value.modified > 0 || diffSummary.value.removed > 0
})

const diffChangedFiles = computed(() => {
  return diffFiles.value.filter(f => f.status !== 'unchanged')
})

function openDiff(item) {
  showDiff.value = true
  diffSkill.value = skill.value.name
  diffTarget.value = item.key
  diffTargetLabel.value = item._project ? `${item._projectName || ''}/${item.label}` : item.label
  diffLoading.value = true
  diffError.value = null
  diffFiles.value = []
  diffSummary.value = {}
  selectedDiffFile.value = null
  previewSource.value = ''
  previewTarget.value = ''
  previewError.value = ''
  fetchSkillDiff(skill.value.name, item.key)
    .then(data => {
      diffFiles.value = data.files || []
      diffSummary.value = data.summary || {}
    })
    .catch(e => { diffError.value = e.message })
    .finally(() => { diffLoading.value = false })
}

async function openFilePreview(file) {
  selectedDiffFile.value = file.path
  previewLoading.value = true
  previewError.value = ''
  try {
    const skillName = diffSkill.value
    const targetName = diffTarget.value
    const filePath = file.path

    let repoPromise = Promise.resolve('')
    let targetPromise = Promise.resolve('')

    if (file.status !== 'removed') {
      repoPromise = fetchSkillFile(skillName, filePath)
        .then(data => data.content || '')
    }
    if (file.status !== 'added') {
      targetPromise = fetchTargetFile(skillName, targetName, filePath)
        .then(data => data.content || '')
    }

    const [repo, target] = await Promise.all([repoPromise, targetPromise])
    previewSource.value = repo
    previewTarget.value = target
  } catch (e) {
    previewError.value = e.message
  } finally {
    previewLoading.value = false
  }
}

function closeFilePreview() {
  selectedDiffFile.value = null
  previewSource.value = ''
  previewTarget.value = ''
  previewError.value = ''
}
</script>

<style scoped>
/* ── Header row (title slot) ── */
.sdm-header-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  flex: 1;
  min-width: 0;
}

.sdm-header-title {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  margin: 0;
}

.sdm-root {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

/* Layout: sidebar + content (desktop) */
.sdm-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: var(--qqx-space-md);
}

.sdm-sidebar {
  width: 140px;
  flex-shrink: 0;
  background: transparent;
  border-right: 1px solid var(--qqx-border-color);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sdm-sidebar-item {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  margin: 0 var(--qqx-space-sm) 0 0;
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--qqx-radius-xs);
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition: color var(--qqx-transition), background-color var(--qqx-transition);
}

.sdm-sidebar-item:not(.sdm-sidebar-item--active):hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-primary);
}

.sdm-sidebar-item:not(.sdm-sidebar-item--active):active {
  transform: scale(0.97);
}

.sdm-sidebar-item--active {
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
  font-weight: var(--qqx-font-semibold);
}

/* Content area */
.sdm-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* Tab panels container — stabilizes height and hosts transition */
.sdm-tab-panels {
  flex: 1;
  min-height: 320px;
  display: flex;
  flex-direction: column;
}

.sdm-tab-content {
  flex: 1;
  min-height: 0;
  padding: var(--qqx-space-md) 0;
}

/* ── Tab switch transition (QQX micro-interaction) ── */
.sdm-tab-fade-enter-active,
.sdm-tab-fade-leave-active {
  transition: opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.sdm-tab-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.sdm-tab-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Top tabs (tablet/mobile only) */
.sdm-top-tabs {
  display: none;
}

/* Responsive: tablet (768-1023px) */
@media (max-width: 1023px) {
  .sdm-sidebar {
    display: none;
  }
  .sdm-top-tabs {
    display: flex;
  }
  .sdm-tab-panels {
    min-height: 280px;
  }
  .sdm-tab-content {
    padding-top: var(--qqx-space-sm);
  }
}

/* Responsive: mobile (< 768px) */
@media (max-width: 767px) {
  .sdm-top-tabs {
    gap: var(--qqx-space-sm);
  }
  .sdm-tab-panels {
    min-height: 240px;
  }
}

/* ── Details tab ── */

.detail-content {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

.detail-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  font-size: var(--qqx-font-size-small);
}

.detail-label {
  color: var(--qqx-text-tertiary);
  min-width: 60px;
  font-size: var(--qqx-font-size-small);
}

.detail-row code {
  font-size: var(--qqx-font-size-small);
  background: var(--qqx-bg-elevated);
  padding: 1px 6px;
  border-radius: var(--qqx-radius-xs);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.category-tag {
  background: var(--qqx-bg-elevated);
  padding: 1px 8px;
  border-radius: var(--qqx-radius-full);
  font-size: var(--qqx-font-size-small);
}

.detail-desc {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  line-height: 1.6;
  margin: 0;
  padding-top: var(--qqx-space-sm);
  border-top: 1px solid var(--qqx-border-color);
}

/* ── Install tab ── */

.im-tabs {
  display: inline-flex;
  background: var(--qqx-bg-subtle, var(--qqx-bg-surface));
  border-radius: var(--qqx-radius-xs, 4px);
  padding: 2px;
  margin-bottom: var(--qqx-space-md);
}

.im-tab {
  padding: 4px 12px;
  border: none;
  background: transparent;
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  font-weight: 400;
  cursor: pointer;
  font-family: inherit;
  border-radius: 6px;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.im-tab:not(.im-tab--active):hover {
  color: var(--qqx-text-primary);
}

.im-tab--active {
  background: var(--qqx-bg-elevated, var(--qqx-bg-base));
  color: var(--qqx-text-primary);
  font-weight: 500;
}

.im-body {
  /* QModal body handles scrolling */
}

.im-empty {
  padding: 24px 0;
  text-align: center;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
}

/* Target row */
.im-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  gap: var(--qqx-space-md);
}

.im-row + .im-row {
  border-top: 1px solid var(--qqx-border-color);
}

.im-row-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.im-row-name {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.im-row-path {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  font-family: 'SF Mono', 'Fira Code', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Project */
.im-project {
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  overflow: hidden;
}

.im-project + .im-project {
  margin-top: var(--qqx-space-sm);
}

.im-project-header {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-xs);
  padding: 10px 12px;
  cursor: pointer;
  user-select: none;
  transition: background var(--qqx-transition);
}

.im-project-header:hover {
  background: var(--qqx-bg-hover);
}

.im-chevron {
  display: flex;
  color: var(--qqx-text-tertiary);
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.im-chevron--open {
  transform: rotate(90deg);
}

.im-project-name {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.im-project-count {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
}

.im-project-installing {
  font-size: var(--qqx-font-size-tiny);
  color: var(--qqx-brand);
  margin-left: auto;
}

.im-project-body {
  border-top: 1px solid var(--qqx-border-color);
  padding: var(--qqx-space-sm) 12px var(--qqx-space-md);
  background: var(--qqx-bg-elevated);
}

.im-target-block {
  margin-bottom: var(--qqx-space-sm);
}

.im-target-path {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  font-family: 'SF Mono', 'Fira Code', monospace;
  margin-bottom: var(--qqx-space-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.im-agent-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-left: var(--qqx-space-sm);
  border-left: 2px solid var(--qqx-border-color);
}

.im-agent-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
}

.im-agent-badge {
  font-size: var(--qqx-font-size-tiny);
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
  padding: 1px 6px;
  border-radius: var(--qqx-radius-full);
  flex-shrink: 0;
}

.im-agent-path {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  font-family: 'SF Mono', 'Fira Code', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.im-agent-warn {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-info);
  background: var(--qqx-info-light);
  padding: 8px 10px;
  border-radius: var(--qqx-radius-xs);
  margin: 4px 0;
}

.im-agent-warn svg {
  flex-shrink: 0;
  margin-top: 1px;
}

.im-project-install-all {
  margin-top: var(--qqx-space-sm);
  width: 100%;
}

/* Custom path */
.im-custom {
  border-top: 1px solid var(--qqx-border-color);
  margin-top: var(--qqx-space-md);
  padding-top: var(--qqx-space-md);
}

.im-custom-label {
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-secondary);
  margin-bottom: var(--qqx-space-sm);
}

.im-custom-row {
  display: flex;
  gap: var(--qqx-space-sm);
}

.im-custom-input {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  border: 1px solid var(--qqx-input-border, var(--qqx-border-color));
  border-radius: var(--qqx-radius-xs);
  background: var(--qqx-input-bg, var(--qqx-bg-card));
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-small);
  font-family: inherit;
  outline: none;
  transition: border-color var(--qqx-transition);
}

.im-custom-input:focus {
  border-color: var(--qqx-brand);
  box-shadow: var(--qqx-shadow-focus, 0 0 0 3px rgba(0, 153, 255, 0.15));
}

.im-custom-input::placeholder {
  color: var(--qqx-text-tertiary);
}

.im-custom-preview {
  margin-top: var(--qqx-space-xs);
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

/* Status messages */
.im-error {
  margin-top: var(--qqx-space-md);
  padding: 8px 12px;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-error);
  background: var(--qqx-error-light);
  border-radius: var(--qqx-radius-xs);
}

.im-ok {
  margin-top: var(--qqx-space-md);
  padding: 8px 12px;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-success);
  background: var(--qqx-success-light);
  border-radius: var(--qqx-radius-xs);
}

/* ── Sync status tab ── */

.sync-loading, .sync-empty {
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
  padding: var(--qqx-space-xl);
  text-align: center;
}

.sync-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sync-card {
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  padding: 12px;
  transition: border-color 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.sync-card:hover {
  border-color: var(--qqx-brand);
}

.sync-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--qqx-space-md);
  margin-bottom: 4px;
}

.sync-card-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.sync-card-name {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.sync-card-project {
  font-size: var(--qqx-font-size-tiny);
  color: var(--qqx-brand);
  background: var(--qqx-brand-light);
  padding: 0 6px;
  border-radius: var(--qqx-radius-full);
}

.sync-card-path {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  font-family: 'SF Mono', 'Fira Code', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 8px;
}

.sync-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sync-badge {
  font-size: var(--qqx-font-size-tiny);
  padding: 2px 10px;
  border-radius: var(--qqx-radius-full);
  flex-shrink: 0;
  font-weight: var(--qqx-font-medium);
}

.sync-badge--unchanged {
  color: var(--qqx-success);
  background: var(--qqx-success-light);
}

.sync-badge--changed {
  color: var(--qqx-warning);
  background: var(--qqx-warning-light);
}

.sync-badge--missing {
  color: var(--qqx-error);
  background: var(--qqx-error-light);
}

.sync-badge--not-installed {
  color: var(--qqx-text-tertiary);
  background: var(--qqx-bg-elevated);
}

.sync-badge--configured {
  color: var(--qqx-text-secondary);
  background: var(--qqx-bg-elevated);
}

/* ── Diff (nested modal) ── */

.diff-summary {
  display: flex;
  gap: var(--qqx-space-sm);
  flex-wrap: wrap;
  margin-bottom: var(--qqx-space-md);
  padding-bottom: var(--qqx-space-md);
  border-bottom: 1px solid var(--qqx-border-color);
}

.diff-stat {
  font-size: var(--qqx-font-size-small);
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
}

.diff-stat.unchanged {
  background: var(--qqx-diff-unchanged-tag-bg);
  color: var(--qqx-diff-unchanged-tag-text);
}

.diff-stat.added {
  background: var(--qqx-diff-added-tag-bg);
  color: var(--qqx-diff-added-tag-text);
}

.diff-stat.modified {
  background: var(--qqx-diff-modified-tag-bg);
  color: var(--qqx-diff-modified-tag-text);
}

.diff-stat.removed {
  background: var(--qqx-diff-removed-tag-bg);
  color: var(--qqx-diff-removed-tag-text);
}

.diff-file-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.diff-file-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  padding: 4px 8px;
  border-radius: var(--qqx-radius-xs);
  cursor: pointer;
  transition: background var(--qqx-transition);
}

.diff-file-row:hover {
  box-shadow: inset 0 0 0 999px rgba(0, 0, 0, 0.06);
}

.diff-file-row.added { background: var(--qqx-diff-added-row-bg); }
.diff-file-row.modified { background: var(--qqx-diff-modified-row-bg); }
.diff-file-row.removed { background: var(--qqx-diff-removed-row-bg); }

.diff-file-status {
  font-size: 11px;
  min-width: 64px;
  font-weight: var(--qqx-font-medium);
}

.diff-file-path {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  word-break: break-all;
}

.diff-all-unchanged {
  text-align: center;
  padding: var(--qqx-space-xl);
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
}

.diff-file-nav {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  margin-bottom: var(--qqx-space-md);
  padding-bottom: var(--qqx-space-md);
  border-bottom: 1px solid var(--qqx-border-color);
}

.diff-file-nav-path {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
}
</style>
