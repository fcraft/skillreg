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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RefreshCw as RefreshCwIcon, Download as DownloadIcon, Terminal as TerminalIcon, BookOpen as BookOpenIcon, GitBranch as GitBranchIcon } from 'lucide-vue-next'
import { useSkillDetail } from '../composables/useSkillDetail.js'
import { useData } from '../composables/useData.js'
import { exportSkill } from '../api/index.js'
import SubmoduleBadge from './SubmoduleBadge.vue'
import SkillImportModal from './SkillImportModal.vue'

const { show: showDetail } = useSkillDetail()
const { refresh } = useData()
const pressed = ref(false)
const showUpdateModal = ref(false)

const props = defineProps({
  skill: { type: Object, required: true }
})

function handleClick() {
  showDetail(props.skill.name)
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

.ctx-sep {
  height: 1px;
  margin: 4px 8px;
  background: var(--qqx-border-color);
}
</style>
