<template>
  <section class="remote-inventory" :aria-label="`${target.name} 中的 Skills`" :aria-busy="Boolean(state?.loading)">
    <header class="ssh-list-toolbar">
      <input v-model="query" class="ssh-input" aria-label="搜索远端 Skill" placeholder="按目录名称筛选" />
      <span class="ssh-muted">{{ state?.data?.skills.length ?? '—' }} 个 Skill</span>
      <QButton type="ghost" size="small" :disabled="state?.loading" @click="$emit('refresh')"><RefreshCw :size="14" /> 刷新目录</QButton>
    </header>
    <QLoadingState v-if="state?.loading">正在探测目录，不读取全部文件内容…</QLoadingState>
    <p v-if="state?.error" class="ssh-error" role="alert">{{ state.error }} · 可重试刷新，已有配置会保留</p>
    <template v-if="state?.data">
      <p class="ssh-muted">上次探测 {{ state.data.observedAt }}<template v-if="state.error || state.loading"> · 下方为上次结果</template></p>
      <p v-if="!state.data.exists" class="ssh-muted">目标目录尚不存在，首次安装时会创建</p>
      <p v-else-if="!state.data.skills.length" class="ssh-muted">尚未发现包含 SKILL.md 的 Skill 目录</p>
      <div class="remote-inventory-list">
        <article v-for="skill in filtered" :key="skill.name" class="remote-inventory-row">
          <div class="ssh-row">
            <div class="remote-inventory-info"><strong>{{ skill.name }}</strong><span>{{ sourceNames.has(skill.name) ? 'workspace 中有同名来源' : '仅远端存在' }}</span></div>
            <div class="ssh-actions">
              <QButton type="ghost" size="small" :disabled="documents[skill.name]?.loading" @click="read(skill.name)">查看说明</QButton>
              <QButton v-if="sourceNames.has(skill.name)" type="secondary" tint="brand" size="small" :disabled="busy || state.loading" @click="$emit('preview', skill.name)">对比并同步</QButton>
            </div>
          </div>
        </article>
      </div>
      <p v-if="query && state.data.skills.length && !filtered.length" class="ssh-muted">没有匹配的远端 Skill</p>
      <p v-if="state.data.truncated" class="ssh-muted">目录较大，本次仅展示部分条目</p>
      <QDisclosure v-if="state.data.skipped.length" :id="`inventory-skipped-${target.id}`" :title="`${state.data.skipped.length} 个条目未读取`">
        <p v-for="item in state.data.skipped" :key="item.name" class="ssh-muted">{{ item.name }} · {{ item.message }}</p>
      </QDisclosure>
    </template>
    <QModal :model-value="Boolean(activeName)" :title="activeName + '/SKILL.md'" width="760px" @update:model-value="!$event && (activeName = '')">
      <div class="remote-inventory-document">
        <QLoadingState v-if="documents[activeName]?.loading">正在读取 {{ activeName }}/SKILL.md…</QLoadingState>
        <p v-if="documents[activeName]?.error" class="ssh-error" role="alert">{{ documents[activeName].error }}</p>
        <QButton v-if="documents[activeName]?.error" type="secondary" @click="read(activeName)">重试读取</QButton>
        <p v-if="documents[activeName]?.data?.truncated" class="ssh-muted">内容较长，仅展示前 256 KiB</p>
        <pre v-if="documents[activeName]?.data">{{ documents[activeName].data.content }}</pre>
      </div>
      <template #footer><span class="ssh-muted">远端说明 · 只读</span><QButton type="primary" @click="activeName = ''">关闭说明</QButton></template>
    </QModal>
  </section>
</template>
<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import QButton from '../QButton.vue'
import QDisclosure from '../QDisclosure.vue'
import QLoadingState from '../QLoadingState.vue'
import QModal from '../QModal.vue'
import { fetchRemoteDocument } from '../../api/remoteSync.js'
const props = defineProps({ target: Object, state: Object, sourceNames: Set, busy: Boolean })
defineEmits(['refresh', 'preview'])
const query = ref(''), documents = ref(Object.create(null)), activeName = ref('')
let disposed = false, generation = 0
const filtered = computed(() => (props.state?.data?.skills || []).filter(skill => skill.name.toLowerCase().includes(query.value.toLowerCase())))
watch(() => props.state?.data, () => { generation++; documents.value = Object.create(null); activeName.value = '' })
async function read(name) {
  activeName.value = name
  if (documents.value[name]?.data) return
  if (documents.value[name]?.loading) return
  const current = generation
  documents.value[name] = { loading: true }
  try {
    const data = await fetchRemoteDocument(props.target.id, name)
    if (!disposed && current === generation) documents.value[name] = { data }
  } catch (err) { if (!disposed && current === generation) documents.value[name] = { error: err.message } }
}
onUnmounted(() => { disposed = true })
</script>
<style scoped>
.remote-inventory { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.remote-inventory-list { flex: 1; min-height: 0; overflow-y: auto; padding: 3px; }
.remote-inventory-row { padding: 8px; border-bottom: 1px solid var(--qqx-border-color); border-radius: 6px; }
.remote-inventory-row:hover { background: var(--qqx-bg-hover); }
.remote-inventory-row > .ssh-row { flex-wrap: nowrap; }
.remote-inventory-info { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; align-items: center; flex: 1; min-width: 0; font-size: 13px; }
.remote-inventory-info strong, .remote-inventory-info span { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.remote-inventory-row .ssh-actions { flex-shrink: 0; }
.remote-inventory-info span, .remote-inventory-document { color: var(--qqx-text-secondary); font-size: 12px; }
.remote-inventory-document pre { padding: 16px; max-height: 55vh; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; background: var(--qqx-bg-base); color: var(--qqx-text-primary); border-radius: var(--qqx-radius-xs); line-height: 1.6; }
@media (max-width: 1100px) {
  .remote-inventory-info { grid-template-columns: minmax(0, 1fr); gap: 4px; }
}
@media (max-width: 540px) {
  .remote-inventory-row > .ssh-row { flex-wrap: wrap; gap: 6px; }
  .remote-inventory-info { flex-basis: 100%; }
}
</style>
