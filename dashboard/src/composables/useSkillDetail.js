import { reactive } from 'vue'
import { useData } from './useData.js'

const state = reactive({
  skill: null,
  open: false,
  activeTab: 'details',
  fileDrawerOpen: false,
})

export function useSkillDetail() {
  const { state: dataState } = useData()

  function show(skillName, options = {}) {
    const found = dataState.skills.find(s => s.name === skillName || s.id === skillName)
    if (found) {
      state.skill = found
      state.activeTab = options.tab || 'details'
      state.open = true
    }
  }

  function close() {
    state.open = false
    state.skill = null
    state.activeTab = 'details'
    state.fileDrawerOpen = false
  }

  function openFileDrawer() {
    state.fileDrawerOpen = true
  }

  function closeFileDrawer() {
    state.fileDrawerOpen = false
  }

  return { state, show, close, openFileDrawer, closeFileDrawer }
}
