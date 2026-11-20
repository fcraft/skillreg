<template>
  <QModal v-model="open" :title="skill?.name || 'Skill 详情'" width="820px" class="sdm-modal">
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
            :class="['sdm-sidebar-item', 'q-press', { 'sdm-sidebar-item--active': activeTab === tab.key }]"
            :aria-pressed="activeTab === tab.key"
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
          <div v-if="skill.source" class="detail-row">
            <span class="detail-label">NPM 来源</span>
            <button class="detail-link q-press" @click="openSource">
              {{ skill.source.package }}@{{ skill.source.resolvedVersion }} →
            </button>
          </div>
          <div v-if="skill.repositoryPath" class="detail-row">
            <span class="detail-label">所属仓库</span>
            <button class="detail-link q-press" @click="openRepository">
              {{ skill.repositoryPath.replace(/^repos\//, '') }} →
            </button>
          </div>
          <p v-if="skill.description" class="detail-desc">{{ skill.description }}</p>
        </div>
      </div>

      <!-- Tab: 安装 -->
      <div v-else-if="activeTab === 'install'" key="install" class="sdm-tab-content">
        <div class="im-tabs">
          <button :class="['im-tab', 'q-press', { 'im-tab--active': installSubTab === 'targets' }]" :aria-pressed="installSubTab === 'targets'" @click="installSubTab = 'targets'">目标</button>
          <button :class="['im-tab', 'q-press', { 'im-tab--active': installSubTab === 'projects' }]" :aria-pressed="installSubTab === 'projects'" @click="installSubTab = 'projects'">项目组</button>
          <button :class="['im-tab', 'q-press', { 'im-tab--active': installSubTab === 'ssh' }]" :aria-pressed="installSubTab === 'ssh'" @click="installSubTab = 'ssh'">SSH</button>
        </div>

        <SkillSshInstall v-if="installSubTab === 'ssh'" :key="skill.name" :skill-name="skill.name" @manage="close(); router.push('/ssh')" />

        <!-- Sub Tab: 目标 -->
        <div v-if="installSubTab === 'targets'" class="im-body">
          <div v-if="syncState.loading && !syncState.loaded" class="im-empty">加载同步目标...</div>
          <div v-else-if="syncState.error && !targets.length" class="im-error im-error-row" role="alert">
            <span>加载同步目标失败：{{ syncState.error }}</span>
            <QButton type="text" size="small" @click="retryLoadSync">重试</QButton>
          </div>
          <div v-else-if="!targets.length" class="im-empty">未自动探测到常见 Agent 目录，可在下方输入自定义目录或在「Sync 工具」中添加目标</div>
          <div v-for="t in targets" :key="t.id || t.path" class="im-row">
            <ProviderIcon :target="t" :size="18" class="im-row-icon" />
            <div class="im-row-info">
              <div class="im-row-title">
                <span class="im-row-name">{{ t.label || t.name }}</span>
                <span v-if="targetBadgeText(t)" class="im-row-badge" :class="{ 'im-row-badge--shared': t.shared }">{{ targetBadgeText(t) }}</span>
              </div>
              <span class="im-row-path" :title="t.path">→ {{ formatAgentDisplayPath(t.path, t.relPath) }}/{{ skill.name }}</span>
            </div>
            <QButton v-if="isInstalled(t.path)" type="ghost" size="small" disabled>已安装</QButton>
            <QButton v-else type="secondary" tint="brand" size="small" :disabled="installing" @click="doInstallTarget(t)">
              {{ installingTarget === (t.id || t.path) ? '安装中...' : '安装' }}
            </QButton>
          </div>
        </div>

        <!-- Sub Tab: 项目组 -->
        <div v-if="installSubTab === 'projects'" class="im-body">
          <div v-if="projectsLoading && !projects.length" class="im-empty">加载项目组...</div>
          <div v-else-if="projectsError && !projects.length" class="im-error im-error-row" role="alert">
            <span>加载项目组失败：{{ projectsError }}</span>
            <QButton type="text" size="small" @click="loadProjects">重试</QButton>
          </div>
          <div v-else-if="!projects.length" class="im-empty">暂无项目组，在「项目组」页面创建</div>
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
                <div v-if="discoveringTargets[t]" class="im-agent-loading">正在检测 agent 目录...</div>
                <div v-else-if="discoveredMap[t]?.agent_dirs?.length" class="im-agent-list">
                  <div v-for="d in discoveredMap[t].agent_dirs" :key="d.path || d.agent" class="im-agent-row">
                    <span class="im-agent-badge">
                      <ProviderIcon :target="d" :size="14" />
                      <span>{{ d.name || d.agent }}</span>
                    </span>
                    <span class="im-agent-path">→ {{ d.path }}/{{ skill.name }}</span>
                    <QButton v-if="isInstalled(d.path)" type="ghost" size="small" disabled>已安装</QButton>
                    <QButton v-else type="secondary" tint="brand" size="small" :disabled="installing" @click="doInstallPath(d.path, `${d.name || d.agent} (${d.path})`)">
                      {{ installingTarget === d.path ? '安装中...' : '安装' }}
                    </QButton>
                  </div>
                </div>
                <div v-else class="im-agent-warn">
                  <TriangleAlert :size="14" />
                  <span>未发现 agent 目录，将安装到根目录: {{ t }}/{{ skill.name }}</span>
                  <QButton v-if="isInstalled(t)" type="ghost" size="small" disabled>已安装</QButton>
                  <QButton v-else type="secondary" tint="brand" size="small" :disabled="installing" @click="doInstallPath(t, t)">
                    {{ installingTarget === t ? '安装中...' : '安装' }}
                  </QButton>
                </div>
              </div>
              <QButton type="primary" size="small" :disabled="installing || isProjectDiscovering(p)" @click="doInstallProject(p)" class="im-project-install-all">
                {{ installingProject === p.id ? '安装中...' : '一键安装到全部目标' }}
              </QButton>
            </div>
          </div>
        </div>

        <!-- Custom path -->
        <div v-if="installSubTab !== 'ssh'" class="im-custom">
          <div class="im-custom-label">自定义目录</div>
          <div class="im-custom-row">
            <input v-model="customPath" class="im-custom-input" placeholder="输入绝对路径或 ~/ 开头路径，如 ~/.claude/skills" @keydown.enter="doInstallCustom" />
            <QButton type="primary" size="small" :disabled="!customPath.trim() || installing" @click="doInstallCustom">安装</QButton>
          </div>
          <div v-if="customPath.trim()" class="im-custom-preview">→ {{ customPath.trim() }}/{{ skill.name }}</div>
        </div>

        <div v-if="installError" class="im-error" role="alert">{{ installError }}</div>
        <div v-if="installOk" class="im-ok" role="status">{{ installOk }}</div>
      </div>

      <!-- Tab: 同步状态 -->
      <div v-else-if="activeTab === 'sync'" key="sync" class="sdm-tab-content">
        <div v-if="syncState.loading && !syncState.loaded" class="sync-loading">加载同步状态...</div>
        <div v-else-if="syncState.error && !allTargetsWithStatus.length" class="im-error im-error-row" role="alert">
          <span>加载同步状态失败：{{ syncState.error }}</span>
          <QButton type="text" size="small" @click="retryLoadSync">重试</QButton>
        </div>
        <div v-else-if="!allTargetsWithStatus.length" class="sync-empty">暂无可用的同步目标</div>
        <div v-else class="sync-list">
          <div v-if="syncError" class="im-error" role="alert">{{ syncError }}</div>
          <div v-for="item in allTargetsWithStatus" :key="item.key" class="sync-card">
            <div class="sync-card-header">
              <div class="sync-card-info">
                <ProviderIcon :target="item" :size="16" class="sync-card-icon" />
                <span class="sync-card-name">{{ item.label }}</span>
                <span v-if="targetBadgeText(item)" class="im-row-badge" :class="{ 'im-row-badge--shared': item.shared }">{{ targetBadgeText(item) }}</span>
                <span v-if="item._projectName" class="sync-card-project">{{ item._projectName }}</span>
              </div>
              <span class="sync-badge" :class="'sync-badge--' + item.status">{{ statusLabel(item.status) }}</span>
            </div>
            <div class="sync-card-path" :title="item.path">{{ formatAgentDisplayPath(item.path, item.relPath) }}</div>
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
import { ref, computed, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { FolderOpen, TriangleAlert, Download } from 'lucide-vue-next'
import QModal from './QModal.vue'
import QButton from './QButton.vue'
import QDiffViewer from './QDiffViewer.vue'
import SkillDetailDrawer from './SkillDetailDrawer.vue'
import SkillSshInstall from './ssh/SkillSshInstall.vue'
import ProviderIcon from './ProviderIcon.vue'
import { useSkillDetail } from '../composables/useSkillDetail.js'
import { useSyncBridge } from '../composables/useSyncBridge.js'
import { useToast } from '../composables/useToast.js'
import {
  buildTargetStatusItems,
  formatInstallError,
  parseSyncExecutionResult,
  resolveProjectInstallTargets,
} from '../sources/skillInstallState.js'
import {
  executeSync, fetchProjects, fetchDiscover,
  fetchSkillDiff, fetchSkillFile, fetchTargetFile,
  exportSkill,
} from '../api/index.js'
import {
  formatAgentDisplayPath,
  targetBadgeText,
} from '../sources/agentTargets.js'

const { state, close, openFileDrawer, closeFileDrawer } = useSkillDetail()
const { state: syncState, loadSyncStatus, getSkillTargetStatus, refreshSkill } = useSyncBridge()
const toast = useToast()
const router = useRouter()

const skill = computed(() => state.skill)

function openSource() {
  const sourceId = skill.value?.source?.id
  if (!sourceId) return
  close()
  router.push({ name: 'sources', query: { source: sourceId } })
}

function openRepository() {
  const path = skill.value?.repositoryPath
  if (!path) return
  close()
  router.push({ name: 'repos', query: { repo: path, skill: skill.value.name } })
}
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
const installingTarget = ref(null)
const syncingTarget = ref(null)
const installError = ref('')
const installOk = ref('')
const syncError = ref('')
const customPath = ref('')
const installSubTab = ref('targets')
const projects = ref([])
const projectsLoading = ref(false)
const projectsError = ref('')
const expandedProject = ref(null)
const installingProject = ref(null)
const discoveredMap = ref({})
const discoveringTargets = ref({})

let okTimer = null
let projectsRequestId = 0

function clearOkTimer() {
  if (okTimer !== null) {
    clearTimeout(okTimer)
    okTimer = null
  }
}

function setTransientInstallOk(message, { clearCustom = false } = {}) {
  clearOkTimer()
  installOk.value = message
  okTimer = setTimeout(() => {
    installOk.value = ''
    if (clearCustom) customPath.value = ''
    okTimer = null
  }, 2500)
}

function isCurrentSkill(skillName) {
  return Boolean(state.open && skill.value && skill.value.name === skillName)
}

onUnmounted(() => {
  clearOkTimer()
})

// ── Install: computed from sync bridge ──
const targets = computed(() => syncState.targets || [])

// ── Sync status computed ──
const targetStatusMap = computed(() => {
  if (!skill.value) return {}
  return getSkillTargetStatus(skill.value.name)
})

const allTargetsWithStatus = computed(() => {
  return buildTargetStatusItems(syncState.targets, syncState.projectTargets, targetStatusMap.value)
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

function isProjectDiscovering(project) {
  return (project?.targets || []).some(t => Boolean(discoveringTargets.value[t]))
}

async function retryLoadSync() {
  const currentName = skill.value?.name
  await loadSyncStatus(true)
  if (currentName && isCurrentSkill(currentName)) {
    await refreshSkill(currentName)
  }
}

// ── Install: watch for modal open, skill change, and tab switch ──
watch(
  [() => state.open, () => state.activeTab, () => state.skill?.name],
  async ([isOpen, tab, skillName], prev) => {
    clearOkTimer()
    installError.value = ''
    installOk.value = ''
    syncError.value = ''

    if (!isOpen || !skillName) return

    const tabChanged = !prev || prev[1] !== tab || prev[0] !== isOpen || prev[2] !== skillName
    if (tab === 'install' && tabChanged) {
      installSubTab.value = 'targets'
      expandedProject.value = null
      customPath.value = ''
      discoveredMap.value = {}
      discoveringTargets.value = {}
      loadProjects()
    }

    if (tab === 'install' || tab === 'sync') {
      if (!syncState.loaded || syncState.error) {
        await loadSyncStatus(Boolean(syncState.error))
      }
      if (isCurrentSkill(skillName)) {
        await refreshSkill(skillName)
      }
    }
  },
  { immediate: true },
)

// ── Install: project loading ──
async function loadProjects() {
  const requestId = ++projectsRequestId
  projectsLoading.value = true
  projectsError.value = ''
  try {
    const list = await fetchProjects()
    if (requestId !== projectsRequestId) return
    projects.value = list
    const allTargets = [...new Set(list.flatMap(p => p.targets || []))]
    await Promise.allSettled(allTargets.map(t => fetchDiscoverForTarget(t, requestId)))
  } catch (e) {
    if (requestId !== projectsRequestId) return
    projectsError.value = formatInstallError(e, '加载项目组失败')
  } finally {
    if (requestId === projectsRequestId) {
      projectsLoading.value = false
    }
  }
}

async function fetchDiscoverForTarget(targetPath, requestId = projectsRequestId) {
  discoveringTargets.value = { ...discoveringTargets.value, [targetPath]: true }
  try {
    const data = await fetchDiscover(targetPath)
    if (requestId !== projectsRequestId) return
    discoveredMap.value = { ...discoveredMap.value, [targetPath]: data }
  } catch {
    if (requestId !== projectsRequestId) return
    discoveredMap.value = { ...discoveredMap.value, [targetPath]: { agent_dirs: [] } }
  } finally {
    if (requestId === projectsRequestId) {
      const next = { ...discoveringTargets.value }
      delete next[targetPath]
      discoveringTargets.value = next
    }
  }
}

// ── Export state ──
const exporting = ref(false)

async function handleExport() {
  const skillName = skill.value?.name
  if (exporting.value || !skillName) return
  exporting.value = true
  try { await exportSkill(skillName) } catch (e) { console.error('Export failed:', e) }
  finally { exporting.value = false }
}

// ── Install: actions ──
async function runSingleInstall(targetIdentifier, displayLabel, { clearCustomOnSuccess = false } = {}) {
  const skillName = skill.value?.name
  if (!skillName || !targetIdentifier) return
  installing.value = true
  installingTarget.value = targetIdentifier
  clearOkTimer()
  installError.value = ''
  installOk.value = ''
  try {
    const result = await executeSync(targetIdentifier, { skills: [skillName] })
    const parsed = parseSyncExecutionResult(result, { skillName, fallback: '安装失败' })
    if (!parsed.ok) {
      throw new Error(parsed.message)
    }
    await refreshSkill(skillName)
    if (isCurrentSkill(skillName)) {
      setTransientInstallOk(`已安装到 ${displayLabel}`, { clearCustom: clearCustomOnSuccess })
    }
    toast.success(`已安装 ${skillName} → ${displayLabel}`)
  } catch (e) {
    const message = formatInstallError(e, '安装失败')
    if (isCurrentSkill(skillName)) {
      installError.value = message
    }
    toast.error(`安装 ${skillName} 失败：${message}`)
  } finally {
    installing.value = false
    installingTarget.value = null
  }
}

function doInstallTarget(targetObj) {
  const identifier = targetObj.id || targetObj.path
  const label = targetObj.label || targetObj.name || targetObj.path
  return runSingleInstall(identifier, label)
}

function doInstallPath(targetPath, displayLabel = targetPath) {
  return runSingleInstall(targetPath, displayLabel)
}

async function doSyncTarget(item) {
  const skillName = skill.value?.name
  if (!skillName || !item) return
  syncingTarget.value = item.key
  syncError.value = ''
  try {
    const targetIdentifier = item.target || item.path || item.key
    const result = await executeSync(targetIdentifier, { skills: [skillName] })
    const parsed = parseSyncExecutionResult(result, { skillName, fallback: '同步失败' })
    if (!parsed.ok) {
      throw new Error(parsed.message)
    }
    await refreshSkill(skillName)
    toast.success(`${skillName} → ${item.label} 同步完成`)
  } catch (e) {
    const message = formatInstallError(e, '同步失败')
    if (isCurrentSkill(skillName)) {
      syncError.value = `${item.label}：${message}`
    }
    toast.error(`同步 ${skillName} 失败：${message}`)
  } finally {
    syncingTarget.value = null
  }
}

async function doInstallProject(proj) {
  const skillName = skill.value?.name
  const rawTargets = proj?.targets || []
  if (!skillName || !rawTargets.length) return
  installing.value = true
  installingProject.value = proj.id
  clearOkTimer()
  installError.value = ''
  installOk.value = ''

  try {
    const undiscovered = rawTargets.filter(t => discoveredMap.value[t] === undefined)
    if (undiscovered.length) {
      await Promise.allSettled(undiscovered.map(t => fetchDiscoverForTarget(t)))
    }
    const destinations = resolveProjectInstallTargets(proj, discoveredMap.value)
    if (!destinations.length) return

    const errors = []
    for (const dest of destinations) {
      try {
        const result = await executeSync(dest.path, { skills: [skillName] })
        const parsed = parseSyncExecutionResult(result, { skillName, fallback: '安装失败' })
        if (!parsed.ok) {
          throw new Error(parsed.message)
        }
      } catch (e) {
        errors.push(`${dest.label}: ${formatInstallError(e, '安装失败')}`)
      }
    }
    await refreshSkill(skillName)
    if (errors.length) {
      const msg = `${errors.length}/${destinations.length} 个目标失败：${errors.join('；')}`
      if (isCurrentSkill(skillName)) {
        installError.value = msg
      }
      toast.error(msg)
    } else {
      const msg = `已安装到 ${proj.name}（${destinations.length} 个目标）`
      if (isCurrentSkill(skillName)) {
        setTransientInstallOk(msg)
      }
      toast.success(`已安装 ${skillName} → ${proj.name}（${destinations.length} 个目标）`)
    }
  } finally {
    installing.value = false
    installingProject.value = null
  }
}

async function doInstallCustom() {
  const path = customPath.value.trim()
  if (!path) return
  await runSingleInstall(path, path, { clearCustomOnSuccess: true })
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
  const skillName = skill.value?.name
  if (!skillName || !item) return
  const targetIdentifier = item.target || item.path || item.key
  showDiff.value = true
  diffSkill.value = skillName
  diffTarget.value = targetIdentifier
  diffTargetLabel.value = item._project ? `${item._projectName || ''}/${item.label}` : item.label
  diffLoading.value = true
  diffError.value = null
  diffFiles.value = []
  diffSummary.value = {}
  selectedDiffFile.value = null
  previewSource.value = ''
  previewTarget.value = ''
  previewError.value = ''
  fetchSkillDiff(skillName, targetIdentifier)
    .then(data => {
      diffFiles.value = data.files || []
      diffSummary.value = data.summary || {}
    })
    .catch(e => { diffError.value = formatInstallError(e, '加载差异失败') })
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

    // removed: exists in source, missing in target
    // added: exists in target, missing in source
    // modified: exists in both
    if (file.status !== 'added') {
      repoPromise = fetchSkillFile(skillName, filePath)
        .then(data => data.exists === false ? '(文件不存在)' : (data.content || ''))
    }
    if (file.status !== 'removed') {
      targetPromise = fetchTargetFile(skillName, targetName, filePath)
        .then(data => data.exists === false ? '(文件不存在)' : (data.content || ''))
    }

    const [repo, target] = await Promise.all([repoPromise, targetPromise])
    previewSource.value = repo
    previewTarget.value = target
  } catch (e) {
    previewError.value = formatInstallError(e, '加载文件内容失败')
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
  gap: var(--sr-space-2);
  flex: 1;
  min-width: 0;
}

.sdm-header-title {
  font-size: var(--sr-text-dialog-title);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
  margin: 0;
}

.sdm-root {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

/* Layout: borderless sidebar + content (desktop) */
.sdm-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: var(--sr-space-4);
}

.sdm-sidebar {
  width: 148px;
  flex-shrink: 0;
  background: transparent;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sdm-sidebar-item {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  min-height: 36px;
  padding: 0 12px;
  font-size: var(--sr-text-body);
  font-weight: var(--sr-weight-medium);
  color: var(--sr-text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--sr-radius-sm);
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition: color var(--sr-duration-fast) var(--sr-ease-standard),
              background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.sdm-sidebar-item:not(.sdm-sidebar-item--active):hover {
  background: var(--sr-bg-hover);
  color: var(--sr-text-primary);
}

.sdm-sidebar-item--active {
  background: var(--sr-nav-bg-selected);
  color: var(--sr-text-primary);
  font-weight: var(--sr-weight-semibold);
}

.sdm-sidebar-item--active:hover {
  background: var(--sr-nav-bg-selected-hover);
}

/* Content area */
.sdm-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.sdm-tab-panels {
  flex: 1;
  min-height: 320px;
  display: flex;
  flex-direction: column;
}

.sdm-tab-content {
  flex: 1;
  min-height: 0;
  padding: 2px 0;
}

.sdm-tab-fade-enter-active,
.sdm-tab-fade-leave-active {
  transition: opacity var(--sr-duration-fast) var(--sr-ease-standard),
              transform var(--sr-duration-fast) var(--sr-ease-standard);
}

.sdm-tab-fade-enter-from,
.sdm-tab-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

@media (prefers-reduced-motion: reduce) {
  .sdm-tab-fade-enter-active, .sdm-tab-fade-leave-active { transition: opacity 80ms linear; }
  .sdm-tab-fade-enter-from, .sdm-tab-fade-leave-to { transform: none; }
  .im-chevron { transition: none; }
}

.sdm-top-tabs {
  display: none;
}

@media (max-width: 1023px) {
  .sdm-sidebar { display: none; }
  .sdm-top-tabs { display: flex; }
  .sdm-tab-panels { min-height: 280px; }
}

@media (max-width: 760px) {
  .sdm-tab-panels { min-height: 240px; }
}

/* ── Details tab ── */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: var(--sr-space-3);
  padding: var(--sr-space-4);
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
}

.detail-row {
  display: flex;
  align-items: center;
  gap: var(--sr-space-3);
  font-size: var(--sr-text-card-title);
}

.detail-label {
  color: var(--sr-text-tertiary);
  min-width: 64px;
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-semibold);
}

.detail-row code {
  font-size: var(--sr-text-compact);
  background: var(--sr-bg-panel);
  color: var(--sr-text-primary);
  padding: 2px 8px;
  border-radius: var(--sr-radius-xs);
  font-family: var(--sr-font-mono);
}

.detail-link {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--sr-accent);
  cursor: pointer;
  font: inherit;
  font-weight: var(--sr-weight-semibold);
  text-align: left;
}

.detail-link:hover {
  color: var(--sr-accent-strong);
  text-decoration: underline;
}

.category-tag {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  background: var(--sr-bg-panel);
  color: var(--sr-text-secondary);
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
}

.detail-desc {
  font-size: var(--sr-text-body);
  color: var(--sr-text-secondary);
  line-height: 1.65;
  margin: var(--sr-space-1) 0 0;
  padding: var(--sr-space-3);
  border-radius: var(--sr-radius-sm);
  background: var(--sr-bg-panel);
}

/* ── Install tab ── */
.im-tabs {
  display: inline-flex;
  gap: 2px;
  background: var(--sr-control-bg);
  border-radius: var(--sr-radius-md);
  padding: 3px;
  margin-bottom: var(--sr-space-4);
}

.im-tab {
  min-height: 26px;
  padding: 0 12px;
  border: none;
  background: transparent;
  color: var(--sr-text-secondary);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-medium);
  cursor: pointer;
  font-family: inherit;
  border-radius: var(--sr-radius-sm);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
}

.im-tab:not(.im-tab--active):hover {
  color: var(--sr-text-primary);
}

.im-tab--active {
  background: var(--sr-action-bg-selected);
  color: var(--sr-text-primary);
  font-weight: var(--sr-weight-semibold);
}

.im-body {
  display: flex;
  flex-direction: column;
  gap: var(--sr-space-2);
}

.im-empty {
  padding: var(--sr-space-5) var(--sr-space-4);
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  text-align: center;
  font-size: var(--sr-text-card-title);
  color: var(--sr-text-tertiary);
}

/* Target row — borderless tonal Workbench surface */
.im-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  gap: var(--sr-space-3);
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.im-row:hover {
  background: var(--sr-content-bg-hover);
}

.im-row-icon {
  color: var(--sr-text-primary);
}

.im-row-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}

.im-row-title {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  min-width: 0;
}

.im-row-name {
  font-size: var(--sr-text-card-title);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
}

.im-row-badge {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
  background: var(--sr-bg-panel);
  color: var(--sr-text-secondary);
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  line-height: 1;
  flex-shrink: 0;
}

.im-row-badge--shared {
  background: var(--sr-role-blue-surface);
  color: var(--sr-role-blue-ink);
}

.im-row-path {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
  font-family: var(--sr-font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Project — borderless container, no left stripe on agent list */
.im-project {
  border: none;
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  overflow: hidden;
}

.im-project-header {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  min-height: 40px;
  padding: 8px 14px;
  cursor: pointer;
  user-select: none;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.im-project-header:hover {
  background: var(--sr-bg-hover);
}

.im-chevron {
  display: flex;
  color: var(--sr-text-tertiary);
  transition: transform var(--sr-duration-normal) var(--sr-ease-standard);
  flex-shrink: 0;
}

.im-chevron--open {
  transform: rotate(90deg);
}

.im-project-name {
  font-size: var(--sr-text-card-title);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
}

.im-project-count {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
}

.im-project-installing {
  font-size: var(--sr-text-meta);
  color: var(--sr-accent);
  font-weight: var(--sr-weight-semibold);
  margin-left: auto;
}

.im-project-body {
  padding: var(--sr-space-2) 14px var(--sr-space-3);
  background: transparent;
}

.im-target-block {
  margin-bottom: var(--sr-space-3);
}

.im-target-path {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-secondary);
  font-family: var(--sr-font-mono);
  margin-bottom: var(--sr-space-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.im-agent-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: var(--sr-space-3);
}

.im-agent-row {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  padding: 6px 10px;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-bg-panel);
}

.im-agent-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 22px;
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  background: var(--sr-role-blue-surface);
  color: var(--sr-role-blue-ink);
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
  flex-shrink: 0;
}

.im-agent-path {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
  font-family: var(--sr-font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.im-agent-loading {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
  padding: 6px 8px;
}

.im-agent-warn {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  font-size: var(--sr-text-compact);
  color: var(--sr-role-amber-ink);
  background: var(--sr-role-amber-surface);
  padding: 10px 12px;
  border-radius: var(--sr-radius-md);
  margin: 4px 0;
}

.im-agent-warn svg {
  flex-shrink: 0;
}

.im-project-install-all {
  margin-top: var(--sr-space-2);
  width: 100%;
}

/* Custom path — borderless Glass input */
.im-custom {
  margin-top: var(--sr-space-4);
  padding: var(--sr-space-3) var(--sr-space-4);
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
}

.im-custom-label {
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-bold);
  color: var(--sr-text-secondary);
  margin-bottom: var(--sr-space-2);
}

.im-custom-row {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
}

.im-custom-input {
  flex: 1;
  height: var(--sr-control-height-sm);
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-bg-panel);
  color: var(--sr-text-primary);
  font-size: var(--sr-text-compact);
  font-family: var(--sr-font-mono);
  outline: none;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              box-shadow 140ms var(--sr-ease-standard);
}

.im-custom-input:focus {
  box-shadow: var(--sr-control-focus-shadow);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              box-shadow 180ms var(--sr-ease-standard);
}

.im-custom-input::placeholder {
  color: var(--sr-text-tertiary);
  font-family: var(--sr-font-sans);
}

.im-custom-preview {
  margin-top: var(--sr-space-2);
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
  font-family: var(--sr-font-mono);
}

/* Status messages */
.im-error {
  margin-top: var(--sr-space-3);
  padding: 10px 14px;
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-medium);
  color: var(--sr-role-rose-ink);
  background: var(--sr-role-rose-surface);
  border-radius: var(--sr-radius-md);
  word-break: break-word;
}

.im-error-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sr-space-2);
}

.im-ok {
  margin-top: var(--sr-space-3);
  padding: 10px 14px;
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-medium);
  color: var(--sr-role-sage-ink);
  background: var(--sr-role-sage-surface);
  border-radius: var(--sr-radius-md);
}

