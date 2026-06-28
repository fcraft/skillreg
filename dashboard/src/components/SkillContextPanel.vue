<template>
  <aside v-if="state.open" class="context-panel">
    <div class="context-header">
      <h3 class="context-title">{{ contextName }}</h3>
      <button class="context-close" @click="closeContext">&times;</button>
    </div>
    <div class="context-body">
      <!-- Skill info -->
      <section v-if="state.type === 'skill' && state.skill" class="context-section">
        <h4>基本信息</h4>
        <div class="context-row">
          <span class="context-label">路径</span>
          <code>{{ state.skill.path.replace(/^(skills|repos)\//, '') }}</code>
        </div>
        <div class="context-row">
          <span class="context-label">类型</span>
          <span class="context-tag">{{ state.skill.type }}</span>
        </div>
        <div class="context-row">
          <span class="context-label">文件数</span>
          <span>{{ state.skill.fileCount || 0 }}</span>
        </div>
      </section>

      <!-- Submodule info -->
      <section v-if="state.skill?.isSubmodule && state.skill?.submodulePath" class="context-section">
        <h4>所属仓库</h4>
        <router-link :to="{ name: 'repos', query: { submodule: state.skill.submodulePath } }" class="context-link">
          {{ state.skill.submodulePath.replace(/^repos\//, '') }}
        </router-link>
      </section>

      <!-- Sync Status -->
      <section v-if="syncSummary" class="context-section">
        <h4>同步状态</h4>
        <SkillSyncBadge :summary="syncSummary" :skill-name="state.skill?.name" />
      </section>

      <!-- Dependencies -->
      <section v-if="dependencies.length" class="context-section">
        <h4>关联</h4>
        <div v-for="rel in dependencies" :key="rel.to" class="context-row">
          <span class="context-label">{{ rel.type === 'depends-on' ? '依赖' : rel.type }}</span>
          <a href="#" class="context-link" @click.prevent="show(rel.to)">{{ rel.to }}</a>
        </div>
      </section>

      <!-- Actions -->
      <section class="context-section">
        <h4>操作</h4>
        <div class="context-actions">
          <button v-if="state.skill?.name" class="context-action-btn" @click="viewSkill">
            查看文件
          </button>
          <button v-if="state.skill?.name" class="context-action-btn" @click="navToSync">
            同步管理
          </button>
          <button v-if="state.skill?.name" class="context-action-btn" @click="navToGraph">
            依赖图
          </button>
        </div>
      </section>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useContextPanel } from '../composables/useContextPanel.js'
import { useSyncBridge } from '../composables/useSyncBridge.js'
import { useData } from '../composables/useData.js'
import { useSkillDetail } from '../composables/useSkillDetail.js'
import SkillSyncBadge from './SkillSyncBadge.vue'

const { state, closeContext } = useContextPanel()
const { getSkillSyncSummary } = useSyncBridge()
const { state: dataState } = useData()
const router = useRouter()
const { show } = useSkillDetail()

const contextName = computed(() => state.skill?.name || state.submodulePath || '')

const syncSummary = computed(() => {
  if (state.skill?.name) return getSkillSyncSummary(state.skill.name)
  return null
})

const dependencies = computed(() => {
  if (!state.skill?.name) return []
  return (dataState.relationships || []).filter(r =>
    r.from === state.skill.name || r.to === state.skill.name
  )
})

function viewSkill() {
  closeContext()
  show(state.skill.name)
}

function navToSync() {
  closeContext()
  router.push({ name: 'sync', query: { skill: state.skill.name } })
}

function navToGraph() {
  closeContext()
  router.push({ name: 'graph', query: { skill: state.skill.name } })
}
</script>

<style scoped>
.context-panel {
  width: 320px;
  border-left: 1px solid var(--qqx-border-color);
  background: var(--qqx-bg-card);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  flex-shrink: 0;
}

.context-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--qqx-space-lg) var(--qqx-space-xl);
  border-bottom: 1px solid var(--qqx-border-color);
}

.context-title {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  margin: 0;
}

.context-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--qqx-text-secondary);
  font-size: 18px;
  border-radius: var(--qqx-radius-xs);
  cursor: pointer;
  transition: all var(--qqx-transition);
}
.context-close:hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-primary);
}

.context-body {
  padding: var(--qqx-space-lg) var(--qqx-space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-xl);
}

.context-section {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-sm);
}

.context-section h4 {
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-tertiary);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.context-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  font-size: var(--qqx-font-size-small);
}

.context-label {
  color: var(--qqx-text-tertiary);
  min-width: 48px;
}

.context-row code {
  font-size: var(--qqx-font-size-small);
  background: var(--qqx-bg-elevated);
  padding: 1px 6px;
  border-radius: var(--qqx-radius-xs);
}

.context-tag {
  background: var(--qqx-bg-elevated);
  padding: 1px 8px;
  border-radius: var(--qqx-radius-full);
  font-size: var(--qqx-font-size-small);
}

.context-link {
  color: var(--qqx-brand);
  text-decoration: none;
  font-size: var(--qqx-font-size-small);
  transition: color var(--qqx-transition);
}
.context-link:hover { color: var(--qqx-brand-hover); text-decoration: underline; }

.context-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--qqx-space-xs);
}

.context-action-btn {
  padding: 4px 12px;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-card);
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  cursor: pointer;
  transition: all var(--qqx-transition);
}
.context-action-btn:hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-primary);
  border-color: var(--qqx-brand);
}
</style>
