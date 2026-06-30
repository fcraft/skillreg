<template>
  <div>
  <section class="submodule-section">
    <div class="section-header">
      <h2>仓库</h2>
      <span class="count">{{ state.submodules.length + 1 }}</span>
      <QButton
        class="refresh-all-btn"
        type="ghost"
        size="small"
        :disabled="refreshingAll"
        @click="handleRefreshAll"
        :title="refreshingAll ? '正在检查远程...' : '对所有子仓库执行只读远程检查（fetch，不改本地）'"
      >
        {{ refreshingAll ? '检查中...' : '检查全部远程' }}
      </QButton>    </div>
    <div v-if="lastBatchCheckAt" class="refresh-summary">
      <span class="refresh-summary-time">上次检查: {{ relativeTime(new Date(lastBatchCheckAt).toISOString()) }}</span>
      <template v-if="refreshSummary.behind || refreshSummary.ahead || refreshSummary.diverged || refreshSummary.unknown || refreshSummary.dirty">
        <span class="refresh-pill behind" v-if="refreshSummary.behind">落后 {{ refreshSummary.behind }}</span>
        <span class="refresh-pill ahead" v-if="refreshSummary.ahead">领先未推送 {{ refreshSummary.ahead }}</span>
        <span class="refresh-pill diverged" v-if="refreshSummary.diverged">分叉 {{ refreshSummary.diverged }}</span>
        <span class="refresh-pill dirty" v-if="refreshSummary.dirty">有改动 {{ refreshSummary.dirty }}</span>
        <span class="refresh-pill unknown" v-if="refreshSummary.unknown">未知 {{ refreshSummary.unknown }}</span>
      </template>
      <span v-else class="refresh-pill synced">全部已同步</span>
    </div>
    <div v-if="error" class="sync-error">{{ error }}</div>
    <div class="submodule-list">
      <!-- Main repo -->
      <div class="submodule-card" :class="{ expanded: expanded.main }">
        <div class="submodule-row" @click="toggle('main')">
          <span class="expand-indicator">{{ expanded.main ? '▾' : '▸' }}</span>
          <div class="sub-info">
            <div class="sub-name-row">
              <span class="sub-path">agent-hub</span>
              <button
                v-if="remoteUrlMap.main"
                class="repo-btn"
                title="打开仓库"
                @click.stop="openRepo(remoteUrlMap.main)"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                  <polyline points="15 3 21 3 21 9"/>
                  <line x1="10" y1="14" x2="21" y2="3"/>
                </svg>
              </button>
            </div>
            <span class="sub-desc">主仓库</span>
          </div>
          <span class="sub-branch">master</span>
          <span class="commit-count" v-if="mainLogs.length">{{ mainLogs.length }} commits</span>
        </div>
        <div v-show="expanded.main" class="commit-panel">
          <div v-for="commit in mainLogs" :key="commit.hash" class="commit-entry">
            <a class="commit-hash" :href="commitUrl('main', commit.hash)" target="_blank">{{ commit.hash.slice(0, 7) }}</a>
            <span class="commit-msg">{{ commit.message }}</span>
            <span class="commit-time">{{ relativeTime(commit.date) }}</span>
          </div>
        </div>
      </div>

      <!-- Submodules -->
      <div v-for="sub in state.submodules" :key="sub.path" class="submodule-card" :class="{ expanded: expanded[sub.path] }">
        <div class="submodule-row" @click="toggle(sub.path)">
          <span class="expand-indicator">{{ expanded[sub.path] ? '▾' : '▸' }}</span>
          <div class="sub-info">
            <div class="sub-name-row">
              <span class="sub-path">{{ displayPath(sub.path) }}</span>
              <button
                v-if="sub.remoteUrl"
                class="repo-btn"
                title="打开仓库"
                @click.stop="openRepo(sub.remoteUrl)"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                  <polyline points="15 3 21 3 21 9"/>
                  <line x1="10" y1="14" x2="21" y2="3"/>
                </svg>
              </button>
            </div>
            <span class="sub-desc">{{ sub.description }}</span>
          </div>
          <span class="sub-branch">{{ sub.branch }}</span>

          <!-- Detached HEAD warning -->
          <span v-if="sub.status.isDetached" class="detached-badge" title="HEAD 处于游离状态，未关联任何分支">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            游离
          </span>

          <!-- Pointer comparison indicator -->
          <span v-if="pointerLabel(sub)" class="pointer-badge" :class="pointerClass(sub)" :title="pointerTitle(sub)">
            {{ pointerLabel(sub) }}
          </span>

          <span class="sub-sync" :class="sub.status.syncState">{{ sub.status.syncState }}</span>

          <!-- Read-only remote check button + last-checked label -->
          <QButton
            class="refresh-btn"
            type="ghost"
            size="small"
            :disabled="refreshing === sub.path"
            :title="refreshing === sub.path ? '检查中...' : '只读远程检查（fetch，不改本地）'"
            @click.stop="handleRefresh(sub)"
          >
            <template v-if="refreshing === sub.path">…</template>
            <template v-else>↻</template>
          </QButton>
          <span class="checked-at" :title="`上次远程检查: ${refreshCheckedLabel(sub)}`">{{ refreshCheckedLabel(sub) }}</span>

          <!-- Detached HEAD fix button -->
          <button
            v-if="sub.status.isDetached"
            class="fix-detached-btn"
            :disabled="fixingDetached === sub.path"
            @click.stop="handleFixDetached(sub)"
          >
            <template v-if="fixingDetached === sub.path">修复中...</template>
            <template v-else>修复</template>
          </button>

          <!-- Sync button with tooltip -->
          <div class="sync-btn-wrapper"
            @mouseenter="onTooltipEnter($event, sub)"
            @mouseleave="onTooltipLeave"
          >
            <button
              v-if="showSyncButton(sub)"
              class="sync-btn"
              :disabled="syncing === sub.path"
              @click.stop="handleSyncSubmodule(sub)"
            >
              <template v-if="syncing === sub.path">处理中...</template>
              <template v-else>{{ syncButtonLabel(sub) }}</template>
            </button>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="info-icon">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
          </div>

          <span class="commit-count" v-if="subLogs(sub.path).length">{{ subLogs(sub.path).length }}</span>
          <span v-if="skillsBySubmodule[sub.path]?.length" class="skill-count-badge"
            :title="skillsBySubmodule[sub.path].map(s=>s.name).join(', ')"
            @click.stop="navToSkillsFiltered(sub.path)">
            {{ skillsBySubmodule[sub.path].length }} skills
          </span>

          <!-- Repo management dropdown -->
          <div class="repo-more-wrapper" @click.stop>
            <button
              class="repo-more-btn"
              :class="{ 'repo-more-btn--open': repoMenuOpen === sub.path }"
              title="管理仓库"
              @click.stop="toggleRepoMenu(sub.path)"
            >
              <MoreHorizontal :size="14" />
            </button>
            <div v-if="repoMenuOpen === sub.path" class="repo-dropdown">
              <button class="repo-dropdown-item" @click="openInstallRepo(sub)">
                <Download :size="13" /> 一键安装到目标
              </button>
              <button class="repo-dropdown-item" @click="openRenameRepo(sub)">
                <Pencil :size="13" /> 重命名仓库
              </button>
              <button class="repo-dropdown-item repo-dropdown-item--danger" @click="openRemoveRepo(sub)">
                <Trash2 :size="13" /> 删除仓库
              </button>
            </div>
          </div>
        </div>
        <div v-show="expanded[sub.path]" class="commit-panel">
          <!-- Skills section -->
          <div v-if="skillsBySubmodule[sub.path]?.length" class="skills-section">
            <div class="skills-section-label">Skills ({{ skillsBySubmodule[sub.path].length }})</div>
            <div v-for="skill in skillsBySubmodule[sub.path]" :key="skill.name" class="skill-item" @click="navToSkill(skill.name)">
              <span class="skill-item-name">{{ skill.name }}</span>
              <span class="skill-item-type">{{ skill.type }}</span>
            </div>
          </div>
          <div v-for="commit in subLogs(sub.path)" :key="commit.hash" class="commit-entry">
            <a class="commit-hash" :href="commitUrl(sub.path, commit.hash)" target="_blank">{{ commit.hash.slice(0, 7) }}</a>
            <span class="commit-msg">{{ commit.message }}</span>
            <span class="commit-time">{{ relativeTime(commit.date) }}</span>
          </div>
          <div v-if="subLogs(sub.path).length === 0" class="commit-empty">暂无提交记录</div>
        </div>
      </div>
    </div>
  </section>

  <!-- Sync preview modal -->
  <QModal :model-value="previewModal.show" :title="previewModal.title" width="420px" @update:model-value="cancelPreview">
    <template v-if="previewModal.loading">
      <div class="sync-preview-loading">正在分析同步状态...</div>
    </template>
    <template v-else-if="previewModal.data">
      <div class="sync-preview-sub">
        <span class="sync-preview-sub-name">{{ displayPath(previewModal.data.path) }}</span>
        <span class="sync-preview-sub-branch">{{ previewModal.data.branch }}</span>
      </div>
      <div class="sync-preview-actions">
        <div v-for="(action, i) in previewModal.data.actions" :key="i" class="sync-preview-action">
          <span class="sync-preview-action-icon">{{ i + 1 }}</span>
          <span>{{ action }}</span>
        </div>
      </div>
      <div v-if="previewModal.data.warnings.length" class="sync-preview-warnings">
        <div v-for="(w, i) in previewModal.data.warnings" :key="i" class="sync-preview-warning">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          {{ w }}
        </div>
      </div>

      <!-- Dirty file diff viewer -->
      <div v-if="previewModal.data.dirty" class="sync-diff-section">
        <div class="sync-diff-header" @click="diffState.expanded = !diffState.expanded">
          <span class="sync-diff-toggle">{{ diffState.expanded ? '▾' : '▸' }}</span>
          <span>改动文件 ({{ diffState.files.length }})</span>
          <span v-if="diffState.loading" class="sync-diff-loading">加载中…</span>
        </div>
        <div v-if="diffState.expanded" class="sync-diff-body">
          <div class="sync-diff-file-list">
            <button
              v-for="f in diffState.files"
              :key="f.path"
              class="sync-diff-file"
              :class="{ active: diffState.selectedFile === f.path, [f.status]: true }"
              :title="f.path"
              @click="diffState.selectedFile = f.path"
            >
              <span class="sync-diff-file-status">{{ f.status === 'modified' ? 'M' : f.status === 'deleted' ? 'D' : f.status === 'added' ? 'A' : 'R' }}</span>
              <span class="sync-diff-file-name">{{ f.path }}</span>
            </button>
          </div>
          <pre v-if="selectedDiff" class="sync-diff-content"><code v-for="(line, i) in (selectedDiff.diff || '(无文本差异，可能为二进制或纯权限/模式变更)').split('\n')" :key="i" :class="diffLineClass(line)">{{ line }}</code></pre>
        </div>
      </div>

      <!-- Custom commit message (only relevant when there are dirty files to commit) -->
      <div v-if="previewModal.data.dirty" class="sync-commit-msg">
        <label class="sync-commit-label">提交信息（留空则用默认 "chore: sync changes"）</label>
        <QInput v-model="commitMessage" placeholder="chore: sync changes" />
      </div>
    </template>
    <template #footer>
      <QButton type="ghost" @click="cancelPreview">取消</QButton>
      <QButton type="primary" @click="confirmSync">{{ previewModal.confirmLabel }}</QButton>
    </template>
  </QModal>

  <!-- Install repo skills to target modal -->
  <QModal v-model="installRepo.show" :title="`安装仓库到目标 — ${displayPath(installRepo.path || '')}`" width="520px">
    <div class="repo-install-body">
      <p class="repo-install-desc">
        将 <strong>{{ installRepo.skills.length }}</strong> 个 skill 安装到选定目标目录：
      </p>
      <div v-if="!targets.length" class="sync-error">未配置任何目标目录，请先在 Sync 工具中添加。</div>
      <div v-else class="repo-install-targets">
        <label
          v-for="t in targets"
          :key="t.path"
          class="repo-install-target-row"
          :class="{ 'repo-install-target-row--selected': installRepo.target === t.path }"
        >
          <input type="radio" name="install-target" :value="t.path" v-model="installRepo.target" />
          <div class="repo-install-target-info">
            <span class="repo-install-target-name">{{ t.label || t.name }}</span>
            <span class="repo-install-target-path" :title="t.path">{{ displayPath(t.path) }}</span>
          </div>
        </label>
      </div>
      <div v-if="installRepo.skills.length" class="repo-install-skill-hint">
        包含: {{ installRepo.skills.map(s => s.name).join(', ') }}
      </div>
      <div v-if="installRepo.error" class="sync-error">{{ installRepo.error }}</div>
    </div>
    <template #footer>
      <QButton type="ghost" @click="installRepo.show = false">取消</QButton>
      <QButton type="primary" :disabled="installRepo.running || !installRepo.target" @click="confirmInstallRepo">
        {{ installRepo.running ? '安装中...' : `安装 ${installRepo.skills.length} 个 skill` }}
      </QButton>
    </template>
  </QModal>

  <!-- Rename repo modal -->
  <QModal v-model="renameRepo.show" title="重命名仓库" width="440px">
    <div class="repo-rename-body">
      <div class="form-field">
        <label class="form-label">当前路径</label>
        <div class="form-static-value">{{ renameRepo.path }}</div>
      </div>
      <div class="form-field">
        <label class="form-label">新名称（仅末级目录名）</label>
        <QInput
          v-model="renameRepo.newName"
          placeholder="例如 my-skills"
          @keyup.enter="confirmRenameRepo"
        />
        <div class="form-hint">将重命名为 <code>{{ renamePreviewPath }}</code></div>
      </div>
      <div v-if="renameRepo.error" class="sync-error">{{ renameRepo.error }}</div>
    </div>
    <template #footer>
      <QButton type="ghost" @click="renameRepo.show = false">取消</QButton>
      <QButton type="primary" :disabled="renameRepo.running || !renameRepo.newName.trim()" @click="confirmRenameRepo">
        {{ renameRepo.running ? '处理中...' : '确认重命名' }}
      </QButton>
    </template>
  </QModal>

  <!-- Remove repo modal -->
  <QModal v-model="removeRepo.show" title="删除仓库" width="480px">
    <div class="repo-remove-body">
      <div class="repo-remove-warn-icon">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <p class="repo-remove-text">
        确认从 workspace 删除仓库 <strong>{{ displayPath(removeRepo.path || '') }}</strong>？
        此操作会卸载子模块/删除目录并提交，其中 <strong>{{ removeRepo.skillCount }}</strong> 个 skill 将一并移除。
      </p>
      <p class="repo-remove-hint">已安装到各 target 的副本不受影响。此操作无法通过本工具恢复。</p>
      <QInput
        v-model="removeRepo.confirmText"
        :placeholder="`输入仓库名 ${removeRepo.leafName} 以确认`"
      />
      <div v-if="removeRepo.error" class="sync-error">{{ removeRepo.error }}</div>
    </div>
    <template #footer>
      <QButton type="ghost" @click="removeRepo.show = false">取消</QButton>
      <QButton type="danger" :disabled="removeRepo.running || removeRepo.confirmText !== removeRepo.leafName" @click="confirmRemoveRepo">
        {{ removeRepo.running ? '删除中...' : '确认删除' }}
      </QButton>
    </template>
  </QModal>

  <!-- Tooltip portaled to body to escape overflow:hidden -->
  <Teleport to="body">
    <Transition name="qqx-tooltip">
      <div
        v-if="tooltip.sub"
        class="sync-tooltip-body"
        :style="{ top: tooltip.top + 'px', left: tooltip.left + 'px', transform: tooltip.transform }"
      >
        {{ syncTooltipText(tooltip.sub) }}
      </div>
    </Transition>
  </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useData } from '../composables/useData.js'
