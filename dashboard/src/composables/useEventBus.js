import { reactive } from 'vue'

const listeners = reactive({})

export function useEventBus() {
  function on(event, fn) {
    if (!listeners[event]) listeners[event] = []
    listeners[event].push(fn)
    return () => {
      listeners[event] = listeners[event]?.filter(f => f !== fn)
    }
  }

  function emit(event, payload) {
    for (const fn of listeners[event] || []) {
      fn(payload)
    }
  }

  return { on, emit }
}
