<template>
  <div class="pm-root">
    <!-- Header -->
    <div class="pm-header">
      <div class="pm-header-left">
        <h2 class="pm-title">项目组管理</h2>
        <span class="pm-count" v-if="!loading">{{ projects.length }} 个项目</span>
      </div>
      <div class="pm-header-actions">
        <QButton type="ghost" size="small" @click="loadProjects"><RefreshCw :size="14" /> 刷新</QButton>
        <QButton type="primary" size="small" @click="openCreate">+ 新建项目</QButton>
      </div>
    </div>

    <div v-if="error" class="pm-error">{{ error }}</div>
    <div v-if="loading" class="pm-loading">加载中...</div>

    <!-- Empty state -->
    <div v-if="!loading && !projects.length" class="pm-empty">
      <div class="pm-empty-icon">
        <FolderKanban :size="48" />
      </div>
      <p class="pm-empty-title">暂无项目组</p>
      <p class="pm-empty-desc">创建项目组，将多个业务仓库目录绑定在一起，一次 Sync 同步到所有目录。</p>
      <QButton type="primary" size="medium" @click="openCreate">创建第一个项目</QButton>
    </div>

    <!-- Project cards -->
    <div v-if="projects.length" class="pm-list">
      <div v-for="proj in projects" :key="proj.id" class="pm-card" :class="{ 'pm-card--expanded': expanded === proj.id }">
        <div class="pm-card-header" @click="toggleExpand(proj.id)">
          <div class="pm-card-title">
            <span class="pm-card-icon"><FolderKanban :size="16" /></span>
            <h3>{{ proj.name }}</h3>
            <span class="pm-card-target-count">{{ proj.targets?.length || 0 }} 个目标</span>
          </div>
          <div class="pm-card-header-actions" @click.stop>
            <QButton type="ghost" size="small" @click="goToSyncTool(proj)" title="跳转到 Sync 工具查看同步状态">
              <RefreshCw :size="14" /> 去同步
            </QButton>
            <QButton type="ghost" size="small" @click="expandTargetAdder(proj)">+ 添加目标</QButton>
            <QButton type="secondary" tint="danger" size="small" :disabled="deleting === proj.id" @click="confirmDelete(proj)">
              {{ deleting === proj.id ? '删除中...' : '删除' }}
            </QButton>
          </div>
        </div>

        <!-- Expanded: target list -->
        <div v-if="expanded === proj.id" class="pm-card-body">
          <!-- Inline add target -->
          <div v-if="addingTarget === proj.id" class="pm-add-target-row">
            <input
              ref="addTargetInput"
              v-model="newTargetPath"
              class="pm-target-input"
              placeholder="项目根目录路径，例如: ~/Code/NTComposeBiz（自动发现 .claude/skills 等）"
              @keydown.enter="addTarget(proj)"
            />
            <QButton type="primary" size="small" :disabled="!newTargetPath.trim()" @click="addTarget(proj)">确认</QButton>
            <QButton type="text" size="small" @click="addingTarget = null">取消</QButton>
          </div>

          <div v-if="!proj.targets?.length && addingTarget !== proj.id" class="pm-no-targets">
            暂无目标目录，点击上方"+ 添加目标"按钮添加
          </div>

          <div v-for="(t, ti) in proj.targets" :key="ti" class="pm-target-row">
            <span class="pm-target-idx">{{ ti + 1 }}</span>
            <span class="pm-target-path" :title="t">{{ t }}</span>
            <button
              class="pm-target-remove"
              :disabled="removingTarget === `${proj.id}:${ti}`"
              @click="removeTarget(proj, t, ti)"
              title="移除此目标"
            >
              <X :size="14" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Project Modal -->
    <QModal v-model="createOpen" title="新建项目组" width="520px">
      <div class="pm-form">
        <div class="pm-form-field">
          <label class="pm-form-label">项目名称</label>
          <input
            v-model="createForm.name"
            class="pm-form-input"
            placeholder="例如: NTComposeBiz"
            @keydown.enter="focusFirstTarget"
          />
        </div>
        <div class="pm-form-field">
          <label class="pm-form-label">目标目录（可添加多个）</label>
          <div class="pm-target-inputs">
            <div v-for="(t, idx) in createForm.targets" :key="idx" class="pm-target-input-row">
              <input
                :ref="el => { if (el) targetRefs[idx] = el }"
                v-model="createForm.targets[idx]"
                class="pm-form-input"
                placeholder="例如: ~/Code/NTComposeBiz（自动发现 .claude/skills 等）"
                @keydown.enter.prevent="idx === createForm.targets.length - 1 ? addCreateTarget() : focusNextTarget(idx)"
              />
              <button
                v-if="createForm.targets.length > 1"
                class="pm-target-input-remove"
                @click="removeCreateTarget(idx)"
              >
                <X :size="14" />
              </button>
            </div>
          </div>
          <QButton type="ghost" size="small" @click="addCreateTarget">+ 添加目录</QButton>
        </div>
        <div v-if="createError" class="pm-error">{{ createError }}</div>
      </div>
      <template #footer>
        <QButton type="secondary" size="small" @click="createOpen = false">取消</QButton>
        <QButton type="primary" size="small" :disabled="!canCreate || creating" @click="doCreate">
          {{ creating ? '创建中...' : '创建项目' }}
        </QButton>
      </template>
    </QModal>

    <!-- Delete Confirmation Modal -->
    <QModal v-model="deleteOpen" title="确认删除项目组" width="420px">
      <div class="pm-delete-body">
        <p>确定要删除项目组 <strong>{{ deleteTarget?.name }}</strong> 吗？</p>
        <p class="pm-delete-note">这只会移除本地的项目组配置，不会影响任何目标目录中的 skill 文件。</p>
        <div v-if="deleteError" class="pm-error">{{ deleteError }}</div>
      </div>
      <template #footer>
        <QButton type="secondary" size="small" @click="deleteOpen = false">取消</QButton>
        <QButton type="danger" size="small" :disabled="deleting" @click="doDelete">
          {{ deleting ? '删除中...' : '确认删除' }}
        </QButton>
      </template>
    </QModal>

    <!-- Sync Result -->
    <QModal v-model="syncResultOpen" title="同步结果" width="480px">
      <div class="pm-sync-results">
        <div v-for="r in syncResults" :key="r.target" class="pm-sync-result-row" :class="{ 'pm-sync-result--fail': r.error }">
          <span class="pm-sync-result-target">{{ r.target }}</span>
          <span v-if="r.error" class="pm-sync-result-error">{{ r.error }}</span>
          <span v-else class="pm-sync-result-ok">OK</span>
        </div>
      </div>
      <template #footer>
        <QButton type="secondary" size="small" @click="syncResultOpen = false">关闭</QButton>
      </template>
    </QModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { FolderKanban, X, RefreshCw } from 'lucide-vue-next'