import { useSkillDetail } from '../composables/useSkillDetail.js'
import { useToast } from '../composables/useToast.js'
import {
  syncSubmodule as syncSubmoduleApi, previewSyncSubmodule as previewSyncApi,
  fixDetachedHead as fixDetachedHeadApi, refreshSubmodule as refreshSubmoduleApi,
  fetchSubmoduleDiff as fetchSubmoduleDiffApi,
  removeSubmodule as removeSubmoduleApi, renameSubmodule as renameSubmoduleApi,
  fetchSyncConfig, executeSync,
} from '../api/index.js'
import { MoreHorizontal, Pencil, Trash2, Download } from 'lucide-vue-next'
import QModal from './QModal.vue'
import QButton from './QButton.vue'
import QInput from './QInput.vue'

function displayPath(p) {
  return p.replace(/^repos\//, '')
}

const { state, remoteUrlMap, refresh } = useData()
const route = useRoute()
const router = useRouter()
const { show } = useSkillDetail()
const toast = useToast()

const syncing = ref(null)
const fixingDetached = ref(null)
const error = ref(null)
const expanded = reactive({})
// Read-only remote check state
const refreshing = ref(null)       // path currently being refreshed, or 'all' during batch
const refreshingAll = ref(false)
const lastBatchCheckAt = ref(null)  // timestamp(ms) of the last batch check
const tooltip = reactive({ sub: null, top: 0, left: 0, transform: '' })

// ── Repo management (rename / remove / install-to-target) ──
const repoMenuOpen = ref(null)        // sub.path whose dropdown is open
const targets = ref([])               // configured sync targets

const installRepo = reactive({ show: false, path: null, skills: [], target: '', running: false, error: '' })
const renameRepo = reactive({ show: false, path: null, newName: '', running: false, error: '' })
const removeRepo = reactive({ show: false, path: null, leafName: '', skillCount: 0, confirmText: '', running: false, error: '' })

const renamePreviewPath = computed(() => {
  if (!renameRepo.path) return ''
  const parts = renameRepo.path.split('/')
  parts[parts.length - 1] = renameRepo.newName.trim() || parts[parts.length - 1]
  return parts.join('/')
})

async function loadTargets() {
  try {
    const config = await fetchSyncConfig()
    targets.value = (config.targets || []).map(t => ({
      name: t.name, path: t.path, label: t.label || t.name,
    }))
  } catch {
    targets.value = []
  }
}

function toggleRepoMenu(path) {
  repoMenuOpen.value = repoMenuOpen.value === path ? null : path
}

function closeRepoMenu() {
  repoMenuOpen.value = null
}

function onDocumentClick(e) {
  if (!e.target.closest('.repo-more-wrapper')) closeRepoMenu()
}

// ── Install repo skills to a target ──
function openInstallRepo(sub) {
  closeRepoMenu()
  installRepo.path = sub.path
  installRepo.skills = (skillsBySubmodule.value[sub.path] || []).slice()
  installRepo.target = targets.value[0]?.path || ''
  installRepo.error = ''
  installRepo.running = false
  installRepo.show = true
}

async function confirmInstallRepo() {
  if (!installRepo.target || !installRepo.skills.length) return
  installRepo.running = true
  installRepo.error = ''
  try {
    const names = installRepo.skills.map(s => s.name)
    const result = await executeSync(installRepo.target, { skills: names })
    if (!result.success) throw new Error(result.stderr || '同步失败')
    installRepo.show = false
    toast.success(`已安装 ${names.length} 个 skill → ${displayPath(installRepo.target)}`)
  } catch (e) {
    installRepo.error = e.message
  } finally {
    installRepo.running = false
  }
}

// ── Rename repo ──
function openRenameRepo(sub) {
  closeRepoMenu()
  renameRepo.path = sub.path
  renameRepo.newName = sub.path.split('/').pop()
  renameRepo.error = ''
  renameRepo.running = false
  renameRepo.show = true
}

async function confirmRenameRepo() {
  const newName = renameRepo.newName.trim()
  if (!newName) return
  if (newName === renameRepo.path.split('/').pop()) {
    renameRepo.show = false
    return
  }
  renameRepo.running = true
  renameRepo.error = ''
  try {
    const result = await renameSubmoduleApi(renameRepo.path, newName)
    if (!result.success) throw new Error(result.error || '重命名失败')
    renameRepo.show = false
    toast.success(`已重命名为 ${displayPath(result.newPath)}`)
    refresh()
  } catch (e) {
    if (e.status === 409) renameRepo.error = `目标名称已存在`
    else renameRepo.error = e.message
  } finally {
    renameRepo.running = false
  }
}

// ── Remove repo ──
function openRemoveRepo(sub) {
  closeRepoMenu()
  removeRepo.path = sub.path
  removeRepo.leafName = sub.path.split('/').pop()
  removeRepo.skillCount = (skillsBySubmodule.value[sub.path] || []).length
  removeRepo.confirmText = ''
  removeRepo.error = ''
  removeRepo.running = false
  removeRepo.show = true
}

async function confirmRemoveRepo() {
  if (removeRepo.confirmText !== removeRepo.leafName) return
  removeRepo.running = true
  removeRepo.error = ''
  try {
    const result = await removeSubmoduleApi(removeRepo.path)
    if (!result.success) throw new Error(result.error || '删除失败')
    removeRepo.show = false
    toast.success(`已删除仓库 ${displayPath(removeRepo.path)}`)
    refresh()
  } catch (e) {
    removeRepo.error = e.message
  } finally {
    removeRepo.running = false
  }
}

onMounted(() => {
  loadTargets()
  document.addEventListener('click', onDocumentClick)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick)
})

