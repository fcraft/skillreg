<template>
  <div
    ref="cardEl"
    :data-skill-name="skill.name"
    class="skill-card"
    :class="{ 'is-pressed': pressed }"
    @mousedown="pressed = true"
    @mouseup="pressed = false"
    @mouseleave="onMouseLeave"
    @touchstart="pressed = true"
    @touchend="pressed = false"
    @touchcancel="pressed = false"
    @click="handleClick"
    @contextmenu.prevent="openContextMenu"
  >
    <div class="card-header">
      <div class="card-title">
        <span class="category-dot" :style="{ background: typeColor }"></span>
        <h3>{{ skill.name }}</h3>
        <button
          v-if="skill.isSubmodule && skill.remoteUrl"
          class="repo-link-btn"
          :title="'打开仓库: ' + skill.remoteUrl"
          @click.stop="openRepo"
        >
          <GitBranchIcon :size="14" />
        </button>
      </div>
      <div class="card-tags">
        <SubmoduleBadge v-if="skill.isSubmodule" :submodule-path="skill.submodulePath" />
        <span class="type-icon" :title="skill.type === 'CLI' ? 'CLI 工具' : '参考文档'">
          <TerminalIcon v-if="skill.type === 'CLI'" :size="14" />
          <BookOpenIcon v-else :size="14" />
        </span>
      </div>
    </div>
    <p class="card-desc">{{ skill.description }}</p>
    <div class="card-meta">
      <span>{{ skill.fileCount || 0 }} files</span>
      <span>{{ skill.path.replace(/^(skills|repos)\//, '') }}</span>
    </div>

    <!-- Context menu -->
    <Teleport to="body">
      <div
        v-if="menuVisible"
        class="card-context-menu"
        :style="menuStyle"
        @click.stop
      >
        <button class="ctx-item ctx-item--primary" @click="handleInstall">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span>安装</span>
        </button>
        <button v-if="skill.type === 'Reference'" class="ctx-item" @click="handleUpdate">
          <RefreshCwIcon :size="16" />
          <span>更新</span>
        </button>
        <button class="ctx-item" @click="handleExport">
          <DownloadIcon :size="16" />
          <span>导出</span>
        </button>
        <template v-if="!skill.isSubmodule">
          <div class="ctx-sep"></div>
          <button class="ctx-item ctx-item--danger" @click="handleDelete">
            <Trash2Icon :size="16" />
            <span>删除</span>
          </button>
        </template>
        <div class="ctx-sep"></div>
        <button class="ctx-item" @click="handleClick">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 16 12 12"/>
            <polyline points="12 8 12.01 8"/>
          </svg>
          <span>查看详情</span>
        </button>
      </div>
    </Teleport>

    <SkillImportModal
      v-if="showUpdateModal"
      v-model="showUpdateModal"
      :existing-skill-name="skill.name"
      @imported="onUpdateComplete"
    />

    <!-- Delete confirmation -->
    <QModal v-model="showDeleteModal" title="删除 Skill" width="440px">
      <div class="delete-confirm-body">
        <div class="delete-warn-icon"><TriangleAlertIcon :size="34" /></div>
        <p class="delete-warn-text">
          确认从 workspace 删除 <strong>{{ skill.name }}</strong>？
          此操作会删除磁盘上的 <code>{{ skill.path }}</code> 目录并提交，无法通过本工具恢复。
        </p>
        <p class="delete-warn-hint">已安装到各 target 的副本不受影响。</p>
        <div v-if="deleteError" class="delete-error">{{ deleteError }}</div>
      </div>
      <template #footer>
        <QButton type="secondary" size="small" @click="showDeleteModal = false">取消</QButton>
        <QButton type="danger" size="small" :disabled="deleting" @click="doDelete">
          {{ deleting ? '删除中...' : '确认删除' }}
        </QButton>
      </template>
    </QModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RefreshCw as RefreshCwIcon, Download as DownloadIcon, Terminal as TerminalIcon, BookOpen as BookOpenIcon, GitBranch as GitBranchIcon, Trash2 as Trash2Icon, TriangleAlert as TriangleAlertIcon } from 'lucide-vue-next'
import { useSkillDetail } from '../composables/useSkillDetail.js'
import { useData } from '../composables/useData.js'
import { useToast } from '../composables/useToast.js'
import { exportSkill, deleteSkill } from '../api/index.js'
import SubmoduleBadge from './SubmoduleBadge.vue'
import SkillImportModal from './SkillImportModal.vue'
import QModal from './QModal.vue'
import QButton from './QButton.vue'

const { show: showDetail } = useSkillDetail()
const { refresh } = useData()
const toast = useToast()
const pressed = ref(false)
const showUpdateModal = ref(false)

// Delete state
const showDeleteModal = ref(false)
const deleting = ref(false)
const deleteError = ref('')

const props = defineProps({
  skill: { type: Object, required: true }
})

function handleClick() {
  showDetail(props.skill.name)
}

function handleDelete() {
  menuVisible.value = false
  deleteError.value = ''
  deleting.value = false
  showDeleteModal.value = true
}

async function doDelete() {
  deleting.value = true
  deleteError.value = ''
  try {
    await deleteSkill(props.skill.name)
    showDeleteModal.value = false
    toast.success(`已删除 ${props.skill.name}`)
    refresh()
  } catch (e) {
    deleteError.value = e.message || '删除失败'
  } finally {
    deleting.value = false
  }
}

function handleInstall() {
  menuVisible.value = false
  showDetail(props.skill.name, { tab: 'install' })
}

function openRepo() {
  window.open(props.skill.remoteUrl, '_blank')
}

function handleUpdate() {
  menuVisible.value = false
  showUpdateModal.value = true
}

const exporting = ref(false)

async function handleExport() {
  menuVisible.value = false
  if (exporting.value) return
  exporting.value = true
  try {
    await exportSkill(props.skill.name)
  } catch (e) {
    console.error('Export failed:', e)
  } finally {
    exporting.value = false
  }
}

function onUpdateComplete() {
  showUpdateModal.value = false
  refresh()
}

function onMouseLeave() {
  pressed.value = false
}

// ── Context menu ──

const menuVisible = ref(false)
const menuX = ref(0)
const menuY = ref(0)
const cardEl = ref(null)

const menuStyle = computed(() => ({
  left: `${menuX.value}px`,
  top: `${menuY.value}px`,
}))

function openContextMenu(e) {
  menuX.value = e.clientX
  menuY.value = e.clientY
  menuVisible.value = true
}

function closeContextMenu() {
  menuVisible.value = false
}

function onGlobalClick(e) {
  if (menuVisible.value) {
    closeContextMenu()
  }
}

function onGlobalScroll() {
  if (menuVisible.value) {
    closeContextMenu()
  }
}

function onGlobalKeydown(e) {
  if (e.key === 'Escape' && menuVisible.value) {
    closeContextMenu()
  }
}

onMounted(() => {
  window.addEventListener('click', onGlobalClick, true)
  window.addEventListener('scroll', onGlobalScroll, true)
  window.addEventListener('keydown', onGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('click', onGlobalClick, true)
  window.removeEventListener('scroll', onGlobalScroll, true)
  window.removeEventListener('keydown', onGlobalKeydown)
})

const TYPE_COLORS = {
  CLI: '#6366f1',
  Reference: '#10b981'
}

const typeColor = computed(() => TYPE_COLORS[props.skill.type] || '#6b7280')
</script>


<style scoped>
.skill-card {
  position: relative;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  padding: var(--qqx-space-lg);
  margin-bottom: 0;
  background: var(--qqx-bg-card);
  cursor: pointer;
  z-index: 0;
  transform: scale(1);
  transition: border-color var(--qqx-transition),
              box-shadow var(--qqx-transition),
              transform 150ms ease-out;
  user-select: none;
  touch-action: manipulation;
  box-shadow: none;
  overflow: visible;
}

.skill-card:hover {
  border-color: var(--qqx-brand);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.skill-card.is-pressed {
  transform: scale(0.97);
  transition: border-color var(--qqx-transition),
              box-shadow var(--qqx-transition),
              transform 100ms cubic-bezier(0.4, 0.0, 0.2, 1.0);
}

.skill-card.skill-highlight {
  animation: skill-highlight-pulse 2s ease-out forwards;
}

@keyframes skill-highlight-pulse {
  0% {
    border-color: #f59e0b;
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4);
  }
  20% {
    border-color: #f59e0b;
    box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.15);
  }
  100% {
    border-color: var(--qqx-border-color);
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0);
  }
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: var(--qqx-space-sm);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  flex: 1 1 auto;
  min-width: 120px;
}

.card-title h3 {
  font-size: var(--qqx-font-size-body);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.repo-link-btn {
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
  transition: background var(--qqx-transition), color var(--qqx-transition);
}

.repo-link-btn:hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-brand);
}

