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
  width: 100%;
  margin-bottom: var(--sr-space-6);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  margin-bottom: var(--sr-space-4);
}

.section-header h2 {
  font-size: var(--sr-text-page-title);
  font-weight: var(--sr-weight-semibold);
  letter-spacing: -0.015em;
  line-height: 1.4;
  color: var(--sr-text-primary);
}

.count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 22px;
  background: var(--sr-content-bg);
  color: var(--sr-text-secondary);
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sr-space-2);
  margin-bottom: var(--sr-space-5);
}

.filter-btn {
  display: inline-flex;
  align-items: center;
  height: var(--sr-control-height-sm);
  padding: 0 12px;
  border: none;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-control-bg);
  color: var(--sr-text-secondary);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-medium);
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
}

.filter-btn:hover {
  background: var(--sr-control-bg-hover);
  color: var(--sr-text-primary);
}

.filter-btn.active {
  background: var(--sr-action-bg-selected);
  color: var(--sr-accent);
  font-weight: var(--sr-weight-semibold);
}

.section-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
}

.filter-spacer {
  flex: 1;
}

.repo-filter-select {
  height: var(--sr-control-height-sm);
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-control-bg);
  color: var(--sr-text-primary);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-medium);
  font-family: inherit;
  cursor: pointer;
  max-width: 220px;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              box-shadow 140ms var(--sr-ease-standard);
}

.repo-filter-select:hover {
  background: var(--sr-control-bg-hover);
}

.repo-filter-select:focus {
  outline: none;
  background: var(--sr-control-bg-active);
  box-shadow: var(--sr-control-focus-shadow);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              box-shadow 180ms var(--sr-ease-standard);
}

.skill-empty {
  padding: var(--sr-space-6) var(--sr-space-5);
  border: none;
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-card-title);
  text-align: center;
}

.skill-empty--first {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sr-space-3);
  padding: var(--sr-space-6) var(--sr-space-5);
  background: var(--sr-content-bg);
}

.skill-empty--first strong {
  color: var(--sr-text-primary);
  font-size: var(--sr-text-page-title);
}

.skill-empty--first span {
  max-width: 400px;
  color: var(--sr-text-secondary);
  font-size: var(--sr-text-card-title);
  line-height: 1.55;
}

.skill-empty-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: var(--sr-radius-md);
  background: var(--sr-role-blue-surface);
  color: var(--sr-role-blue-ink);
}

.skill-group {
  margin-bottom: var(--sr-space-5);
}

.skill-group-header {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  margin-bottom: var(--sr-space-3);
}

.skill-group-label {
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-bold);
  color: var(--sr-text-tertiary);
  letter-spacing: 0.02em;
}

.skill-group-count {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  font-size: var(--sr-text-micro);
  font-weight: var(--sr-weight-bold);
  color: var(--sr-text-tertiary);
  background: var(--sr-content-bg);
  padding: 0 7px;
  border-radius: var(--sr-radius-badge);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--sr-space-3);
}

@media (max-width: 760px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

@media (pointer: coarse) {
  .filter-btn,
  .repo-filter-select {
    min-height: 40px;
  }
}
</style>
