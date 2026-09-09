<template>
  <QModal :model-value="Boolean(preview)" title="确认同步内容" width="760px" @update:model-value="!$event && $emit('close')">
    <div v-if="preview" class="ssh-form">
      <p class="ssh-muted">来源：{{ preview.workspace }}</p>
      <section v-for="item in preview.targets" :key="item.target.id" class="ssh-preview-target">
        <h3>{{ item.target.name }}</h3><code class="ssh-path">{{ item.target.path }}</code>
        <p v-if="item.error" class="ssh-error">{{ item.error.message }} · 此目标无法执行</p>
        <QDisclosure v-for="skill in item.skills" :id="`diff-${item.target.id}-${skill.name}`" :key="skill.name" class="ssh-file-diff">
          <template #title><span class="ssh-row"><span>{{ skill.name }}</span><span :class="`ssh-status-${skill.status}`">{{ statusLabel(skill.status) }}</span></span></template>
          <div v-for="file in skill.files.filter(f => f.change !== 'unchanged')" :key="file.path" class="ssh-diff-row"><span>{{ changeLabel(file.change) }}</span><code>{{ file.path }}</code></div>
          <p v-if="skill.status === 'synced'" class="ssh-muted">内容一致，将跳过写入</p>
        </QDisclosure>
      </section>
      <QCheckbox v-if="preview.requiresOverwrite" v-model="force" label="确认覆盖以上有差异的 Skill 内容，包括目标中额外的文件" />
      <p v-if="error" class="ssh-error" role="alert">{{ error }}</p>
    </div>
    <template #footer><QButton type="secondary" @click="$emit('close')">取消</QButton><QButton type="primary" :disabled="busy || !canExecute || (preview?.requiresOverwrite && !force)" @click="$emit('execute', force)">{{ busy ? '启动中…' : '执行同步' }}</QButton></template>
  </QModal>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import QModal from '../QModal.vue'
import QCheckbox from '../QCheckbox.vue'
import QButton from '../QButton.vue'
import QDisclosure from '../QDisclosure.vue'
import { statusLabel, changeLabel } from '../../sources/remoteSyncState.js'
const props = defineProps({ preview: Object, busy: Boolean, error: String })
defineEmits(['close', 'execute'])
const force = ref(false)
watch(() => props.preview?.id, () => { force.value = false })
const canExecute = computed(() => props.preview?.targets.some(t => !t.error && t.skills.length))
</script>
