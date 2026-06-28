import { reactive } from 'vue'

const state = reactive({
  visible: false,
  message: '',
  tint: 'brand',
  position: 'bottom',
  duration: 3500,
  actionLabel: '',
  onAction: null,
})

let actionHandler = null

export function useToast() {
  function show(message, options = {}) {
    const { tint = 'brand', position = 'bottom', duration = 3500, actionLabel = '', onAction = null } = options
    // Clear any pending action handler
    if (actionHandler) state.onAction = null
    actionHandler = onAction

    state.message = message
    state.tint = tint
    state.position = position
    state.duration = duration
    state.actionLabel = actionLabel
    state.onAction = onAction
    state.visible = true
  }

  function success(message, opts = {}) { show(message, { ...opts, tint: 'success' }) }
  function error(message, opts = {}) { show(message, { ...opts, tint: 'error', duration: 5000 }) }
  function warn(message, opts = {}) { show(message, { ...opts, tint: 'warn' }) }
  function info(message, opts = {}) { show(message, { ...opts, tint: 'brand' }) }
  function hide() { state.visible = false }

  function onAction() {
    if (state.onAction) state.onAction()
    hide()
  }

  return { state, show, success, error, warn, info, hide, onAction }
}
