import { ref, onMounted, onUnmounted } from 'vue'
import { useData } from './useData.js'

const isServerDown = ref(false)

let timer = null
let failCount = 0

const FAST_RETRY_INTERVAL = 2_000
const FAST_RETRY_MAX = 3
const RECOVERY_POLL = 10_000
const KEEPALIVE_ACTIVE = 60_000
const KEEPALIVE_IDLE = 120_000

function getKeepaliveInterval() {
  return document.visibilityState === 'hidden' ? KEEPALIVE_IDLE : KEEPALIVE_ACTIVE
}

async function ping() {
  try {
    const res = await fetch('/api/health')
    if (!res.ok) throw new Error('unhealthy')
    if (failCount > 0) {
      failCount = 0
      if (isServerDown.value) {
        isServerDown.value = false
      }
    }
    return true
  } catch {
    return false
  }
}

function clearTimer() {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
}

async function fastDetect() {
  for (let i = 0; i < FAST_RETRY_MAX; i++) {
    if (await ping()) return true
    if (i < FAST_RETRY_MAX - 1) {
      await new Promise(r => { setTimeout(r, FAST_RETRY_INTERVAL) })
    }
  }
  return false
}

function startRecoveryPoll() {
  clearTimer()
  timer = setTimeout(async () => {
    const alive = await ping()
    if (alive) {
      // Server recovered — refresh data and switch to keepalive
      try {
        const { refresh } = useData()
        await refresh()
      } catch { /* refresh may fail during transition */ }
      isServerDown.value = false
      failCount = 0
      startKeepalive()
    } else {
      startRecoveryPoll()
    }
  }, RECOVERY_POLL)
}

function startKeepalive() {
  clearTimer()
  timer = setTimeout(async () => {
    await ping()
    if (!isServerDown.value) {
      startKeepalive()
    }
  }, getKeepaliveInterval())
}

function handleVisibilityChange() {
  if (isServerDown.value) return // recovery poll has its own interval
  clearTimer()
  startKeepalive()
}

export function useServerHealth() {
  onMounted(async () => {
    // Phase 1: immediate fast detection (~6s max)
    const alive = await fastDetect()

    if (alive) {
      startKeepalive()
    } else {
      isServerDown.value = true
      startRecoveryPoll()
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
  })

  onUnmounted(() => {
    clearTimer()
    document.removeEventListener('visibilitychange', handleVisibilityChange)
  })

  return { isServerDown, ping }
}
