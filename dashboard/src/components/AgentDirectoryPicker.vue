<template>
  <QModal :model-value="visible" :title="firstVisit ? '选择要同步到的 Agent' : '添加内置 Agent'" width="560px" @update:model-value="dismiss">
    <p class="intro">勾选目录并加入后，即可向这些 Agent 安装 Skill。</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="loading">正在探测本机目录…</p>
    <template v-else>
      <input v-model="query" type="search" class="search" aria-label="搜索 Agent 或路径" placeholder="搜索 Agent 或路径">
      <h3>本机已发现 · {{ groups.detected.length }}</h3>
      <p v-if="!groups.detected.length" class="intro">没有匹配的本机目录，可从下方预设中选择。</p>
      <template v-for="group in ['detected', 'presets']" :key="group">
        <button v-if="group === 'presets'" class="presets" :aria-expanded="expanded" @click="expanded = !expanded">
          其他内置预设（{{ groups.presets.length }}）{{ expanded ? '收起' : '展开' }}
        </button>
        <div v-if="group === 'detected' || expanded" class="rows">
          <div v-for="agent in groups[group]" :key="agent.id" class="row">
            <label>
              <input v-model="selected" type="checkbox" :value="agent.id" :disabled="agent.added || busy">
              <ProviderIcon :target="agent" :size="22" />
              <span class="info"><strong>{{ agent.name }}</strong><code :title="agent.path">{{ formatAgentDisplayPath(agent.path, agent.rel_path) }}</code></span>
            </label>
            <small v-if="agent.added">已加入</small>
            <small v-else-if="agent.detected">本机已发现</small>
            <QButton v-if="!agent.added && !firstVisit" type="text" size="small" :disabled="busy" @click="save([agent.id])">加入</QButton>
          </div>
        </div>
      </template>
    </template>
    <template #footer>
      <QButton type="ghost" :disabled="busy" @click="dismiss">{{ firstVisit ? '稍后再说' : '关闭' }}</QButton>
      <QButton type="primary" :disabled="!selected.length || busy" @click="save(selected)">加入所选（{{ selected.length }}）</QButton>
    </template>
  </QModal>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { fetchBuiltinAgents, joinBuiltinAgents } from '../api/index.js'
import { useEventBus } from '../composables/useEventBus.js'
import { formatAgentDisplayPath, needsAgentOnboarding, partitionAgentCatalog } from '../sources/agentTargets.js'
import QModal from './QModal.vue'
import QButton from './QButton.vue'
import ProviderIcon from './ProviderIcon.vue'

const { on, emit } = useEventBus()
const visible = ref(false)
const firstVisit = ref(false)
const agents = ref([])
const selected = ref([])
const query = ref('')
const expanded = ref(false)
watch(query, value => { expanded.value = Boolean(value.trim()) })
const groups = computed(() => partitionAgentCatalog(agents.value, query.value))
const loading = ref(false)
const busy = ref(false)
const error = ref('')
let requestId = 0

async function open(automatic) {
  const id = ++requestId
  visible.value = !automatic
  loading.value = true
  firstVisit.value = automatic
  selected.value = []
  query.value = ''
  expanded.value = false
  error.value = ''
  try {
    const catalog = await fetchBuiltinAgents()
    if (id !== requestId) return
    agents.value = catalog.agents
    visible.value = !automatic || needsAgentOnboarding(catalog)
  } catch (err) {
    if (id === requestId) error.value = err.message
  } finally {
    if (id === requestId) loading.value = false
  }
}

async function save(ids, skipped = false) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await joinBuiltinAgents(ids, firstVisit.value ? (skipped ? 'skipped' : 'completed') : null)
    visible.value = false
    if (ids.length) {
      emit('agent-targets-changed')
      emit('data-changed')
    }
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

function dismiss() {
  if (busy.value) return
  if (firstVisit.value) return save([], true)
  requestId++
  visible.value = false
}

const unsubscribe = on('open-agent-picker', () => open(false))
onMounted(() => open(true))
onUnmounted(() => { requestId++; unsubscribe() })
</script>

<style scoped>
.intro, code, small { color: var(--sr-text-secondary); }
.intro { margin: 0 0 16px; }
.search, .row { background: var(--sr-bg-group); border-radius: var(--sr-radius-md); }
.search { width: 100%; box-sizing: border-box; border: 0; padding: 12px; color: var(--sr-text-primary); font: inherit; }
h3, .presets { margin: 18px 0 8px; font-size: 14px; }
.presets { border: 0; background: transparent; color: var(--sr-text-secondary); cursor: pointer; padding: 4px 0; }
.rows { display: grid; gap: 5px; }
.row, label { display: flex; align-items: center; gap: 12px; }
.row { padding: 10px 14px; }
label { flex: 1; min-width: 0; cursor: pointer; }
.info { min-width: 0; display: grid; gap: 3px; }
code { overflow-wrap: anywhere; font-size: 12px; }
</style>
