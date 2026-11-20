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
  margin-left: var(--sr-space-4);
  border: none;
  border-radius: var(--sr-radius-lg);
  background: var(--sr-inspector-bg);
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
  padding: var(--sr-space-4) var(--sr-space-5) var(--sr-space-3);
}

.context-title {
  font-size: var(--sr-text-dialog-title);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
  margin: 0;
}

.context-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--sr-control-height-sm);
  height: var(--sr-control-height-sm);
  border: none;
  background: transparent;
  color: var(--sr-text-secondary);
  font-size: 18px;
  border-radius: var(--sr-radius-sm);
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
}

.context-close:hover {
  background: var(--sr-action-bg-hover);
  color: var(--sr-text-primary);
}

.context-body {
  padding: var(--sr-space-2) var(--sr-space-5) var(--sr-space-5);
  display: flex;
  flex-direction: column;
  gap: var(--sr-space-5);
}

.context-section {
  display: flex;
  flex-direction: column;
  gap: var(--sr-space-2);
}

.context-section h4 {
  font-size: var(--sr-text-micro);
  font-weight: var(--sr-weight-bold);
  color: var(--sr-text-tertiary);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.context-row {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  font-size: var(--sr-text-compact);
}

.context-label {
  color: var(--sr-text-tertiary);
  min-width: 48px;
}

.context-row code {
  font-size: var(--sr-text-compact);
  background: var(--sr-bg-panel);
  padding: 2px 6px;
  border-radius: var(--sr-radius-xs);
}

.context-tag {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  background: var(--sr-bg-panel);
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
}

.context-link {
  color: var(--sr-accent);
  text-decoration: none;
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-semibold);
}
.context-link:hover { color: var(--sr-accent-strong); text-decoration: underline; }

.context-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sr-space-2);
}

.context-action-btn {
  min-height: var(--sr-control-height-sm);
  padding: 0 12px;
  border: none;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-control-bg);
  color: var(--sr-text-primary);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-semibold);
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.context-action-btn:hover {
  background: var(--sr-control-bg-hover);
}
</style>
