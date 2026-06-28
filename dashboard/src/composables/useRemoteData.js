import { ref, computed, watch } from 'vue'
import { useSshMode } from './useSshMode.js'
import { useData } from './useData.js'
import * as sshApi from '../api/ssh.js'

export function useRemoteData() {
  const { activeHostId, isRemoteMode, activeHost } = useSshMode()
  const { state: localState } = useData()

  const remoteLoading = ref(false)
  const remoteError = ref(null)

  // Remote structured status: { ok, targets, config, skillStatus }
  const remoteStatus = ref(null)

  // Remote config: { ok, config }
  const remoteConfig = ref(null)

  // Composable: local skill array augmented with remote status
  const skills = computed(() => {
    const base = localState.skills || []
    if (!isRemoteMode.value) return base

    const ss = remoteStatus.value?.skillStatus || {}
    return base.map(s => ({
      ...s,
      _remoteStatus: ss[s.name]?.status || 'not_installed',
      _remoteTargets: ss[s.name]?.targets || [],
    }))
  })

  // Remote targets (only meaningful in remote mode)
  const targets = computed(() => {
    if (!isRemoteMode.value) return []
    return remoteStatus.value?.targets || []
  })

  // Remote sync config
  const config = computed(() => {
    return remoteConfig.value?.config || null
  })

  // Load remote structured status
  async function loadRemoteStatus() {
    if (!activeHostId.value) return
    remoteLoading.value = true
    remoteError.value = null
    try {
      const result = await sshApi.getStructuredStatus(activeHostId.value)
      remoteStatus.value = result
      return result
    } catch (err) {
      remoteError.value = err.message
      return { ok: false, error: err.message }
    } finally {
      remoteLoading.value = false
    }
  }

  // Load remote sync config
  async function loadRemoteConfig() {
    if (!activeHostId.value) return
    try {
      const result = await sshApi.getHostConfig(activeHostId.value)
      remoteConfig.value = result
      return result
    } catch (err) {
      return { ok: false, error: err.message }
    }
  }

  // Trigger remote sync
  async function triggerRemoteSync(skill, target) {
    if (!activeHostId.value) return
    remoteLoading.value = true
    try {
      const result = await sshApi.syncHost(activeHostId.value, { skill, target })
      await loadRemoteStatus()
      return result
    } catch (err) {
      remoteError.value = err.message
      return { ok: false, error: err.message }
    } finally {
      remoteLoading.value = false
    }
  }

  // Sync specific skill to remote
  async function syncSkillToRemote(skillName, targetName) {
    return triggerRemoteSync(skillName, targetName)
  }

  // Update remote config
  async function updateRemoteConfig(newConfig) {
    if (!activeHostId.value) return
    try {
      const result = await sshApi.updateHostConfig(activeHostId.value, newConfig)
      if (result.ok) {
        remoteConfig.value = { ok: true, config: newConfig }
        await loadRemoteStatus()
      }
      return result
    } catch (err) {
      return { ok: false, error: err.message }
    }
  }

  // Auto-load when entering remote mode
  watch(activeHostId, async (newId) => {
    if (newId) {
      await Promise.all([loadRemoteStatus(), loadRemoteConfig()])
    } else {
      remoteStatus.value = null
      remoteConfig.value = null
    }
  }, { immediate: true })

  return {
    remoteLoading,
    remoteError,
    remoteStatus,
    remoteConfig,
    skills,
    targets,
    config,
    loadRemoteStatus,
    loadRemoteConfig,
    triggerRemoteSync,
    syncSkillToRemote,
    updateRemoteConfig,
  }
}
