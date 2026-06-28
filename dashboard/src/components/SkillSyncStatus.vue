<template>
  <section class="sync-section">
    <div class="section-header">
      <h2>Skill Sync</h2>
      <span class="count">{{ targets.length }}</span>
      <button class="refresh-btn" @click="loadStatus" :disabled="loading">Refresh</button>
    </div>
    <div v-if="error" class="sync-error">{{ error }}</div>

    <div v-if="targets.length === 0" class="empty">未配置同步目标目录</div>

    <div v-for="target in targets" :key="target.name" class="target-card">
      <div class="target-header">
        <div class="target-info">
          <span class="target-name">{{ target.name }}</span>
          <span class="target-path" :title="target.path">{{ target.path }}</span>
        </div>
        <button
          class="sync-btn"
          :disabled="syncing === target.name || target.deregistered"
          @click="syncTarget(target)"
        >{{ syncing === target.name ? '同步中...' : 'Sync All' }}</button>
      </div>

      <div v-if="target.deregistered" class="deregistered-banner">
        ✖ 目标目录不存在 — {{ target.path }}
      </div>

      <div v-else class="skill-rows">
        <div v-for="entry in target.skills" :key="entry.name" class="skill-row">
          <span class="skill-name">{{ entry.name }}</span>
          <span class="skill-status" :class="entry.status">{{ entry.status }}</span>
          <button
            v-if="entry.status !== 'unchanged' && entry.status !== 'syncing'"
            class="sync-btn"
            :disabled="syncing === `${target.name}/${entry.name}`"
            @click="syncSkill(target.name, entry.name)"
          >{{ syncing === `${target.name}/${entry.name}` ? '...' : 'Sync' }}</button>
        </div>
        <div v-if="target.skills.length === 0" class="skill-empty">无 skill 关联</div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['synced'])

const targets = ref([])
const loading = ref(false)
const syncing = ref(null)
const error = ref(null)

onMounted(loadStatus)

async function loadStatus() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch('/api/skill-sync-targets')
    const data = await res.json()
    if (data.error) throw new Error(data.error)

    const byTarget = {}
    for (const t of data) {
      const registered = t.status && Object.keys(t.status).length > 0 && !Object.values(t.status).some(s => s === 'deregistered')
      const rows = []
      if (t.skills === null) {
        // All skills — use whatever status reports
        for (const [name, status] of Object.entries(t.status || {})) {
          rows.push({ name, status })
        }
      } else {
        for (const name of t.skills) {
          rows.push({ name, status: t.status[name] || 'missing' })
        }
      }
      byTarget[t.name] = {
        name: t.name,
        path: t.path,
        skills: rows,
        deregistered: t.status && Object.values(t.status).some(s => s === 'deregistered'),
      }
    }
    targets.value = Object.values(byTarget)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function syncTarget(target) {
  syncing.value = target.name
  error.value = null
  try {
    const res = await fetch('/api/sync-skills', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: target.name }),
    })
    const result = await res.json()
    if (!result.success) throw new Error(result.stderr || result.error || 'sync failed')
    emit('synced')
    await loadStatus()
  } catch (e) {
    error.value = `${target.name}: ${e.message}`
  } finally {
    syncing.value = null
  }
}

async function syncSkill(targetName, skillName) {
  const key = `${targetName}/${skillName}`
  syncing.value = key
  error.value = null
  try {
    const res = await fetch('/api/sync-skills', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: targetName, skills: [skillName] }),
    })
    const result = await res.json()
    if (!result.success) throw new Error(result.stderr || result.error || 'sync failed')
    emit('synced')
    await loadStatus()
  } catch (e) {
    error.value = `${key}: ${e.message}`
  } finally {
    syncing.value = null
  }
}
</script>

<style scoped>
.sync-section {
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
.refresh-btn {
  margin-left: auto;
  font-size: var(--qqx-font-size-small);
  padding: 4px 12px;
  border-radius: var(--qqx-radius-full);
  border: 1px solid var(--qqx-border-color);
  background: var(--qqx-bg-card);
  color: var(--qqx-text-primary);
  cursor: pointer;
}
.refresh-btn:hover:not(:disabled) { background: var(--qqx-bg-hover); }
.refresh-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.sync-error { color: #ef4444; font-size: var(--qqx-font-size-small); margin-bottom: var(--qqx-space-md); }
.empty { color: var(--qqx-text-tertiary); font-size: var(--qqx-font-size-small); padding: var(--qqx-space-lg); }

.target-card {
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-card);
  margin-bottom: var(--qqx-space-md);
  overflow: hidden;
}
.target-header {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  background: var(--qqx-bg-elevated);
}
.target-info { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.target-name {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}
.target-path {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.deregistered-banner {
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  color: #f59e0b;
  font-size: var(--qqx-font-size-small);
}

.skill-rows { display: flex; flex-direction: column; }
.skill-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-sm) var(--qqx-space-lg);
  transition: background 0.15s;
}
.skill-row:hover { background: var(--qqx-bg-hover); }
.skill-name {
  flex: 1;
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-primary);
}
.skill-empty {
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
}

.skill-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-elevated);
  flex-shrink: 0;
}
.skill-status.synced,
.skill-status.unchanged { color: #10b981; }
.skill-status.changed { color: #f59e0b; }
.skill-status.missing { color: var(--qqx-text-tertiary); }
.skill-status.deregistered { color: #ef4444; }
.skill-status.syncing { color: #8b5cf6; }

.sync-btn {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: var(--qqx-radius-full);
  border: none;
  background: var(--qqx-brand-fill-bg);
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
}
.sync-btn:hover:not(:disabled) { opacity: 0.85; }
.sync-btn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