// Preview modal state
const previewModal = reactive({ show: false, loading: false, data: null, submodulePath: null, title: '同步确认', confirmLabel: '确认同步' })

// Diff viewer state (within the preview modal, shown when submodule is dirty)
const diffState = reactive({
  loading: false,       // true while fetching diff
  files: [],            // [{ path, status, diff }]
  selectedFile: null,   // path of the file currently shown
  expanded: false,      // whether the diff panel is open
})
// Custom commit message for dirty sync; empty string → backend default 'chore: sync changes'
const commitMessage = ref('')

const TOOLTIP_PAD = 8
const TOOLTIP_EST_W = 320
const TOOLTIP_EST_H = 50

function onTooltipEnter(event, sub) {
  const rect = event.currentTarget.getBoundingClientRect()
  const vw = window.innerWidth
  const vh = window.innerHeight

  // Default: center above trigger element
  let x = rect.left + rect.width / 2
  let y = rect.top - TOOLTIP_PAD
  let tx = '-50%'
  let ty = '-100%'

  // Right edge: flip alignment so right edge snaps to viewport edge
  if (x + TOOLTIP_EST_W / 2 > vw - TOOLTIP_PAD) {
    x = vw - TOOLTIP_PAD
    tx = '-100%'
  }
  // Left edge: clamp
  if (x - TOOLTIP_EST_W / 2 < TOOLTIP_PAD) {
    x = TOOLTIP_PAD
    tx = '0'
  }
  // Top edge: flip below
  if (y - TOOLTIP_EST_H < TOOLTIP_PAD) {
    y = rect.bottom + TOOLTIP_PAD
    ty = '0'
  }

  tooltip.sub = sub
  tooltip.top = y
  tooltip.left = x
  tooltip.transform = `translate(${tx}, ${ty})`
}
function onTooltipLeave() {
  tooltip.sub = null
}

