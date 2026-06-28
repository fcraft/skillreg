import { reactive, computed } from 'vue'
import { fetchSkills, fetchSkillsFull, fetchSkillsRefresh } from '../api/index.js'
import { useEventBus } from './useEventBus.js'

const state = reactive({
  skills: [],
  repoNodes: [],
  submodules: [],
  relationships: [],
  gitLogs: { main: [], submodules: {} },
  generatedAt: '',
  loading: true,
  error: null,
})

const remoteUrlMap = computed(() => {
  const map = {}
  for (const sm of state.submodules) {
    if (sm.remoteUrl) map[sm.path] = sm.remoteUrl
  }
  const mainSkill = state.skills.find(s => !s.isSubmodule && s.remoteUrl)
  if (mainSkill) map.main = mainSkill.remoteUrl
  return map
})

let loadPromise = null
const { on, emit } = useEventBus()

const _onDataChangedCallbacks = []

export function useData() {
  async function loadData() {
    if (loadPromise) return loadPromise
    state.loading = true
    loadPromise = (async () => {
      try {
        const data = await fetchSkills()
        state.skills = data.skills || []
        state.generatedAt = data.generatedAt || ''
        state.error = null
      } catch (err) {
        state.error = err.message || 'Failed to load data'
      } finally {
        state.loading = false
        loadPromise = null
      }
    })()
    return loadPromise
  }

  async function loadExtended() {
    try {
      const data = await fetchSkillsFull()
      state.repoNodes = data.repoNodes || []
      state.submodules = data.submodules || []
      state.relationships = data.relationships || []
      state.gitLogs = data.gitLogs || { main: [], submodules: {} }
    } catch (err) {
      console.error('Extended data load failed:', err)
    }
  }

  async function refresh() {
    loadPromise = null
    state.loading = true
    try {
      const data = await fetchSkillsRefresh()
      state.skills = data.skills || []
      state.repoNodes = data.repoNodes || []
      state.submodules = data.submodules || []
      state.relationships = data.relationships || []
      state.gitLogs = data.gitLogs || { main: [], submodules: {} }
      state.generatedAt = data.generatedAt || ''
      state.error = null
    } catch (err) {
      state.error = err.message || 'Failed to refresh'
    } finally {
      state.loading = false
    }
    emit('data-changed')
  }

  function onDataChanged(callback) {
    _onDataChangedCallbacks.push(callback)
    return () => {
      const idx = _onDataChangedCallbacks.indexOf(callback)
      if (idx >= 0) _onDataChangedCallbacks.splice(idx, 1)
    }
  }

  return {
    state,
    remoteUrlMap,
    loadData,
    loadExtended,
    refresh,
    onDataChanged,
  }
}
