<template>
  <QModal :model-value="modelValue" title="添加远端安装目标" width="580px" @update:model-value="$emit('update:modelValue', $event)">
    <div class="ssh-form">
      <p class="ssh-muted">{{ connection?.name }} · {{ connection?.host }}</p>
      <QSelect v-model="scope" label="安装范围" :options="[{ value: 'global', label: '全局 Agent' }, { value: 'project', label: '项目内 Agent' }]" @change="reset" />
      <label v-if="scope === 'project'">项目根目录<input v-model="root" class="ssh-input" placeholder="/path/to/project" @input="reset" /></label>
      <QButton type="secondary" :disabled="busy || (scope === 'project' && !root)" @click="discover">{{ busy ? '发现中…' : '发现 Agent 目录' }}</QButton>
      <div v-if="discovered" class="ssh-target-options">
        <p v-if="!candidates.length" class="ssh-muted">没有发现 Agent 目录，可手动填写安装路径</p>
        <QCheckbox v-for="item in candidates" :key="item.path" class="ssh-option" :model-value="selected.includes(item.path)" @update:model-value="selected = $event ? [...selected, item.path] : selected.filter(path => path !== item.path)"><span><span class="ssh-provider-label"><ProviderIcon :target="item" :size="16" /><span>{{ item.name || item.agentKind }}</span></span><code>{{ item.path }}</code></span></QCheckbox>
      </div>
      <QDisclosure id="ssh-manual-target" title="手动指定目录"><div class="ssh-form ssh-advanced">
        <label>目标名称<input v-model="manualName" class="ssh-input" placeholder="项目 Codex" /></label>
        <label>Skill 安装目录<input v-model="manualPath" class="ssh-input" placeholder="~/project/.codex/skills" /></label>
      </div></QDisclosure>
      <p v-if="error" class="ssh-error" role="alert">{{ error }}</p>
    </div>
    <template #footer><QButton type="secondary" @click="$emit('update:modelValue', false)">取消</QButton><QButton type="primary" :disabled="busy || (!selected.length && !(manualName && manualPath))" @click="save">添加目标</QButton></template>
  </QModal>
</template>
<script setup>
import { ref, watch } from 'vue'
import QModal from '../QModal.vue'
import QButton from '../QButton.vue'
import QDisclosure from '../QDisclosure.vue'
import QCheckbox from '../QCheckbox.vue'
import QSelect from '../QSelect.vue'
import ProviderIcon from '../ProviderIcon.vue'
import { discoverTargets, addTarget } from '../../api/remoteSync.js'
const props = defineProps({ modelValue: Boolean, connection: Object })
const emit = defineEmits(['update:modelValue', 'saved'])
const scope = ref('global'), root = ref(''), manualName = ref(''), manualPath = ref('')
const candidates = ref([]), selected = ref([]), discovered = ref(false), busy = ref(false), error = ref('')
let generation = 0
function reset() { generation++; candidates.value = []; selected.value = []; discovered.value = false; error.value = '' }
watch(() => props.modelValue, open => { reset(); if (open) { scope.value = 'global'; root.value = ''; manualName.value = ''; manualPath.value = '' } })
async function discover() {
  const current = ++generation
  busy.value = true; error.value = ''
  try {
    const data = await discoverTargets(props.connection.id, scope.value === 'project' ? root.value : null)
    if (current === generation) { candidates.value = data.targets; discovered.value = true }
  } catch (err) { if (current === generation) error.value = err.message }
  finally { busy.value = false }
}
async function save() {
  if (busy.value) return
  busy.value = true; error.value = ''
  const items = candidates.value.filter(t => selected.value.includes(t.path)).map(t => ({ ...t, name: `${props.connection.name} · ${t.name || t.agentKind}${scope.value === 'project' ? ' · 项目' : ''}` }))
  if (manualName.value && manualPath.value) items.push({ name: manualName.value, path: manualPath.value, scope: scope.value, projectRoot: scope.value === 'project' ? root.value : null })
  const added = []
  try {
    for (const item of items) { added.push(await addTarget({ ...item, connectionId: props.connection.id })); selected.value = selected.value.filter(path => path !== item.path) }
    emit('saved', added); emit('update:modelValue', false)
  } catch (err) { error.value = err.message; emit('saved', added) }
  finally { busy.value = false }
}
</script>