import QCard from './QCard.vue'
import QButton from './QButton.vue'
import QModal from './QModal.vue'
import { fetchProjects, createProject, executeSync } from '../api/index.js'

const projects = ref([])
const loading = ref(true)
const error = ref(null)
const expanded = ref(null)
const syncing = ref(null)
const deleting = ref(null)
const router = useRouter()

function goToSyncTool(proj) {
  router.push({ path: '/sync', query: { view: 'projects', project: proj.id } })
}

// Inline add target
const addingTarget = ref(null)
const newTargetPath = ref('')
const removingTarget = ref(null)
const addTargetInput = ref(null)

// Create modal
const createOpen = ref(false)
const creating = ref(false)
const createError = ref('')
const createForm = ref({ name: '', targets: [''] })
const targetRefs = ref({})

const canCreate = computed(() => {
  const name = createForm.value.name.trim()
  const targets = createForm.value.targets.filter(t => t.trim())
  return name && targets.length > 0
})

// Delete confirmation
const deleteOpen = ref(false)
const deleteTarget = ref(null)
const deleteError = ref('')

// Sync results
const syncResultOpen = ref(false)
const syncResults = ref([])

async function loadProjects() {
  loading.value = true
  error.value = null
  try {
    projects.value = await fetchProjects()
  } catch (e) {
    error.value = '加载项目列表失败: ' + e.message
  } finally {
    loading.value = false
  }
}

function toggleExpand(id) {
  expanded.value = expanded.value === id ? null : id
}

// --- Create ---

function openCreate() {
  createForm.value = { name: '', targets: [''] }
  createError.value = ''
  createOpen.value = true
}

function addCreateTarget() {
  createForm.value.targets.push('')
}

function removeCreateTarget(idx) {
  createForm.value.targets.splice(idx, 1)
}

function focusFirstTarget() {
  nextTick(() => {
    const el = targetRefs.value[0]
    if (el) el.focus()
  })
}

function focusNextTarget(idx) {
  nextTick(() => {
    const el = targetRefs.value[idx + 1]
    if (el) el.focus()
  })
}

