import { ref, reactive } from 'vue'
import * as sshApi from '../api/ssh.js'

// Module-level singleton state (shared across all consumers)
const hosts = ref([])
const checks = reactive({})       // { [hostId]: { ok, reason, detail } }
const statusCache = reactive({})  // { [hostId]: { ok, output, error } }

export function useSshHosts() {
  const loading = ref(false)
  const error = ref(null)

  // Selected host for detail panel
  const selectedHostId = ref(null)

  // ── Host list ──────────────────────────────────

  async function loadHosts() {
    loading.value = true
    error.value = null
    try {
      const data = await sshApi.fetchHosts()
      hosts.value = data.hosts || []
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addHost(config) {
    const data = await sshApi.addHost(config)
    await loadHosts()
    return data
  }

  async function updateHost(id, patch) {
    const data = await sshApi.updateHost(id, patch)
    // Update local list
    const idx = hosts.value.findIndex(h => h.id === id)
    if (idx !== -1) hosts.value[idx] = data.host
    return data
  }

  async function removeHost(id) {
    await sshApi.deleteHost(id)
    if (selectedHostId.value === id) selectedHostId.value = null
    delete checks[id]
    delete statusCache[id]
    await loadHosts()
  }

  // ── Connection check ──────────────────────────

  async function checkHost(id) {
    checks[id] = { loading: true }
    try {
      const result = await sshApi.checkHost(id)
      checks[id] = result
      return result
    } catch (err) {
      checks[id] = { ok: false, reason: 'error', detail: err.message }
      return checks[id]
    }
  }

  async function checkAllHosts() {
    const results = await Promise.allSettled(
      hosts.value.map(h => checkHost(h.id))
    )
    return results
  }

  // ── Remote status ─────────────────────────────

  async function loadHostStatus(id) {
    statusCache[id] = { loading: true }
    try {
      const result = await sshApi.getHostStatus(id)
      statusCache[id] = result
      return result
    } catch (err) {
      statusCache[id] = { ok: false, error: err.message }
      return statusCache[id]
    }
  }

  async function triggerSync(id) {
    statusCache[id] = { loading: true, syncing: true }
    try {
      const result = await sshApi.syncHost(id)
      statusCache[id] = result
      // Refresh status after sync
      await loadHostStatus(id)
      return result
    } catch (err) {
      statusCache[id] = { ok: false, error: err.message }
      return statusCache[id]
    }
  }

  async function installHost(id) {
    statusCache[id] = { loading: true, installing: true }
    try {
      const result = await sshApi.installHost(id)
      statusCache[id] = result
      // Re-check connection and load status
      await checkHost(id)
      if (result.ok) {
        await loadHostStatus(id)
      }
      return result
    } catch (err) {
      statusCache[id] = { ok: false, error: err.message }
      return statusCache[id]
    }
  }

  // ── Helpers ───────────────────────────────────

  function selectHost(id) {
    selectedHostId.value = id
    if (id && !statusCache[id]) {
      loadHostStatus(id)
    }
  }

  return {
    hosts, loading, error,
    selectedHostId, checks, statusCache,
    loadHosts, addHost, updateHost, removeHost,
    checkHost, checkAllHosts,
    loadHostStatus, triggerSync, installHost,
    selectHost,
  }
}
