import { reactive } from 'vue'
import { fetchSyncConfig, fetchSyncStatus } from '../api/index.js'
import { normalizeTarget } from '../sources/agentTargets.js'
import { useEventBus } from './useEventBus.js'
import { computeSkillSyncSummary, mergeBridgeTargetStatus } from '../sources/skillInstallState.js'

const state = reactive({
  statusMap: {},
  targets: [],
  projectTargets: [],
  loading: false,
  loaded: false,
  error: '',
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
  state.error = ''
  loadPromise = (async () => {
    try {
      const [config, rows] = await Promise.all([
        fetchSyncConfig(),
        fetchSyncStatus(null, true),
      ])
      const namedTargets = (config.targets || [])
        .map(t => normalizeTarget(t))
        .filter(Boolean)
        .map(t => ({ ...t, _project: false }))
      const projSet = new Map()
      if (Array.isArray(rows)) {
        for (const row of rows) {
          if (row._project) {
            const key = `${row._projectId || row._project}:${row.target}`
            if (!projSet.has(key)) {
              projSet.set(key, {
                name: row.target,
                path: row.target,
                _project: true,
                _projectName: row._project,
                _projectId: row._projectId,
                _projectRoot: row._projectRoot || null,
                _agent: row._agent || null,
                _icon: row._icon || null,
              })
            }
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
      state.error = ''
    } catch (err) {
      state.error = err?.message || '加载同步目标和状态失败'
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
    if (!skillName) return
    if (!state.loaded) {
      await doLoadSyncStatus()
      if (!state.loaded) return
    }
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
      // statusMap retains previous data if refresh fails transiently
    }
  }

  /**
   * Merge single-target status rows from SkillSyncManager without overwriting
   * unrelated targets or project targets already tracked by the bridge.
   */
  function mergeTargetStatus(targetKey, rows, targetsList = null) {
    state.statusMap = mergeBridgeTargetStatus(state.statusMap, targetKey, rows)
    if (Array.isArray(targetsList)) {
      state.targets = targetsList
        .map(t => normalizeTarget(t))
        .filter(Boolean)
        .map(t => ({ ...t, _project: false }))
    }
  }

  function getSkillSyncSummary(skillName) {
    if (!state.loaded) return null
    return computeSkillSyncSummary(state.targets, state.projectTargets, state.statusMap, skillName)
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

  return {
    state,
    loadSyncStatus,
    forceRefresh,
    refreshSkill,
    mergeTargetStatus,
    getSkillSyncSummary,
    getSkillTargetStatus,
    getTotalTargets,
    getNamedTargetCount,
    getProjectTargetCount,
  }
}