.repo-link-btn:active {
  transform: scale(0.97);
}

.card-desc {
  font-size: var(--qqx-font-size-caption);
  color: var(--qqx-text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--qqx-space-sm);
  margin-top: var(--qqx-space-md);
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
}

.card-meta span {
  background: var(--qqx-bg-elevated);
  border-radius: var(--qqx-radius-full);
  padding: 2px 8px;
}

.remote-status-badge {
  font-weight: 500;
}
.remote-status--ok { color: #22c55e; }
.remote-status--pending { color: #f59e0b; }
.remote-status--missing { color: var(--qqx-text-tertiary); }

.card-meta span {
}

.type-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--qqx-radius-xs);
  color: var(--qqx-text-tertiary);
  flex-shrink: 0;
}

.card-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

/* Delete confirmation */
.delete-confirm-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--qqx-space-sm);
}

.delete-warn-icon {
  color: #ef4444;
}

.delete-warn-text {
  font-size: var(--qqx-font-size-body);
  color: var(--qqx-text-primary);
  line-height: 1.6;
}

.delete-warn-text code {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  background: var(--qqx-bg-elevated);
  padding: 1px 6px;
  border-radius: var(--qqx-radius-xs);
  color: var(--qqx-text-secondary);
}

.delete-warn-hint {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
}

.delete-error {
  font-size: var(--qqx-font-size-small);
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  border-radius: var(--qqx-radius-sm);
  align-self: stretch;
}
</style>

<!-- Context menu styles (unscoped — teleported to body) -->
<style>
.card-context-menu {
  position: fixed;
  z-index: var(--z-dropdown, 200);
  min-width: 160px;
  padding: 4px;
  background: var(--qqx-modal-bg, var(--qqx-bg-card));
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-sm);
  box-shadow: var(--qqx-shadow-dropdown);
  animation: ctx-menu-in 0.12s ease-out;
}

@keyframes ctx-menu-in {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.ctx-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-label);
  font-family: inherit;
  cursor: pointer;
  transition: background 0.1s ease;
  text-align: left;
}

.ctx-item:hover {
  background: var(--qqx-bg-hover);
}

.ctx-item--primary {
  color: var(--qqx-brand);
}

.ctx-item--primary:hover {
  background: var(--qqx-brand-light);
}

.ctx-item--danger {
  color: #ef4444;
}

.ctx-item--danger:hover {
  background: rgba(239, 68, 68, 0.1);
}

.ctx-sep {
  height: 1px;
  margin: 4px 8px;
  background: var(--qqx-border-color);
}
</style>
