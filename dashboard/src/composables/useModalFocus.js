import { nextTick, onMounted, onUnmounted, watch } from 'vue'

const stack = []
const focusable = 'button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])'

export function useModalFocus(isOpen, panel, close) {
  const entry = {}
  let previous, lastFocused
  function remember(event) {
    if (!isOpen()) lastFocused = event.target
  }
  onMounted(() => document.addEventListener('focusin', remember))
  function release() {
    const index = stack.indexOf(entry)
    if (index === -1) return
    const wasTop = index === stack.length - 1
    stack.splice(index, 1)
    document.removeEventListener('keydown', keydown, true)
    if (wasTop && previous?.isConnected && !previous.closest('[inert]')) previous.focus({ preventScroll: true })
  }
  function keydown(event) {
    if (stack.at(-1) !== entry || !panel.value || event.isComposing) return
    const activeDialog = event.target.closest?.('[role="dialog"]')
    if (activeDialog && activeDialog !== panel.value && !panel.value.contains(activeDialog)) return
    if (event.key === 'Escape') {
      event.preventDefault(); event.stopImmediatePropagation(); close()
    } else if (event.key === 'Tab') {
      const items = [...panel.value.querySelectorAll(focusable)].filter(item => !item.disabled && !item.closest('[inert]') && item.getClientRects().length)
      const first = items[0], last = items.at(-1), active = document.activeElement
      if (!first) { event.preventDefault(); panel.value.focus(); return }
      if (!items.includes(active) || (event.shiftKey ? active === first : active === last)) {
        event.preventDefault(); (event.shiftKey ? last : first).focus()
      }
    }
  }
  watch(isOpen, async open => {
    if (!open) { release(); return }
    previous = document.activeElement === document.body ? lastFocused : document.activeElement
    stack.push(entry)
    document.addEventListener('keydown', keydown, true)
    await nextTick()
    if (isOpen() && stack.at(-1) === entry) panel.value?.focus({ preventScroll: true })
  }, { immediate: true, flush: 'post' })
  onUnmounted(() => { release(); document.removeEventListener('focusin', remember) })
}
