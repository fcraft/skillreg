<template>
  <QModal :model-value="modelValue" title="选择安装目标" width="620px" @update:model-value="$emit('update:modelValue', $event)">
    <div class="ssh-form">
      <p class="ssh-muted">可同时选择当前机器的多个目录，确认后仍需检查并预览</p>
      <QCheckbox v-for="target in targets" :key="target.id" class="ssh-target-choice" :model-value="draft.includes(target.id)" @update:model-value="draft = $event ? [...draft, target.id] : draft.filter(id => id !== target.id)"><span><span class="ssh-provider-label"><ProviderIcon :target="target" :size="16" /><span>{{ target.name }}</span></span><code class="ssh-path">{{ target.path }}</code></span></QCheckbox>
      <p v-if="!targets.length" class="ssh-muted">尚未配置目录，请先在设置中添加目标</p>
    </div>
    <template #footer><QButton type="secondary" @click="$emit('update:modelValue', false)">取消</QButton><QButton type="primary" @click="apply">确认目标</QButton></template>
  </QModal>
</template>
<script setup>
import { ref, watch } from 'vue'
import QModal from '../QModal.vue'
import QButton from '../QButton.vue'
import QCheckbox from '../QCheckbox.vue'
import ProviderIcon from '../ProviderIcon.vue'
const props = defineProps({ modelValue: Boolean, targets: Array, selected: Array })
const emit = defineEmits(['update:modelValue', 'apply'])
const draft = ref([])
watch(() => props.modelValue, open => { if (open) draft.value = [...props.selected] })
function apply() { emit('apply', draft.value.filter(id => props.targets.some(target => target.id === id))); emit('update:modelValue', false) }
</script>
