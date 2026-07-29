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
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-card);
  overflow: hidden;
  transition: border-color 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.managed-repo-card--expanded,
.managed-repo-card--selected {
  border-color: var(--qqx-brand);
}

.managed-repo-card--selected {
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--qqx-brand) 16%, transparent);
}

.managed-repo-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  cursor: pointer;
  user-select: none;
}

.managed-repo-row:hover,
.managed-repo-card--expanded .managed-repo-row {
  background: var(--qqx-bg-surface);
}

.expand-indicator {
  width: 12px;
  flex-shrink: 0;
  color: var(--qqx-text-tertiary);
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
  gap: 6px;
}

.repo-name {
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
}

.managed-badge,
.skill-count {
  padding: 2px 6px;
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
  font-size: 10px;
  font-weight: var(--qqx-font-medium);
}

.skill-count {
  flex-shrink: 0;
  padding: 1px 8px;
  font-size: 11px;
}

.source-link,
.skill-link {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--qqx-brand);
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.source-link {
  align-self: flex-start;
  font-size: var(--qqx-font-size-small);
}

.skill-panel {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 16px 8px 40px;
  border-top: 1px solid var(--qqx-border-color);
  background: var(--qqx-bg-surface);
}

.skill-panel-label {
  color: var(--qqx-text-tertiary);
  font-size: 11px;
  font-weight: var(--qqx-font-semibold);
  text-transform: uppercase;
}

.skill-link {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
}

.skill-link:disabled {
  color: var(--qqx-text-tertiary);
  cursor: default;
}

.missing-label {
  color: var(--qqx-warning);
  font-size: var(--qqx-font-size-small);
}
</style>
