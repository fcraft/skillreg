<template>
  <section class="hooks-section">
    <div class="section-header">
      <h2>Hooks 管理</h2>
      <div class="section-actions">
        <QButton type="secondary" size="small" :disabled="loading" @click="refreshAll">
          <RefreshCw :size="14" /> 刷新
        </QButton>
      </div>
    </div>

    <div v-if="loading" class="hooks-loading">加载中...</div>

    <div v-else>
      <QTabs v-model="activeTab" :tabs="tabs" />

      <!-- Agent-hub hooks -->
      <div v-if="activeTab === 'native'" class="hooks-panel">
        <QCard v-if="nativeHooks.length === 0" empty>
          <p class="hooks-empty-text">暂无 agent-hub 内置 Hook。将 hook 脚本放入 <code>hooks/</code> 目录即可自动发现。</p>
        </QCard>
        <HookItem
          v-for="hook in nativeHooks"
          :key="hook.id"
          :hook="hook"
          @toggle="toggleHook"
        />
      </div>

      <!-- Repos hooks -->
      <div v-if="activeTab === 'repos'" class="hooks-panel">
        <QCard v-if="repoHooks.length === 0" empty>
          <p class="hooks-empty-text">暂无第三方仓库 Hook。将 hook 脚本放入 <code>repos/&lt;name&gt;/hooks/</code> 目录即可自动发现。</p>
        </QCard>
        <div v-for="group in groupedRepoHooks" :key="group.source">
          <div class="hooks-group-label">{{ group.source }}</div>
          <HookItem
            v-for="hook in group.hooks"
            :key="hook.id"
            :hook="hook"
            @toggle="toggleHook"
          />
        </div>
      </div>

      <!-- Third-party hooks -->
      <div v-if="activeTab === 'third'" class="hooks-panel">
        <QCard v-if="thirdParty.length === 0" empty>
          <p class="hooks-empty-text">暂未检测到第三方 Hook（在 settings.json 中但不在当前项目中的 hook）。</p>
        </QCard>
        <div v-for="hook in thirdParty" :key="hook.id || hook.command" class="hook-item hook-item--third">
          <div class="hook-item-main">
            <span class="hook-item-name">{{ hook.command || hook.id }}</span>
            <span class="hook-item-source third-party-badge">第三方</span>
          </div>
          <div class="hook-item-actions">
            <!-- Third-party hooks can only be removed (no install needed) -->
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import QCard from './QCard.vue'
import QButton from './QButton.vue'
import QTabs from './QTabs.vue'
import HookItem from './HookItem.vue'
import { useToast } from '../composables/useToast.js'
import { getHookStatus, installHook, uninstallHook } from '../api/index.js'

const toast = useToast()

const tabs = [
  { key: 'native', label: 'Agent-hub Hooks' },
  { key: 'repos', label: '仓库 Hooks' },
  { key: 'third', label: '第三方 Hooks' },
]

const activeTab = ref('native')
const loading = ref(true)
const actionLoading = ref({})
const settingsLocal = ref(false)
const hooks = ref([])
const thirdParty = ref([])

const nativeHooks = computed(() =>
  hooks.value.filter(h => h.source === 'hooks/' || h.source === 'global')
)
const repoHooks = computed(() =>
  hooks.value.filter(h => h.source !== 'hooks/' && h.source !== 'global' && h.source !== 'third-party')
)

const groupedRepoHooks = computed(() => {
  const groups = {}
  for (const h of repoHooks.value) {
    if (!groups[h.source]) groups[h.source] = []
    groups[h.source].push(h)
  }
  return Object.entries(groups).map(([source, hooks]) => ({ source, hooks }))
})

async function refreshAll() {
  loading.value = true
  try {
    const status = await getHookStatus(settingsLocal.value)
    hooks.value = status.hooks || []
    thirdParty.value = status.thirdParty || []
  } catch (err) {
    toast.error(`加载失败: ${err.message}`)
  } finally {
    loading.value = false
  }
}

async function toggleHook(hook, install = true) {
  const hookId = hook.id || hook.hook_id
  actionLoading.value = { ...actionLoading.value, [hookId]: true }
  try {
    if (install) {
      const res = await installHook(hookId, settingsLocal.value)
      if (res.success) {
        toast.success(`已安装: ${hookId}`)
      } else {
        toast.warn(res.error || `安装失败: ${hookId}`)
      }
    } else {
      const res = await uninstallHook(hookId, settingsLocal.value)
      if (res.success) {
        toast.success(`已卸载: ${hookId}`)
      } else {
        toast.warn(res.error || `卸载失败: ${hookId}`)
      }
    }
    await refreshAll()
  } catch (err) {
    toast.error(`操作失败: ${err.message}`)
  } finally {
    actionLoading.value = { ...actionLoading.value, [hookId]: false }
  }
}

onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.hooks-section {
  margin-bottom: var(--qqx-space-3xl);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  margin-bottom: var(--qqx-space-lg);
}

.section-header h2 {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
}

.section-actions {
  margin-left: auto;
}

.hooks-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--qqx-text-tertiary);
}

.hooks-panel {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

.hooks-empty-text {
  color: var(--qqx-text-tertiary);
  text-align: center;
  margin: 0;
}

.hooks-empty-text code {
  font-family: var(--qqx-font-mono, monospace);
  background: var(--qqx-bg-subtle);
  padding: 2px 6px;
  border-radius: var(--qqx-radius-xs);
  font-size: var(--qqx-font-size-small);
}

.hooks-group-label {
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-secondary);
  padding: var(--qqx-space-sm) 0 var(--qqx-space-xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.hook-item--third {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  background: var(--qqx-bg-card);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
}

.hook-item-main {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  flex: 1;
  min-width: 0;
}

.hook-item-name {
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  white-space: nowrap;
}

.hook-item-source {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
}

.third-party-badge {
  display: inline-block;
  padding: 1px 8px;
  background: var(--qqx-bg-subtle);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  font-size: var(--qqx-font-size-mini, 11px);
  color: var(--qqx-text-tertiary);
}

.hook-item-actions {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  flex-shrink: 0;
  margin-left: var(--qqx-space-md);
}
</style>