const mainLogs = computed(() => state.gitLogs.main || [])

// Compute skills per submodule
const skillsBySubmodule = computed(() => {
  const map = { main: [] }
  for (const s of state.skills) {
    if (s.isSubmodule) {
      const key = s.submodulePath
      if (!map[key]) map[key] = []
      map[key].push(s)
    }
  }
  return map
})

// Watch query params — auto-expand
watch(() => route.query.submodule, (val) => {
  if (val) expanded[val] = true
}, { immediate: true })

watch(() => route.query.skill, (skillName) => {
  if (skillName) {
    const skill = state.skills.find(s => s.name === skillName)
    if (skill?.submodulePath) expanded[skill.submodulePath] = true
  }
}, { immediate: true })

function navToSkill(skillName) {
  show(skillName)
}

function navToSkillsFiltered(submodulePath) {
  router.push({ name: 'skills', query: { submodule: submodulePath } })
}

function subLogs(path) {
  return state.gitLogs.submodules?.[path] || []
}

function toggle(key) {
  expanded[key] = !expanded[key]
}

function openRepo(url) {
  window.open(url, '_blank')
}

function commitUrl(repoKey, hash) {
  const url = repoKey === 'main' ? remoteUrlMap.value.main : remoteUrlMap.value[repoKey]
  if (!url) return '#'
  return `${url}/commit/${hash}`
}

