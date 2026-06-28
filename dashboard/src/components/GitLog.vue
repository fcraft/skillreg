<template>
  <section class="git-log-section">
    <div class="section-header">
      <h2>提交记录</h2>
    </div>
    <div class="repo-tabs">
      <button
        v-for="repo in repos"
        :key="repo.key"
        :class="['tab-btn', { 'tab-btn--active': activeRepo === repo.key }]"
        @click="activeRepo = repo.key"
      >
        {{ repo.label }}
        <span class="tab-count">{{ repo.count }}</span>
      </button>
    </div>
    <div class="log-list">
      <div
        v-for="commit in activeCommits"
        :key="commit.hash"
        class="log-entry"
      >
        <a
          class="log-hash"
          :href="commitUrl(commit.hash)"
          target="_blank"
          :title="commit.hash"
        >{{ commit.hash.slice(0, 7) }}</a>
        <span class="log-message">{{ commit.message }}</span>
        <span class="log-meta">
          <span class="log-author">{{ commit.author }}</span>
          <span class="log-date">{{ relativeTime(commit.date) }}</span>
        </span>
      </div>
      <div v-if="activeCommits.length === 0" class="log-empty">
        暂无提交记录
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useData } from '../composables/useData.js'

const { state, remoteUrlMap } = useData()

const activeRepo = ref('main')

const repos = computed(() => {
  const list = [{ key: 'main', label: '主仓库', count: state.gitLogs.main?.length || 0 }]
  if (state.gitLogs.submodules) {
    for (const [path, commits] of Object.entries(state.gitLogs.submodules)) {
      list.push({ key: path, label: path.replace(/^repos\//, ''), count: commits.length })
    }
  }
  return list
})

const activeCommits = computed(() => {
  if (activeRepo.value === 'main') return state.gitLogs.main || []
  return state.gitLogs.submodules?.[activeRepo.value] || []
})

function commitUrl(hash) {
  const url = activeRepo.value === 'main'
    ? remoteUrlMap.value.main
    : remoteUrlMap.value[activeRepo.value]
  if (!url) return '#'
  return `${url}/commit/${hash}`
}

function relativeTime(isoDate) {
  if (!isoDate) return ''
  const now = Date.now()
  const then = new Date(isoDate).getTime()
  const diff = now - then
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}天前`
  const months = Math.floor(days / 30)
  return `${months}个月前`
}
</script>

<style scoped>
.git-log-section {
  margin-bottom: var(--qqx-space-3xl);
}

.section-header {
  margin-bottom: var(--qqx-space-lg);
}

.section-header h2 {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
}

.repo-tabs {
  display: flex;
  gap: var(--qqx-space-sm);
  margin-bottom: var(--qqx-space-lg);
  flex-wrap: wrap;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  font-size: var(--qqx-font-size-small);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-card);
  color: var(--qqx-text-secondary);
  cursor: pointer;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.tab-btn:not(.tab-btn--active):hover {
  border-color: var(--qqx-brand);
  color: var(--qqx-text-primary);
}

.tab-btn--active {
  background: var(--qqx-brand-light);
  border-color: var(--qqx-brand);
  color: var(--qqx-brand);
  font-weight: var(--qqx-font-medium);
}

.tab-count {
  font-size: 10px;
  opacity: 0.7;
}

.log-list {
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  overflow: hidden;
}

.log-entry {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  padding: 8px 16px;
  border-bottom: 1px solid var(--qqx-border-color);
  transition: background-color 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.log-entry:last-child {
  border-bottom: none;
}

.log-entry:hover {
  background: var(--qqx-bg-hover);
}

.log-hash {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-brand);
  text-decoration: none;
  flex-shrink: 0;
}

.log-hash:hover {
  text-decoration: underline;
}

.log-message {
  flex: 1;
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-meta {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  flex-shrink: 0;
}

.log-author {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
}

.log-date {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  min-width: 60px;
  text-align: right;
}

.log-empty {
  padding: var(--qqx-space-xl);
  text-align: center;
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-label);
}

@media (max-width: 767px) {
  .log-entry {
    flex-wrap: wrap;
    gap: 4px;
  }
  .log-meta {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
