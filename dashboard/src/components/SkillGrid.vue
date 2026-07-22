<template>
  <section class="skill-grid-section">
    <div class="section-header">
      <h2>Skills</h2>
      <span class="count">{{ state.skills.length }}</span>
      <div class="section-actions">
        <QButton type="primary" size="small" @click="showImportModal = true">
          导入
        </QButton>
      </div>
    </div>
    <SkillImportModal v-model="showImportModal" @imported="onImportComplete" />
    <div v-if="state.skills.length" class="filter-bar">
      <button
        v-for="cat in categories"
        :key="cat"
        class="filter-btn"
        :class="{ active: activeFilter === cat }"
        @click="activeFilter = activeFilter === cat ? null : cat"
      >
        {{ cat === null ? 'All' : cat }}
      </button>
      <div class="filter-spacer"></div>
      <!-- Repo filter dropdown -->
      <div class="repo-filter">
        <select v-model="repoFilter" class="repo-filter-select">
          <option :value="null">全部仓库</option>
          <option value="__standalone__">独立 Skill</option>
          <option v-for="repo in repoOptions" :key="repo.path" :value="repo.path">
            {{ repo.label }} ({{ repo.count }})
          </option>
        </select>
      </div>
    </div>

    <!-- Grouped by repo (default). When a repo filter is active, only that
         group is shown. -->
    <template v-for="group in groupedSkills" :key="group.key">
      <div v-if="group.skills.length" class="skill-group">
        <div class="skill-group-header">
          <span class="skill-group-label">{{ group.label }}</span>
          <span class="skill-group-count">{{ group.skills.length }}</span>
        </div>
        <div class="grid">
          <SkillCard
            v-for="skill in group.skills"
            :key="skill.id"
            :skill="skill"
          />
        </div>
      </div>
    </template>
    <div v-if="!state.skills.length" class="skill-empty skill-empty--first">
      <div class="skill-empty-icon"><PackagePlus :size="24" /></div>
      <strong>还没有 Skill</strong>
      <span>导入本地目录、ZIP、Git 仓库或 NPM 包，开始建立你的 Skill 集合</span>
      <QButton type="primary" size="small" @click="showImportModal = true">导入首个 Skill</QButton>
    </div>
    <div v-else-if="!totalFiltered" class="skill-empty">没有匹配的 Skill</div>

    <!-- File tree drawer -->
    <SkillDetailDrawer
      :skill="fileDrawerSkill"
      :open="Boolean(fileDrawerSkill)"
      @close="fileDrawerSkill = null"
    />
  </section>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PackagePlus } from 'lucide-vue-next'
import SkillCard from './SkillCard.vue'
import SkillDetailDrawer from './SkillDetailDrawer.vue'
import SkillImportModal from './SkillImportModal.vue'
import QButton from './QButton.vue'
import { useData } from '../composables/useData.js'
import { useSkillDetail } from '../composables/useSkillDetail.js'

const { state } = useData()
const { show: showDetail } = useSkillDetail()
const route = useRoute()
const router = useRouter()

const activeFilter = ref(null)
const fileDrawerSkill = ref(null)
const showImportModal = ref(false)

// Repo filter: null = all repos, '__standalone__' = only standalone skills,
// or a submodulePath string. Initialised from the ?submodule= query param so
// cross-page navigation (graph/repos → skills) still works.
const repoFilter = ref(route.query.submodule || null)

// Keep repoFilter in sync with the ?submodule= query param (both directions).
watch(() => route.query.submodule, (val) => {
  repoFilter.value = val || null
})

watch(() => route.query.onboarding, (value) => {
  if (value !== 'import') return
  showImportModal.value = true
  const query = { ...route.query }
  delete query.onboarding
  router.replace({ query })
}, { immediate: true })
watch(repoFilter, (val) => {
  const current = route.query.submodule || null
  const next = val && val !== '__standalone__' ? val : null
  if (current !== next) {
    const query = { ...route.query }
    if (next) query.submodule = next
    else delete query.submodule
    router.replace({ query })
  }
})

// Scroll to and highlight a skill card by name
function scrollToSkillCard(skillName) {
  nextTick(() => {
    const card = document.querySelector(`.skill-card[data-skill-name="${CSS.escape(skillName)}"]`)
    if (!card) return
    const cardRect = card.getBoundingClientRect()
    const targetTop = window.scrollY + cardRect.top - Math.max((window.innerHeight - cardRect.height) / 2, 0)
    window.scrollTo({ top: targetTop, behavior: 'smooth' })
    card.classList.add('skill-highlight')
    setTimeout(() => {
      card.classList.remove('skill-highlight')
    }, 2500)
  })
}