function relativeTime(isoDate) {
  if (!isoDate) return ''
  const diff = Date.now() - new Date(isoDate).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}天前`
  return `${Math.floor(days / 30)}个月前`
}

// --- Pointer comparison helpers ---

function pointerLabel(sub) {
  const st = sub.status
  if (!st || !st.indexRef) return null
  if (st.indexAhead === 0 && st.indexBehind === 0) return '指针已同步'
  if (st.indexBehind > 0) return `主仓库引用落后 ${st.indexBehind} 个提交`
  if (st.indexAhead > 0) return '本地有未推送提交'
  return null
}

function pointerClass(sub) {
  const st = sub.status
  if (!st || !st.indexRef) return ''
  if (st.indexAhead === 0 && st.indexBehind === 0) return 'pointer-synced'
  if (st.indexBehind > 0) return 'pointer-behind'
  if (st.indexAhead > 0) return 'pointer-ahead'
  return ''
}

// --- Refresh (read-only remote check) helpers ---

// Summary across all submodules after a batch check.
const refreshSummary = computed(() => {
  const subs = state.submodules || []
  const behind = subs.filter(s => s.status?.syncState === 'behind').length
  const ahead = subs.filter(s => s.status?.syncState === 'ahead').length
  const diverged = subs.filter(s => s.status?.syncState === 'diverged').length
  const unknown = subs.filter(s => s.status?.syncState === 'unknown').length
  const dirty = subs.filter(s => s.status?.syncState === 'dirty').length
  return { behind, ahead, diverged, unknown, dirty }
})

function refreshCheckedLabel(sub) {
  const ts = sub.status?.checkedAt
  if (!ts) return '未检查'
  return relativeTime(new Date(ts).toISOString())
}

async function handleRefresh(sub) {
  refreshing.value = sub.path
  error.value = null
  try {
    const result = await refreshSubmoduleApi(sub.path)
    if (result.error) {
      error.value = `${sub.path}: 远程检查失败 — ${result.error}`
    } else {
      // In-place update of the submodule's status within global state.
      const target = state.submodules.find(s => s.path === sub.path)
      if (target && result.status) target.status = result.status
    }
  } catch (e) {
    error.value = `${sub.path}: ${e.message}`
  } finally {
    refreshing.value = null
  }
}

async function handleRefreshAll() {
  refreshingAll.value = true
  error.value = null
  try {
    const result = await refreshSubmoduleApi()
    // result = { results: [{path, status, error}], checkedAt }
    lastBatchCheckAt.value = result.checkedAt
    for (const r of result.results || []) {
      if (r.error) {
        error.value = `${r.path}: 远程检查失败 — ${r.error}`
        continue
      }
      const target = state.submodules.find(s => s.path === r.path)
      if (target && r.status) target.status = r.status
    }
    refresh()
  } catch (e) {
    error.value = `批量检查失败 — ${e.message}`
  } finally {
    refreshingAll.value = false
  }
}

function showSyncButton(sub) {
  const st = sub.status
  // Show when there's actually something to sync:
  // - Submodule is ahead/behind/diverged from origin
  // - Main repo's submodule pointer is behind or ahead of submodule HEAD
  const needsSync = ['ahead', 'behind', 'diverged', 'missing', 'unknown']
  if (needsSync.includes(st.syncState)) return true
  if (st.indexBehind > 0 || st.indexAhead > 0) return true
  if (st.indexDirty) return true
  return false
}

function syncButtonLabel(sub) {
  const st = sub.status
  if (st.syncState === 'diverged') return 'Rebase'
  if (st.syncState === 'ahead') return 'Push'
  return 'Sync'
}

function syncTooltipText(sub) {
  const st = sub.status
  const parts = []
  if (st.syncState === 'diverged') {
    parts.push('本地和远程分叉，将通过 rebase 合并')
  } else if (st.syncState === 'ahead') {
    parts.push('将本地提交推送到远程')
  } else if (st.syncState === 'behind') {
    parts.push('将远程更新拉取到本地')
  } else if (st.syncState === 'missing') {
    parts.push('子模块目录缺失，需要初始化')
  } else {
    parts.push('将子模块与远程同步')
  }
  if (st.indexBehind > 0) {
    parts.push('，并更新主仓库的子模块指针')
  } else if (st.indexAhead > 0) {
    parts.push('，主仓库指针需要更新')
  }
  return parts.join('')
}

function pointerTitle(sub) {
  const st = sub.status
  if (!st || !st.indexRef) return ''
  if (st.indexAhead === 0 && st.indexBehind === 0) return '子模块 HEAD 与主仓库子模块指针一致'
  if (st.indexBehind > 0) return `主仓库中记录的子模块提交 ${st.indexRef?.slice(0, 7)} 落后于子模块当前 HEAD ${st.commit}，需要在主仓库中提交更新`
  if (st.indexAhead > 0) return `子模块 HEAD ${st.commit} 落后于主仓库记录的提交 ${st.indexRef?.slice(0, 7)}`
  return ''
}

// --- Actions ---

async function handleSyncSubmodule(submodule) {
  error.value = null
  previewModal.loading = true
  previewModal.show = true
  previewModal.data = null
  previewModal.submodulePath = submodule.path
  // reset diff + commit message state
  diffState.loading = false
  diffState.files = []
  diffState.selectedFile = null
  diffState.expanded = false
  commitMessage.value = ''
  // Set modal title/button based on sync state
  const st = submodule.status
  if (st.syncState === 'diverged') {
    previewModal.title = 'Rebase 确认'
    previewModal.confirmLabel = '确认 Rebase'
  } else if (st.syncState === 'ahead') {
    previewModal.title = '推送确认'
    previewModal.confirmLabel = '确认推送'
  } else {
    previewModal.title = '同步确认'
    previewModal.confirmLabel = '确认同步'
  }
  try {
    const data = await previewSyncApi(submodule.path)
    previewModal.data = data
    // If dirty, auto-load the diff so the user can review before committing.
    if (data.dirty) await loadDiff(submodule.path)
  } catch (e) {
    previewModal.show = false
    error.value = `${submodule.path}: ${e.message}`
  } finally {
    previewModal.loading = false
  }
}

async function loadDiff(path) {
  diffState.loading = true
  try {
    const data = await fetchSubmoduleDiffApi(path)
    diffState.files = data.files || []
    diffState.selectedFile = diffState.files[0]?.path || null
    diffState.expanded = diffState.files.length > 0
  } catch (e) {
    error.value = `${path}: diff 加载失败 — ${e.message}`
  } finally {
    diffState.loading = false
  }
}

const selectedDiff = computed(() => {
  if (!diffState.selectedFile) return null
  return diffState.files.find(f => f.path === diffState.selectedFile) || null
})

function diffLineClass(line) {
  if (line.startsWith('+') && !line.startsWith('+++')) return 'diff-add'
  if (line.startsWith('-') && !line.startsWith('---')) return 'diff-del'
  if (line.startsWith('@@')) return 'diff-hunk'
  if (line.startsWith('diff ') || line.startsWith('index ')) return 'diff-meta'
  return ''
}

function cancelPreview() {
  previewModal.show = false
  previewModal.data = null
  previewModal.submodulePath = null
  diffState.files = []
  diffState.selectedFile = null
  diffState.expanded = false
  commitMessage.value = ''
}

async function confirmSync() {
  const path = previewModal.submodulePath
  // Only pass a custom message when there are dirty files to commit;
  // otherwise the backend has nothing to commit and the field is irrelevant.
  const msg = previewModal.data?.dirty ? commitMessage.value : ''
  previewModal.show = false
  syncing.value = path
  error.value = null
  try {
    const result = await syncSubmoduleApi(path, msg)
    if (!result.success) throw new Error(result.error)
    refresh()
  } catch (e) {
    error.value = `${path}: ${e.message}`
  } finally {
    syncing.value = null
    previewModal.data = null
    previewModal.submodulePath = null
  }
}

async function handleFixDetached(sub) {
  fixingDetached.value = sub.path
  error.value = null
  try {
    const result = await fixDetachedHeadApi(sub.path)
    if (result.fixed) {
      refresh()
    } else if (!result.success && result.error) {
      throw new Error(result.error)
    }
  } catch (e) {
    error.value = `${sub.path}: ${e.message}`
  } finally {
    fixingDetached.value = null
  }
}
</script>

<style scoped>
.submodule-section {
  margin-bottom: var(--qqx-space-3xl);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  margin-bottom: var(--qqx-space-lg);
}

.section-header h2 {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
}

.remote-scope-hint {
  display: flex;
  flex-wrap: wrap;
  gap: var(--qqx-space-sm) var(--qqx-space-lg);
  margin: calc(-1 * var(--qqx-space-sm)) 0 var(--qqx-space-md);
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
}

.remote-scope-hint strong {
  color: var(--qqx-text-primary);
  font-weight: var(--qqx-font-medium);
}

.count {
  background: var(--qqx-bg-elevated);
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
}

.submodule-list {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-sm);
}

.submodule-card {
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-card);
  overflow: hidden;
  transition: border-color 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.submodule-card.expanded {
  border-color: var(--qqx-brand);
}

.submodule-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  cursor: pointer;
  user-select: none;
  transition: background var(--qqx-transition);
}

.submodule-row:hover {
  background: var(--qqx-bg-hover);
}

.submodule-card.expanded .submodule-row {
  background: var(--qqx-bg-surface);
}

.expand-indicator {
  font-size: 10px;
  color: var(--qqx-text-tertiary);
  flex-shrink: 0;
  width: 12px;
  transition: color var(--qqx-transition);
}

.submodule-card.expanded .expand-indicator {
  color: var(--qqx-brand);
}

.sub-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.sub-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sub-path {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.repo-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  color: var(--qqx-text-tertiary);
  border-radius: var(--qqx-radius-xs);
  cursor: pointer;
  flex-shrink: 0;
  transition: background var(--qqx-transition),
              color var(--qqx-transition);
}

.repo-btn:hover {
  background: var(--qqx-bg-elevated);
  color: var(--qqx-brand);
}

.repo-btn:active {
  transform: scale(0.97);
}

.sub-desc {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sub-branch {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  background: var(--qqx-bg-elevated);
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
  flex-shrink: 0;
}

.sub-sync {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-elevated);
  color: var(--qqx-text-secondary);
  flex-shrink: 0;
}

.sub-sync.synced { color: #10b981; }
.sub-sync.ahead { color: #f59e0b; }
.sub-sync.behind { color: #ef4444; }
.sub-sync.dirty { color: #8b5cf6; }

/* Detached HEAD badge */
.detached-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  padding: 2px 7px;
  border-radius: var(--qqx-radius-full);
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  flex-shrink: 0;
  font-weight: var(--qqx-font-medium);
}

.detached-badge svg {
  flex-shrink: 0;
}

/* Pointer comparison badge */
.pointer-badge {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: var(--qqx-radius-full);
  flex-shrink: 0;
  font-weight: var(--qqx-font-medium);
  white-space: nowrap;
}

.pointer-badge.pointer-synced {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.pointer-badge.pointer-behind {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.pointer-badge.pointer-ahead {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

/* Fix detached HEAD button */
.fix-detached-btn {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
  border: 1px solid #ef4444;
  background: transparent;
  color: #ef4444;
  cursor: pointer;
  flex-shrink: 0;
  transition: background var(--qqx-transition), color var(--qqx-transition);
}

.fix-detached-btn:hover:not(:disabled) {
  background: #ef4444;
  color: #fff;
}

.fix-detached-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.fix-detached-btn:active:not(:disabled) {
  transform: scale(0.97);
}

.commit-count {
  font-size: 10px;
  color: var(--qqx-text-tertiary);
  background: var(--qqx-bg-elevated);
  padding: 1px 6px;
  border-radius: var(--qqx-radius-full);
  flex-shrink: 0;
}

/* Sync button wrapper with tooltip */
.sync-btn-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
}

.sync-btn {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: var(--qqx-radius-full);
  border: none;
  background: var(--qqx-brand-fill-bg);
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity var(--qqx-transition);
}

.sync-btn:hover:not(:disabled) { opacity: 0.85; }
.sync-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.sync-btn:active:not(:disabled) { transform: scale(0.97); }

/* --- Read-only remote check --- */
/* QButton handles colors/border/radius; here we only override layout. */
.refresh-all-btn {
  margin-left: auto;
}

.refresh-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--qqx-space-sm);
  margin-bottom: var(--qqx-space-md);
  font-size: 12px;
}
.refresh-summary-time { color: var(--qqx-text-secondary); }
.refresh-pill {
  padding: 2px var(--qqx-space-sm);
  border-radius: var(--qqx-radius-full);
  font-size: 12px;
  font-weight: 500;
  background: var(--qqx-brand-light);
}
.refresh-pill.behind { color: #ef4444; }
.refresh-pill.ahead { color: #f59e0b; }
.refresh-pill.diverged { color: #ef4444; }
.refresh-pill.dirty { color: #8b5cf6; }
.refresh-pill.unknown { color: var(--qqx-text-tertiary); }
.refresh-pill.synced { color: #10b981; }

/* Single-row refresh: compact icon button */
.refresh-btn {
  padding: 0 var(--qqx-space-sm);
  line-height: 1.5;
}

.checked-at {
  font-size: 11px;
  color: var(--qqx-text-tertiary);
  white-space: nowrap;
}

/* --- Dirty diff viewer (inside preview modal) --- */
.sync-diff-section {
  margin-top: var(--qqx-space-md);
  border-top: 1px solid var(--qqx-border-color);
  padding-top: var(--qqx-space-sm);
}
.sync-diff-header {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-xs);
  cursor: pointer;
  font-size: 13px;
  color: var(--qqx-text-secondary);
  user-select: none;
}
.sync-diff-toggle { width: 12px; }
.sync-diff-loading { margin-left: auto; color: var(--qqx-text-tertiary); }
.sync-diff-body {
  margin-top: var(--qqx-space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-sm);
}
.sync-diff-file-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--qqx-space-xs);
}
.sync-diff-file {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px var(--qqx-space-sm);
  font-size: 12px;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  background: transparent;
  color: var(--qqx-text-secondary);
  cursor: pointer;
  max-width: 100%;
}
.sync-diff-file.active {
  border-color: var(--qqx-brand);
  color: var(--qqx-brand);
  background: var(--qqx-brand-light);
}
.sync-diff-file-status {
  font-weight: 600;
  flex-shrink: 0;
}
.sync-diff-file.modified .sync-diff-file-status { color: #f59e0b; }
.sync-diff-file.added .sync-diff-file-status { color: #10b981; }
.sync-diff-file.deleted .sync-diff-file-status { color: #ef4444; }
.sync-diff-file.renamed .sync-diff-file-status { color: var(--qqx-brand); }
.sync-diff-file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sync-diff-content {
  margin: 0;
  padding: var(--qqx-space-sm);
  max-height: 320px;
  overflow: auto;
  font-family: var(--qqx-font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
  font-size: 12px;
  line-height: 1.5;
  background: var(--qqx-bg-elevated, #f6f8fa);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
}
.sync-diff-content code {
  display: block;
  white-space: pre-wrap;
  word-break: break-all;
}
.sync-diff-content code.diff-add { color: #1a7f37; background: rgba(26,127,55,0.08); }
.sync-diff-content code.diff-del { color: #cf222e; background: rgba(207,34,46,0.08); }
.sync-diff-content code.diff-hunk { color: var(--qqx-brand); }
.sync-diff-content code.diff-meta { color: var(--qqx-text-tertiary); }

/* --- Custom commit message input --- */
.sync-commit-msg {
  margin-top: var(--qqx-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-xs);
}
.sync-commit-label {
  font-size: 12px;
  color: var(--qqx-text-secondary);
}

.info-icon {
  color: var(--qqx-text-tertiary);
  flex-shrink: 0;
  cursor: help;
  transition: color var(--qqx-transition);
}

.info-icon:hover {
  color: var(--qqx-brand);
}

.sync-tooltip-body {
  position: fixed;
  background: var(--qqx-text-primary);
  color: var(--qqx-bg-card);
  font-size: 11px;
  padding: 6px 10px;
  border-radius: var(--qqx-radius-sm);
  white-space: nowrap;
  z-index: var(--z-tooltip);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  line-height: 1.5;
  pointer-events: none;
}

/* Micro-animation: fade (qqx pattern, opacity-only to avoid conflict with dynamic transform) */
.qqx-tooltip-enter-active {
  transition: opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}
.qqx-tooltip-leave-active {
  transition: opacity 0.1s cubic-bezier(0.4, 0, 0.2, 1);
}
.qqx-tooltip-enter-from,
.qqx-tooltip-leave-to {
  opacity: 0;
}

/* Commit panel */
.commit-panel {
  border-top: 1px solid var(--qqx-border-color);
  background: var(--qqx-bg-surface);
  max-height: 320px;
  overflow-y: auto;
}

.commit-entry {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  padding: 6px 16px 6px 40px;
  border-bottom: 1px solid var(--qqx-border-color);
  font-size: var(--qqx-font-size-small);
}

.commit-entry:last-child {
  border-bottom: none;
}

.commit-entry:hover {
  background: var(--qqx-bg-hover);
}

.commit-hash {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  color: var(--qqx-brand);
  text-decoration: none;
  flex-shrink: 0;
}

.commit-hash:hover {
  text-decoration: underline;
}

.commit-msg {
  flex: 1;
  color: var(--qqx-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.commit-time {
  font-size: 11px;
  color: var(--qqx-text-tertiary);
  flex-shrink: 0;
}

.commit-empty {
  padding: 12px 40px;
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
}

.sync-error {
  font-size: var(--qqx-font-size-small);
  color: #ef4444;
  margin-bottom: var(--qqx-space-md);
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  background: rgba(239, 68, 68, 0.08);
  border-radius: var(--qqx-radius-sm);
}

/* Skills section in expanded panel */
.skill-count-badge {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
  cursor: pointer;
  flex-shrink: 0;
  transition: filter 0.15s ease;
}
.skill-count-badge:hover { filter: brightness(0.92); }

.skills-section {
  border-bottom: 1px solid var(--qqx-border-color);
  padding: 8px 16px 8px 40px;
  background: var(--qqx-bg-surface);
}
.skills-section-label {
  font-size: 11px;
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-tertiary);
  text-transform: uppercase;
  margin-bottom: 4px;
}
.skill-item {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  padding: 2px 0;
  cursor: pointer;
  border-radius: var(--qqx-radius-xs);
  transition: background var(--qqx-transition);
}
.skill-item:hover {
  background: var(--qqx-bg-hover);
}
.skill-item-name {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-brand);
  font-weight: var(--qqx-font-medium);
}
.skill-item-type {
  font-size: 10px;
  color: var(--qqx-text-tertiary);
  background: var(--qqx-bg-elevated);
  padding: 0 4px;
  border-radius: var(--qqx-radius-full);
}

/* Repo management dropdown */
.repo-more-wrapper {
  position: relative;
  flex-shrink: 0;
}

.repo-more-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--qqx-text-tertiary);
  border-radius: var(--qqx-radius-xs);
  cursor: pointer;
  transition: background var(--qqx-transition), color var(--qqx-transition);
}

.repo-more-btn:hover,
.repo-more-btn--open {
  background: var(--qqx-bg-elevated);
  color: var(--qqx-brand);
}

.repo-dropdown {
  position: absolute;
  top: 28px;
  right: 0;
  z-index: var(--z-dropdown, 200);
  min-width: 168px;
  padding: 4px;
  background: var(--qqx-bg-card);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-sm);
  box-shadow: var(--qqx-shadow-dropdown);
  animation: repo-menu-in 0.12s ease-out;
}

@keyframes repo-menu-in {
  from { opacity: 0; transform: scale(0.96); }
  to { opacity: 1; transform: scale(1); }
}

.repo-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-small);
  font-family: inherit;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s ease;
}

.repo-dropdown-item:hover {
  background: var(--qqx-bg-hover);
}

.repo-dropdown-item--danger {
  color: #ef4444;
}

.repo-dropdown-item--danger:hover {
  background: rgba(239, 68, 68, 0.1);
}

/* Repo install / rename / remove modal bodies */
.repo-install-desc,
.repo-remove-text {
  font-size: var(--qqx-font-size-body);
  color: var(--qqx-text-primary);
  line-height: 1.6;
  margin-bottom: var(--qqx-space-md);
}

.repo-install-targets {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-xs);
  max-height: 280px;
  overflow-y: auto;
}

.repo-install-target-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-sm);
  cursor: pointer;
  transition: all var(--qqx-transition);
}

.repo-install-target-row--selected {
  border-color: var(--qqx-brand);
  background: var(--qqx-brand-light);
}

.repo-install-target-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.repo-install-target-name {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.repo-install-target-path {
  font-size: 11px;
  color: var(--qqx-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.repo-install-skill-hint {
  margin-top: var(--qqx-space-md);
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  line-height: 1.5;
}

.repo-rename-body,
.repo-remove-body {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

.repo-remove-body {
  align-items: center;
  text-align: center;
}

.repo-remove-warn-icon {
  color: #ef4444;
}

.repo-remove-hint {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-xs);
}

.form-label {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
}

.form-static-value {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  color: var(--qqx-text-primary);
  background: var(--qqx-bg-elevated);
  padding: 6px 10px;
  border-radius: var(--qqx-radius-xs);
  word-break: break-all;
}

.form-hint {
  font-size: 11px;
  color: var(--qqx-text-tertiary);
}

.form-hint code {
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--qqx-brand);
}

/* Sync preview modal body content */
.sync-preview-loading {
  text-align: center;
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-body);
  padding: 12px 0;
}

.sync-preview-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.sync-preview-sub-name {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.sync-preview-sub-branch {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  background: var(--qqx-bg-elevated);
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
}

.sync-preview-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sync-preview-action {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: var(--qqx-font-size-body);
  color: var(--qqx-text-primary);
}

.sync-preview-action-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-brand);
  background: var(--qqx-brand-light);
  border-radius: var(--qqx-radius-full);
  flex-shrink: 0;
}

.sync-preview-warnings {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--qqx-border-color);
}

.sync-preview-warning {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: var(--qqx-font-size-small);
  color: #f59e0b;
  line-height: 1.5;
}

.sync-preview-warning svg {
  flex-shrink: 0;
  margin-top: 1px;
}

@media (max-width: 767px) {
  .submodule-row {
    flex-wrap: wrap;
  }
  .commit-entry {
    padding-left: 16px;
  }
}
</style>
