import { reactive } from 'vue'

const state = reactive({
  open: false,
  skill: null,
  type: null, // 'skill' | 'submodule'
  submodulePath: null,
})

export function useContextPanel() {
  function openContext(skill) {
    state.skill = skill
    state.type = 'skill'
    state.submodulePath = null
    state.open = true
  }

  function openSubmoduleContext(submodulePath) {
    state.submodulePath = submodulePath
    state.type = 'submodule'
    state.skill = null
    state.open = true
  }

  function closeContext() {
    state.open = false
    state.skill = null
    state.type = null
    state.submodulePath = null
  }

  return { state, openContext, openSubmoduleContext, closeContext }
}