/* ── Sync status tab ── */
.sync-loading,
.sync-empty {
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-card-title);
  padding: var(--sr-space-5);
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  text-align: center;
}

.sync-list {
  display: flex;
  flex-direction: column;
  gap: var(--sr-space-2);
}

.sync-card {
  border: none;
  border-radius: var(--sr-radius-md);
  padding: 12px 16px;
  background: var(--sr-content-bg);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.sync-card:hover {
  background: var(--sr-content-bg-hover);
}

.sync-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sr-space-3);
  margin-bottom: 4px;
}

.sync-card-info {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  min-width: 0;
}

.sync-card-icon {
  color: var(--sr-text-primary);
}

.sync-card-name {
  font-size: var(--sr-text-card-title);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
}

.sync-card-project {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-role-blue-ink);
  background: var(--sr-role-blue-surface);
  padding: 0 7px;
  border-radius: var(--sr-radius-badge);
}

.sync-card-path {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
  font-family: var(--sr-font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: var(--sr-space-2);
}

.sync-card-actions {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
}

.sync-badge {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  font-size: var(--sr-text-meta);
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
  flex-shrink: 0;
  font-weight: var(--sr-weight-semibold);
}

.sync-badge--unchanged {
  color: var(--sr-role-sage-ink);
  background: var(--sr-role-sage-surface);
}

.sync-badge--changed {
  color: var(--sr-role-amber-ink);
  background: var(--sr-role-amber-surface);
}

.sync-badge--missing {
  color: var(--sr-role-rose-ink);
  background: var(--sr-role-rose-surface);
}

.sync-badge--not-installed {
  color: var(--sr-text-secondary);
  background: var(--sr-bg-panel);
}

.sync-badge--configured {
  color: var(--sr-text-secondary);
  background: var(--sr-bg-panel);
}

/* ── Diff (nested modal) ── */
.diff-summary {
  display: flex;
  gap: var(--sr-space-2);
  flex-wrap: wrap;
  margin-bottom: var(--sr-space-3);
}

.diff-stat {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
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
  gap: 4px;
}

.diff-file-row {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  padding: 8px 12px;
  border-radius: var(--sr-radius-sm);
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.diff-file-row:hover {
  background: var(--sr-bg-hover);
}

.diff-file-row.added { background: var(--qqx-diff-added-row-bg); }
.diff-file-row.modified { background: var(--qqx-diff-modified-row-bg); }
.diff-file-row.removed { background: var(--qqx-diff-removed-row-bg); }

.diff-file-status {
  font-size: var(--sr-text-meta);
  min-width: 64px;
  font-weight: var(--sr-weight-semibold);
}

.diff-file-path {
  font-family: var(--sr-font-mono);
  font-size: var(--sr-text-compact);
  color: var(--sr-text-primary);
  word-break: break-all;
}

.diff-all-unchanged {
  text-align: center;
  padding: var(--sr-space-5);
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-card-title);
}

.diff-file-nav {
  display: flex;
  align-items: center;
  gap: var(--sr-space-3);
  margin-bottom: var(--sr-space-3);
}

.diff-file-nav-path {
  font-family: var(--sr-font-mono);
  font-size: var(--sr-text-compact);
  color: var(--sr-text-secondary);
}

@media (pointer: coarse) {
  .sdm-sidebar-item,
  .im-tab {
    min-height: 40px;
  }
}
</style>
