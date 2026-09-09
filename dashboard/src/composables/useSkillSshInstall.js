import { onMounted, onUnmounted, ref } from 'vue'
import * as api from '../api/remoteSync.js'
import { isActiveRun } from '../sources/remoteSyncState.js'

export function useSkillSshInstall(skillName) {
  const connections = ref([]), targets = ref([]), rows = ref({})
  const loading = ref(true), error = ref(''), busy = ref(false)
  const planned = ref(null), run = ref(null), showRun = ref(false)
  let disposed = false, timer, selectedTarget

  async function load() {
    loading.value = true
    error.value = ''
    try {
      const [c, t] = await Promise.all([api.fetchConnections(), api.fetchTargets()])
      if (!disposed) { connections.value = c; targets.value = t.filter(item => item.transport === 'ssh') }
    } catch (err) { if (!disposed) error.value = err.message }
    finally { if (!disposed) loading.value = false }
  }

  async function inspect(target) {
    if (rows.value[target.id]?.loading || busy.value || isActiveRun(run.value)) return
    rows.value[target.id] = { loading: true }
    selectedTarget = target.id
    try {
      const preview = await api.previewSync([target.id], [skillName])
      if (disposed) return
      const item = preview.targets[0]
      rows.value[target.id] = { status: item.skills[0]?.status, error: item.error?.message, observedAt: item.observedAt }
      if (!item.error && selectedTarget === target.id) { error.value = ''; planned.value = preview }
    } catch (err) { if (!disposed) rows.value[target.id] = { error: err.message } }
    finally { if (!disposed) rows.value[target.id].loading = false }
  }

  async function poll() {
    try {
      const updated = await api.fetchRun(run.value.id)
      if (disposed) return
      run.value = updated
      if (!isActiveRun(updated)) {
        for (const result of updated.results) {
          const skill = result.skills.find(s => s.name === skillName)
          rows.value[result.target.id] = skill?.state === 'succeeded'
            ? { status: 'synced', observedAt: updated.finishedAt }
            : { error: skill?.error?.message || result.error?.message || '同步未完成，请重新检查' }
        }
        return
      }
    } catch (err) {
      if (!disposed) error.value = `读取进度失败：${err.message}`
      return
    }
    if (!disposed) timer = setTimeout(poll, 1500)
  }

  async function action(callback) {
    if (busy.value) return
    busy.value = true; error.value = ''
    try { await callback() } catch (err) { if (!disposed) error.value = err.message }
    finally { if (!disposed) busy.value = false }
  }
  async function execute(force) {
    await action(async () => {
      const result = await api.executePreview(planned.value.id, force)
      if (disposed) return
      run.value = result; planned.value = null; showRun.value = true
      await poll()
    })
  }
  async function retry() {
    await action(async () => {
      const result = await api.retryRun(run.value.id)
      if (!disposed) { planned.value = result; showRun.value = false }
    })
  }
  async function cancel() {
    await action(async () => {
      const result = await api.cancelRun(run.value.id)
      if (!disposed) run.value = result
    })
  }
  function refreshRun() { clearTimeout(timer); poll() }
  onMounted(load)
  onUnmounted(() => { disposed = true; clearTimeout(timer) })
  return { connections, targets, rows, loading, error, busy, planned, run, showRun, load, inspect, execute, retry, cancel, refreshRun }
}