// Watch ?skill=X param — auto-open detail + scroll + highlight
watch(() => route.query.skill, (skillName) => {
  if (skillName) {
    const skill = state.skills.find(s => s.name === skillName || s.id === skillName)
    if (skill) {
      showDetail(skill.name)
      scrollToSkillCard(skillName)
    }
  }
}, { immediate: true })

function onImportComplete() {
  const { refresh } = useData()
  refresh()
}

function repoLabel(path) {
  return path.replace(/^repos\//, '')
}

const categories = computed(() => {
  const types = [...new Set(state.skills.map(s => s.type))]
  return [null, ...types.sort()]
})

// Build the list of repos (submodulePaths) present among current skills.
const repoOptions = computed(() => {
  const counts = new Map()
  for (const s of state.skills) {
    if (s.submodulePath) {
      counts.set(s.submodulePath, (counts.get(s.submodulePath) || 0) + 1)
    }
  }
  return [...counts.entries()]
    .map(([path, count]) => ({ path, label: repoLabel(path), count }))
    .sort((a, b) => a.label.localeCompare(b.label))
})

// Apply the type + repo filters.
const filtered = computed(() => {
  let list = activeFilter.value ? state.skills.filter(s => s.type === activeFilter.value) : state.skills
  if (repoFilter.value === '__standalone__') {
    list = list.filter(s => !s.submodulePath)
  } else if (repoFilter.value) {
    list = list.filter(s => s.submodulePath === repoFilter.value)
  }
  return list
})

const totalFiltered = computed(() => filtered.value.length)

// Group skills by repo (default ordering). Standalone skills come first, then
// each repo group sorted alphabetically; within a group, sort by name.
const groupedSkills = computed(() => {
  const byName = (a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase())
  const standalone = filtered.value.filter(s => !s.submodulePath).sort(byName)

  const repoMap = new Map()
  for (const s of filtered.value) {
    if (!s.submodulePath) continue
    if (!repoMap.has(s.submodulePath)) repoMap.set(s.submodulePath, [])
    repoMap.get(s.submodulePath).push(s)
  }
  const repoGroups = [...repoMap.entries()]
    .sort((a, b) => repoLabel(a[0]).localeCompare(repoLabel(b[0])))
    .map(([path, skills]) => ({
      key: path,
      label: repoLabel(path),
      skills: skills.sort(byName),
    }))

  const groups = []
  if (standalone.length) {
    groups.push({ key: '__standalone__', label: '独立 Skill', skills: standalone })
  }
  groups.push(...repoGroups)
  return groups
})
</script>

<style scoped>
.skill-grid-section {
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

.count {
  background: var(--qqx-bg-elevated);
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--qqx-space-sm);
  margin-bottom: var(--qqx-space-lg);
}

.filter-btn {
  padding: 4px 12px;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-surface);
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  cursor: pointer;
  transition: all var(--qqx-transition);
}

.filter-btn:hover {
  background: var(--qqx-bg-hover);
}

.filter-btn.active {
  background: var(--qqx-brand-light);
  border-color: var(--qqx-brand);
  color: var(--qqx-brand);
}

.section-actions {
  margin-left: auto;
}

.filter-spacer {
  flex: 1;
}

.repo-filter-select {
  padding: 4px 10px;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-surface);
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  font-family: inherit;
  cursor: pointer;
  max-width: 220px;
  transition: all var(--qqx-transition);
}

.repo-filter-select:hover {
  background: var(--qqx-bg-hover);
}

.skill-empty {
  padding: var(--qqx-space-2xl);
  border: 1px dashed var(--qqx-border-dashed);
  border-radius: var(--qqx-radius-sm);
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
  text-align: center;
}

.skill-empty--first {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-3xl) var(--qqx-space-xl);
  background: var(--qqx-bg-overlay);
}

.skill-empty--first strong {
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-title);
}

.skill-empty--first span {
  max-width: 520px;
  margin-bottom: var(--qqx-space-sm);
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-caption);
  line-height: 1.6;
}

.skill-empty-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  margin-bottom: var(--qqx-space-xs);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
}

.repo-filter-select:focus {
  outline: none;
  border-color: var(--qqx-brand);
  color: var(--qqx-text-primary);
}

.skill-group {
  margin-bottom: var(--qqx-space-xl);
}

.skill-group-header {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  margin-bottom: var(--qqx-space-md);
  padding-bottom: var(--qqx-space-xs);
  border-bottom: 1px solid var(--qqx-border-color);
}

.skill-group-label {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-secondary);
}

.skill-group-count {
  font-size: 11px;
  color: var(--qqx-text-tertiary);
  background: var(--qqx-bg-elevated);
  padding: 1px 8px;
  border-radius: var(--qqx-radius-full);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--qqx-space-lg);
}
</style>
