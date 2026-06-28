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
    <div class="filter-bar">
      <button
        v-for="cat in categories"
        :key="cat"
        class="filter-btn"
        :class="{ active: activeFilter === cat }"
        @click="activeFilter = activeFilter === cat ? null : cat"
      >
        {{ cat === null ? 'All' : cat }}
      </button>
      <button v-if="submoduleFilter" class="filter-btn active" @click="clearSubmoduleFilter">
        仓库: {{ submoduleFilter.replace(/^repos\//, '') }}
      </button>
    </div>
    <div class="grid">
      <SkillCard
        v-for="skill in filtered"
        :key="skill.id"
        :skill="skill"
      />
    </div>

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
import SkillCard from './SkillCard.vue'
import SkillDetailDrawer from './SkillDetailDrawer.vue'
import SkillImportModal from './SkillImportModal.vue'
import { useData } from '../composables/useData.js'
import { useSkillDetail } from '../composables/useSkillDetail.js'

const { state } = useData()
const { show: showDetail } = useSkillDetail()
const route = useRoute()
const router = useRouter()

const activeFilter = ref(null)
const fileDrawerSkill = ref(null)
const showImportModal = ref(false)

const submoduleFilter = computed(() => route.query.submodule || null)

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

function clearSubmoduleFilter() {
  router.replace({ query: {} })
}

const categories = computed(() => {
  const types = [...new Set(state.skills.map(s => s.type))]
  return [null, ...types.sort()]
})

const filtered = computed(() => {
  let list = activeFilter.value ? state.skills.filter(s => s.type === activeFilter.value) : state.skills
  if (submoduleFilter.value) {
    list = list.filter(s => s.submodulePath === submoduleFilter.value)
  }
  return list
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

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--qqx-space-lg);
}
</style>
