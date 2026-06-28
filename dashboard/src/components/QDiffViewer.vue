<template>
  <div class="qqx-diff">
    <!-- Header -->
    <div class="qqx-diff__header">
      <code class="qqx-diff__filepath">{{ filePath }}</code>
      <span class="qqx-diff__stats">
        <span class="qqx-diff__legend">
          <span class="qqx-diff__legend-item qqx-diff__legend-item--added">+ 仓库</span>
          <span class="qqx-diff__legend-item qqx-diff__legend-item--removed">- 目标</span>
        </span>
        <span v-if="addedLines > 0" class="qqx-diff__stat qqx-diff__stat--added">+{{ addedLines }}</span>
        <span v-if="removedLines > 0" class="qqx-diff__stat qqx-diff__stat--removed">-{{ removedLines }}</span>
      </span>
    </div>

    <!-- Diff Content -->
    <div class="qqx-diff__content">
      <!-- Added file (repo has it, target missing) -->
      <div v-if="isAdded" class="qqx-diff__lines">
        <div v-for="(line, idx) in repoLines" :key="'a-' + idx" class="qqx-diff__line qqx-diff__line--added">
          <span class="qqx-diff__ln qqx-diff__ln--new">{{ idx + 1 }}</span>
          <span class="qqx-diff__sign">+</span>
          <span class="qqx-diff__code">{{ line }}</span>
        </div>
      </div>

      <!-- Removed file (target has it, repo missing) -->
      <div v-else-if="isRemoved" class="qqx-diff__lines">
        <div v-for="(line, idx) in targetLines" :key="'r-' + idx" class="qqx-diff__line qqx-diff__line--removed">
          <span class="qqx-diff__ln qqx-diff__ln--old">{{ idx + 1 }}</span>
          <span class="qqx-diff__sign">-</span>
          <span class="qqx-diff__code">{{ line }}</span>
        </div>
      </div>

      <!-- Unified diff -->
      <div v-else class="qqx-diff__lines">
        <div v-for="(chunk, ci) in diffChunks" :key="'c-' + ci"
          :class="['qqx-diff__line', {
            'qqx-diff__line--added': chunk.added,
            'qqx-diff__line--removed': chunk.removed,
          }]">
          <span class="qqx-diff__ln qqx-diff__ln--old">{{ chunk.added ? '' : chunk.oldLine }}</span>
          <span class="qqx-diff__ln qqx-diff__ln--new">{{ chunk.removed ? '' : chunk.newLine }}</span>
          <span class="qqx-diff__sign">{{ chunk.added ? '+' : chunk.removed ? '-' : ' ' }}</span>
          <span class="qqx-diff__code">{{ chunk.value }}</span>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!repoLines.length && !targetLines.length" class="qqx-diff__empty">文件为空</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { diffLines } from 'diff'

const props = defineProps({
  // repoContent: 仓库（source）中的文件内容 — green when unique
  repoContent: { type: String, default: '' },
  // targetContent: 目标目录中的文件内容 — red when stale
  targetContent: { type: String, default: '' },
  filePath: { type: String, default: '' },
})

const repoLines = computed(() => {
  if (!props.repoContent) return []
  return props.repoContent.split('\n')
})

const targetLines = computed(() => {
  if (!props.targetContent) return []
  return props.targetContent.split('\n')
})

// isAdded: repo has it, target doesn't → new file to sync
const isAdded = computed(() => props.repoContent && !props.targetContent)
// isRemoved: target has it, repo doesn't → stale file in target
const isRemoved = computed(() => !props.repoContent && props.targetContent)

const diffChunks = computed(() => {
  if (!props.targetContent || !props.repoContent) return []

  // diffLines(old, new): old=target (current), new=repo (desired)
  // → added (green) = repo additions, removed (red) = target deletions
  const changes = diffLines(props.targetContent, props.repoContent, { newlineIsToken: true })

  let oldLine = 1
  let newLine = 1
  const result = []

  for (const change of changes) {
    const lines = change.value.split('\n')
    if (lines[lines.length - 1] === '') lines.pop()

    for (const line of lines) {
      result.push({
        value: line,
        added: !!change.added,
        removed: !!change.removed,
        oldLine: change.added ? null : oldLine++,
        newLine: change.removed ? null : newLine++,
      })
    }
  }

  return result
})

const addedLines = computed(() => {
  if (isAdded.value) return repoLines.value.length
  return diffChunks.value.filter(c => c.added).length
})

const removedLines = computed(() => {
  if (isRemoved.value) return targetLines.value.length
  return diffChunks.value.filter(c => c.removed).length
})
</script>

<style scoped>
.qqx-diff {
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  overflow: hidden;
  margin-top: var(--qqx-space-md);
}

.qqx-diff__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  background: var(--qqx-bg-elevated);
  border-bottom: 1px solid var(--qqx-border-color);
  flex-wrap: wrap;
  gap: var(--qqx-space-sm);
}

.qqx-diff__filepath {
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
}

.qqx-diff__stats {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
}

.qqx-diff__legend {
  display: flex;
  gap: var(--qqx-space-sm);
}

.qqx-diff__legend-item {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: var(--qqx-radius-full);
  font-family: 'SF Mono', monospace;
}

.qqx-diff__legend-item--added {
  color: var(--qqx-diff-added-tag-text);
  background: var(--qqx-diff-added-tag-bg);
}

.qqx-diff__legend-item--removed {
  color: var(--qqx-diff-removed-tag-text);
  background: var(--qqx-diff-removed-tag-bg);
}

.qqx-diff__stat {
  font-family: 'SF Mono', monospace;
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-semibold);
}

.qqx-diff__stat--added {
  color: var(--qqx-diff-added-tag-text);
}

.qqx-diff__stat--removed {
  color: var(--qqx-diff-removed-tag-text);
}

/* Lines container */
.qqx-diff__content {
  max-height: 60vh;
  overflow: auto;
  background: var(--qqx-bg-card);
}

.qqx-diff__lines {
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 12px;
  line-height: 1.6;
  tab-size: 4;
}

.qqx-diff__line {
  display: flex;
  padding: 0 var(--qqx-space-sm);
  min-height: 19px;
}

.qqx-diff__line--added {
  background: var(--qqx-diff-added-bg);
  border-left: 3px solid var(--qqx-diff-added-border);
}

.qqx-diff__line--removed {
  background: var(--qqx-diff-removed-bg);
  border-left: 3px solid var(--qqx-diff-removed-border);
}

/* Line numbers */
.qqx-diff__ln {
  width: 36px;
  flex-shrink: 0;
  text-align: right;
  padding-right: var(--qqx-space-sm);
  color: var(--qqx-text-quaternary);
  user-select: none;
}

/* Sign column (+/-/ )  */
.qqx-diff__sign {
  width: 16px;
  flex-shrink: 0;
  color: var(--qqx-text-quaternary);
  user-select: none;
}

.qqx-diff__line--added .qqx-diff__sign {
  color: var(--qqx-diff-added-tag-text);
}

.qqx-diff__line--removed .qqx-diff__sign {
  color: var(--qqx-diff-removed-tag-text);
}

/* Code text */
.qqx-diff__code {
  white-space: pre;
  color: var(--qqx-text-primary);
  overflow-x: auto;
}

.qqx-diff__empty {
  padding: var(--qqx-space-lg);
  text-align: center;
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
}
</style>