async function doCreate() {
  creating.value = true
  createError.value = ''
  try {
    const data = await createProject(
      createForm.value.name.trim(),
      createForm.value.targets.filter(t => t.trim()),
    )
    if (data.error) throw new Error(data.error)
    createOpen.value = false
    await loadProjects()
  } catch (e) {
    createError.value = e.message
  } finally {
    creating.value = false
  }
}

// --- Add target to existing project ---

function expandTargetAdder(proj) {
  expanded.value = proj.id
  addingTarget.value = proj.id
  newTargetPath.value = ''
  nextTick(() => {
    if (addTargetInput.value) addTargetInput.value.focus()
  })
}

async function addTarget(proj) {
  const path = newTargetPath.value.trim()
  if (!path) return
  try {
    const res = await fetch(`/api/sync/projects/${encodeURIComponent(proj.id)}/targets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    })
    const data = await res.json()
    if (!res.ok || data.error) throw new Error(data.error || res.statusText)
    addingTarget.value = null
    newTargetPath.value = ''
    await loadProjects()
    expanded.value = proj.id // keep expanded
  } catch (e) {
    error.value = '添加目标失败: ' + e.message
  }
}

// --- Remove target ---

async function removeTarget(proj, path, idx) {
  removingTarget.value = `${proj.id}:${idx}`
  try {
    const res = await fetch(`/api/sync/projects/${encodeURIComponent(proj.id)}/targets`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    })
    const data = await res.json()
    if (!res.ok || data.error) throw new Error(data.error || res.statusText)
    await loadProjects()
    expanded.value = proj.id // keep expanded
  } catch (e) {
    error.value = '移除目标失败: ' + e.message
  } finally {
    removingTarget.value = null
  }
}

// --- Delete project ---

function confirmDelete(proj) {
  deleteTarget.value = proj
  deleteError.value = ''
  deleteOpen.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = deleteTarget.value.id
  deleteError.value = ''
  try {
    const res = await fetch(`/api/sync/projects/${encodeURIComponent(deleteTarget.value.id)}`, {
      method: 'DELETE',
    })
    const data = await res.json()
    if (!res.ok || data.error) throw new Error(data.error || res.statusText)
    deleteOpen.value = false
    expanded.value = null
    await loadProjects()
  } catch (e) {
    deleteError.value = e.message
  } finally {
    deleting.value = null
  }
}

// --- Sync project ---

async function syncProject(proj) {
  syncing.value = proj.id
  error.value = null
  syncResults.value = []
  const results = []
  try {
    for (const target of (proj.targets || [])) {
      try {
        const data = await executeSync(target)
        if (data.error || !data.success) {
          results.push({ target, error: data.error || '同步失败' })
        } else {
          results.push({ target, error: null })
        }
      } catch (e) {
        results.push({ target, error: e.message })
      }
    }
  } catch (e) {
    error.value = '项目同步出错: ' + e.message
  } finally {
    syncing.value = null
    syncResults.value = results
    const hasError = results.some(r => r.error)
    if (hasError || results.length > 1) {
      syncResultOpen.value = true
    } else if (results.length === 1 && results[0].error) {
      error.value = `同步 ${results[0].target}: ${results[0].error}`
    }
  }
}

onMounted(() => { loadProjects() })
</script>

<style scoped>
.pm-root {
  /* container */
}

.pm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--qqx-space-xl);
  flex-wrap: wrap;
  gap: var(--qqx-space-sm);
}

.pm-header-left {
  display: flex;
  align-items: baseline;
  gap: var(--qqx-space-md);
}

.pm-title {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  margin: 0;
}

.pm-count {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
}

.pm-header-actions {
  display: flex;
  gap: var(--qqx-space-sm);
  align-items: center;
}

.pm-error {
  color: #ef4444;
  font-size: var(--qqx-font-size-small);
  margin-bottom: var(--qqx-space-md);
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  background: rgba(239, 68, 68, 0.08);
  border-radius: var(--qqx-radius-sm);
}

.pm-loading {
  color: var(--qqx-text-tertiary);
  text-align: center;
  padding: var(--qqx-space-xl);
}

/* Empty state */
.pm-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  gap: var(--qqx-space-md);
  text-align: center;
}

.pm-empty-icon {
  color: var(--qqx-text-tertiary);
  opacity: 0.5;
}

.pm-empty-title {
  font-size: var(--qqx-font-size-body);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  margin: 0;
}

.pm-empty-desc {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  max-width: 420px;
  line-height: 1.6;
  margin: 0;
}

/* Cards */
.pm-list {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

.pm-card {
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-card);
  overflow: hidden;
}

.pm-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  cursor: pointer;
  transition: background var(--qqx-transition);
  user-select: none;
}

.pm-card-header:hover {
  background: var(--qqx-bg-hover);
}

.pm-card-title {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
}

.pm-card-icon {
  color: var(--qqx-brand);
  display: flex;
}

.pm-card-title h3 {
  font-size: var(--qqx-font-size-body);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  margin: 0;
}

.pm-card-target-count {
  font-size: 11px;
  color: var(--qqx-text-tertiary);
  background: var(--qqx-bg-elevated);
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
}

.pm-card-header-actions {
  display: flex;
  gap: var(--qqx-space-xs);
  align-items: center;
}

.pm-card-body {
  border-top: 1px solid var(--qqx-border-color);
  padding: var(--qqx-space-md) var(--qqx-space-lg);
}

.pm-no-targets {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  padding: var(--qqx-space-md) 0;
}

/* Target rows */
.pm-target-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  padding: 6px 0;
}

.pm-target-row + .pm-target-row {
  border-top: 1px solid var(--qqx-border-color);
}

.pm-target-idx {
  width: 22px;
  font-size: 11px;
  color: var(--qqx-text-tertiary);
  text-align: center;
  flex-shrink: 0;
}

.pm-target-path {
  flex: 1;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  font-family: 'SF Mono', 'Fira Code', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pm-target-remove {
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
  flex-shrink: 0;
  transition: color var(--qqx-transition), background var(--qqx-transition);
}

.pm-target-remove:hover:not(:disabled) {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}

.pm-target-remove:disabled {
  opacity: 0.4;
}

/* Add target inline */
.pm-add-target-row {
  display: flex;
  gap: var(--qqx-space-sm);
  align-items: center;
  margin-bottom: var(--qqx-space-md);
  padding-bottom: var(--qqx-space-md);
  border-bottom: 1px solid var(--qqx-border-color);
}

.pm-target-input {
  flex: 1;
  padding: 6px var(--qqx-space-md);
  border: 1px solid var(--qqx-input-border);
  border-radius: var(--qqx-radius-xs);
  background: var(--qqx-input-bg);
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-small);
  font-family: 'SF Mono', 'Fira Code', monospace;
  height: 32px;
  transition: border-color var(--qqx-transition);
}

.pm-target-input:focus {
  outline: none;
  border-color: var(--qqx-brand);
  box-shadow: var(--qqx-shadow-focus);
}

/* Form */
.pm-form {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-lg);
}

.pm-form-field {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-xs);
}

.pm-form-label {
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-secondary);
}

.pm-form-input {
  padding: var(--qqx-space-xs) var(--qqx-space-md);
  border: 1px solid var(--qqx-input-border);
  border-radius: var(--qqx-radius-xs);
  background: var(--qqx-input-bg);
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-label);
  font-family: inherit;
  height: 40px;
  transition: border-color var(--qqx-transition);
}

.pm-form-input:focus {
  outline: none;
  border-color: var(--qqx-brand);
  box-shadow: var(--qqx-shadow-focus);
}

.pm-target-inputs {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-sm);
}

.pm-target-input-row {
  display: flex;
  gap: var(--qqx-space-sm);
  align-items: center;
}

.pm-target-input-row .pm-form-input {
  flex: 1;
}

.pm-target-input-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--qqx-text-tertiary);
  border-radius: var(--qqx-radius-xs);
  cursor: pointer;
  flex-shrink: 0;
}

.pm-target-input-remove:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}

/* Delete confirmation */
.pm-delete-body {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

.pm-delete-body p {
  margin: 0;
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-secondary);
}

.pm-delete-note {
  font-size: var(--qqx-font-size-small) !important;
  color: var(--qqx-text-tertiary) !important;
}

/* Sync results */
.pm-sync-results {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 40vh;
  overflow-y: auto;
}

.pm-sync-result-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px var(--qqx-space-sm);
  border-radius: var(--qqx-radius-xs);
  font-size: var(--qqx-font-size-small);
}

.pm-sync-result-row.pm-sync-result--fail {
  background: rgba(239, 68, 68, 0.06);
}

.pm-sync-result-target {
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--qqx-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: var(--qqx-space-sm);
}

.pm-sync-result-error {
  color: #ef4444;
  font-size: 12px;
  flex-shrink: 0;
}

.pm-sync-result-ok {
  color: #10b981;
  font-weight: var(--qqx-font-semibold);
  flex-shrink: 0;
}
</style>
