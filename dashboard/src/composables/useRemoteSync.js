import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import * as api from '../api/remoteSync.js'
import { isActiveRun } from '../sources/remoteSyncState.js'

export function useRemoteSync() {
  const connections = ref([]), targets = ref([]), observations = ref([]), runs = ref([])
  const selectedConnection = ref(''), selectedTargets = ref([]), selectedSkills = ref([])
  const loading = ref(true), busy = ref(false), error = ref(''), actionError = ref('')
  const loadError = ref(''), pollError = ref('')
  const planned = ref(null), currentRun = ref(null)
  const activeConnection = computed(() => connections.value.find(c => c.id === selectedConnection.value))
  const connectionTargets = computed(() => targets.value.filter(t => t.connectionId === selectedConnection.value))
  const observationFor = id => observations.value.find(o => o.targetId === id)
  let timer, disposed = false, selectionRevision = 0
  watch(selectedConnection, () => { selectedTargets.value = []; planned.value = null; actionError.value = '' })
  watch([selectedConnection, selectedTargets, selectedSkills], () => { selectionRevision++; planned.value = null }, { deep: true, flush: 'sync' })
  async function connectionSaved(connection) { connections.value = await api.fetchConnections(); selectedConnection.value = connection.id }
  async function loadTargets() { try { targets.value = await api.fetchTargets() } catch (err) { error.value = err.message } }
  async function loadHistory() { try { runs.value = await api.fetchRuns() } catch (err) { error.value = err.message } }
  async function action(callback) {
    if (busy.value) return
    busy.value = true; error.value = ''; actionError.value = ''
    try { await callback() } catch (err) { if (!disposed) { error.value = err.message; actionError.value = err.message } }
    finally { if (!disposed) busy.value = false }
  }
  async function check() { await action(async () => { await api.checkConnection(selectedConnection.value); connections.value = await api.fetchConnections() }) }
  async function preview() {
    await previewFor([...selectedTargets.value], [...selectedSkills.value])
  }
  async function previewFor(ids, skills) {
    const revision = selectionRevision
    await action(async () => {
      try {
        const result = await api.previewSync(ids, skills)
        if (disposed || revision !== selectionRevision) return
        planned.value = result
        const observed = await api.fetchObservations()
        if (!disposed) observations.value = observed
      } catch (err) { if (!disposed && revision === selectionRevision) throw err }
    })
  }
  async function execute(force) { await action(async () => { currentRun.value = await api.executePreview(planned.value.id, force); planned.value = null; await loadHistory() }) }
  function openRun(run) { actionError.value = ''; currentRun.value = run }
  async function retry() { await action(async () => { planned.value = await api.retryRun(currentRun.value.id); currentRun.value = null }) }
  async function cancel() { await action(async () => { currentRun.value = await api.cancelRun(currentRun.value.id) }) }
  async function poll() {
    try {
      if (currentRun.value && isActiveRun(currentRun.value)) {
        const id = currentRun.value.id
        const updated = await api.fetchRun(id)
        if (disposed) return
        if (currentRun.value?.id === id) currentRun.value = updated
        pollError.value = ''
        if (!isActiveRun(updated)) {
          const [history, observed] = await Promise.all([api.fetchRuns(), api.fetchObservations()])
          if (!disposed) { runs.value = history; observations.value = observed }
        }
      } else if (runs.value.some(isActiveRun) || pollError.value) {
        const [history, observed] = await Promise.all([api.fetchRuns(), api.fetchObservations()])
        if (!disposed) { runs.value = history; observations.value = observed; pollError.value = '' }
      }
    } catch (err) { if (!disposed) pollError.value = err.message }
    finally { if (!disposed) timer = setTimeout(poll, 1500) }
  }
  async function load() {
    clearTimeout(timer)
    loading.value = true; loadError.value = ''
    try {
      const [c, t, o, r] = await Promise.all([api.fetchConnections(), api.fetchTargets(), api.fetchObservations(), api.fetchRuns()])
      if (disposed) return
      connections.value = c; targets.value = t; observations.value = o; runs.value = r; selectedConnection.value = c[0]?.id || ''
    } catch (err) { if (!disposed) loadError.value = err.message }
    finally { if (!disposed) { loading.value = false; if (!loadError.value) poll() } }
  }
  onMounted(load)
  onUnmounted(() => { disposed = true; clearTimeout(timer) })
  return { connections, targets, runs, selectedConnection, selectedTargets, selectedSkills, loading, busy, error, actionError, loadError, pollError, load, planned, currentRun, activeConnection, connectionTargets, observationFor, connectionSaved, loadTargets, loadHistory, action, check, preview, previewFor, execute, openRun, retry, cancel }
}
