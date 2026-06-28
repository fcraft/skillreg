import { reactive } from 'vue'
import { fetchSyncConfig, fetchSyncStatus } from '../api/index.js'
import { useEventBus } from './useEventBus.js'

const state = reactive({
  statusMap: {},
  targets: [],
  projectTargets: [],
  loading: false,
  loaded: false,
})

let loadPromise = null
const { on } = useEventBus()

async function doLoadSyncStatus(force = false) {
  if (force) {
    state.loaded = false
    loadPromise = null
  }
  if (state.loaded || loadPromise) return loadPromise || Promise.resolve()
  state.loading = true
  loadPromise = (async () => {
    try {
      const [config, rows] = await Promise.all([
        fetchSyncConfig(),
        fetchSyncStatus(null, true),
      ])
      const namedTargets = (config.targets || []).map(t => ({ name: t.name, path: t.path, _project: false }))
      const projSet = new Map()
      for (const row of rows) {
        if (row._project) {
          const key = row.target
          if (!projSet.has(key)) {
            projSet.set(key, { name: row.target, path: row.target, _project: true, _projectName: row._project, _projectId: row._projectId })
          }
        }
      }
      state.targets = namedTargets
      state.projectTargets = [...projSet.values()]
      state.statusMap = {}
      if (Array.isArray(rows)) {
        for (const row of rows) {
          state.statusMap[row.name] = state.statusMap[row.name] || {}
          state.statusMap[row.name][row.target] = row.status
        }
      }
      state.loaded = true
    } catch {
      // silently fail — badges will just not show
    } finally {
      state.loading = false
      loadPromise = null
    }
  })()
  return loadPromise
}

// Auto-refresh when data changes (e.g. after sync completes)
on('data-changed', () => {
  doLoadSyncStatus(true)
})

export function useSyncBridge() {
  function loadSyncStatus(force = false) {
    return doLoadSyncStatus(force)
  }

  function forceRefresh() {
    return doLoadSyncStatus(true)
  }

  /**
   * Lightweight per-skill refresh — only updates statusMap for one skill.
   */
  async function refreshSkill(skillName) {
    if (!skillName || !state.loaded) return
    try {
      const rows = await fetchSyncStatus(null, true, skillName)
      const newEntries = {}
      if (Array.isArray(rows)) {
        for (const row of rows) {
          newEntries[row.target] = row.status
        }
      }
      state.statusMap[skillName] = newEntries
    } catch {
      // silently ignore — statusMap retains previous data
    }
  }

  function getSkillSyncSummary(skillName) {
    if (!state.loaded) return null
    const targetsForSkill = state.statusMap[skillName]
    const totalTargets = state.targets.length + state.projectTargets.length
    if (!targetsForSkill) return { installed: 0, changed: 0, missing: 0, ok: 0, total: totalTargets }
    const summary = { installed: 0, changed: 0, missing: 0, ok: 0, total: totalTargets, namedOk: 0, namedInstalled: 0, projInstalled: 0 }
    for (const [target, st] of Object.entries(targetsForSkill)) {
      summary.installed++
      if (st === 'unchanged') summary.ok++
      else if (st === 'changed') summary.changed++
      else if (st === 'missing') summary.missing++
      const isNamed = state.targets.some(t => t.name === target)
      if (isNamed) {
        summary.namedInstalled++
        if (st === 'unchanged') summary.namedOk++
      } else {
        summary.projInstalled++
      }
    }
    return summary
  }

  function getSkillTargetStatus(skillName) {
    if (!state.loaded) return {}
    return state.statusMap[skillName] || {}
  }

  function getTotalTargets() {
    return state.targets.length + state.projectTargets.length
  }

  function getNamedTargetCount() {
    return state.targets.length
  }

  function getProjectTargetCount() {
    return state.projectTargets.length
  }

  return { state, loadSyncStatus, forceRefresh, refreshSkill, getSkillSyncSummary, getSkillTargetStatus, getTotalTargets, getNamedTargetCount, getProjectTargetCount }
}
