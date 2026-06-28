import { ref, computed } from 'vue'
import { useSshHosts } from './useSshHosts.js'

// Singleton state
const activeHostId = ref(null)

export function useSshMode() {
  const { hosts } = useSshHosts()

  const isRemoteMode = computed(() => !!activeHostId.value)

  const activeHost = computed(() => {
    if (!activeHostId.value) return null
    return hosts.value.find(h => h.id === activeHostId.value) || null
  })

  function enterRemoteMode(hostId) {
    activeHostId.value = hostId
  }

  function exitRemoteMode() {
    activeHostId.value = null
  }

  return {
    activeHostId,
    activeHost,
    isRemoteMode,
    enterRemoteMode,
    exitRemoteMode,
  }
}
