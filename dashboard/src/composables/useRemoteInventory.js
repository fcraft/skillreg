import { onUnmounted, ref } from 'vue'
import { fetchInventory } from '../api/remoteSync.js'

export function useRemoteInventory() {
  const entries = ref({}), activeTargetId = ref(null)
  let disposed = false
  async function scan(target) {
    if (entries.value[target.id]?.loading) return
    entries.value[target.id] = { data: entries.value[target.id]?.data, loading: true, error: '' }
    try {
      const data = await fetchInventory(target.id)
      if (!disposed) entries.value[target.id] = { data, loading: false, error: '' }
    } catch (err) {
      if (!disposed) entries.value[target.id] = { ...entries.value[target.id], loading: false, error: err.message }
    }
  }
  function open(target) {
    activeTargetId.value = target.id
    if (!entries.value[target.id]) scan(target)
  }
  async function added(targets) {
    if (!targets.length) return
    activeTargetId.value = targets[0].id
    for (const target of targets) {
      if (disposed) break
      await scan(target)
    }
  }
  onUnmounted(() => { disposed = true })
  return { entries, activeTargetId, scan, open, added }
}
