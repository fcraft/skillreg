<template>
  <article
    class="managed-repo-card"
    :class="{ 'managed-repo-card--expanded': expanded, 'managed-repo-card--selected': selected }"
    :data-repository-path="repo.path"
  >
    <div class="managed-repo-row" @click="$emit('toggle')">
      <span class="expand-indicator">{{ expanded ? '▾' : '▸' }}</span>
      <div class="repo-info">
        <div class="repo-name-row">
          <span class="repo-name">{{ displayName }}</span>
          <span class="managed-badge">NPM 托管</span>
        </div>
        <button class="source-link" @click.stop="$emit('navigate-source', repo.source.id)">
          {{ repo.source.package }}@{{ repo.source.resolvedVersion }} →
        </button>
      </div>
      <span v-if="!repo.exists" class="missing-label">仓库缺失</span>
      <span class="skill-count">{{ repo.skills.length }} skills</span>
    </div>
    <div v-show="expanded" class="skill-panel">
      <div class="skill-panel-label">Skills ({{ repo.skills.length }})</div>
      <button
        v-for="skill in repo.skills"
        :key="skill.path"
        class="skill-link"
        :disabled="!skill.available"
        @click="$emit('navigate-skill', skill.skillId)"
      >
        <span>{{ skill.name }}</span>
        <span v-if="!skill.available" class="missing-label">Skill 缺失</span>
      </button>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  repo: { type: Object, required: true },
  expanded: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
})

defineEmits(['toggle', 'navigate-source', 'navigate-skill'])

const displayName = computed(() => props.repo.path.replace(/^repos\//, ''))
</script>

<style scoped>
.managed-repo-card {
  border: none;
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  overflow: hidden;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.managed-repo-card--selected {
  background: var(--sr-surface-selected);
  box-shadow: inset 0 0 0 2px var(--sr-accent);
}

.managed-repo-row {
  display: flex;
  align-items: center;
  gap: var(--sr-space-3);
  padding: var(--sr-space-3) var(--sr-space-4);
  cursor: pointer;
  user-select: none;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.managed-repo-row:hover {
  background: var(--sr-bg-hover);
}

.expand-indicator {
  width: 12px;
  flex-shrink: 0;
  color: var(--sr-text-tertiary);
  font-size: 10px;
}

.repo-info {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.repo-name-row {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
}

.repo-name {
  color: var(--sr-text-primary);
  font-size: var(--sr-text-body);
  font-weight: var(--sr-weight-semibold);
}

.managed-badge,
.skill-count {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
  background: var(--sr-role-blue-surface);
  color: var(--sr-role-blue-ink);
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
}

.skill-count {
  flex-shrink: 0;
  background: var(--sr-bg-panel);
  color: var(--sr-text-secondary);
}

.source-link,
.skill-link {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--sr-accent);
  cursor: pointer;
  font: inherit;
  font-weight: var(--sr-weight-semibold);
  text-align: left;
}

.source-link {
  align-self: flex-start;
  font-size: var(--sr-text-compact);
}

.skill-panel {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 16px 12px 40px;
  background: transparent;
}

.skill-panel-label {
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-micro);
  font-weight: var(--sr-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.skill-link {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  font-size: var(--sr-text-compact);
}

.skill-link:disabled {
  color: var(--sr-text-tertiary);
  cursor: default;
}

.missing-label {
  color: var(--sr-role-amber-ink);
  font-size: var(--sr-text-compact);
}
</style>
