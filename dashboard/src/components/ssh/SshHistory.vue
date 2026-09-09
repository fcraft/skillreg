<template>
  <QModal :model-value="modelValue" title="执行记录" width="760px" @update:model-value="$emit('update:modelValue', $event)">
    <div class="ssh-form">
      <div class="ssh-row"><span class="ssh-muted">关闭记录不会停止正在执行的同步</span><QButton type="ghost" size="small" @click="$emit('refresh')">刷新记录</QButton></div>
      <p v-if="error" class="ssh-error" role="alert">{{ error }}</p>
      <p v-if="!runs.length" class="ssh-muted">暂无执行记录</p>
      <button v-for="run in runs" :key="run.id" class="ssh-history-row q-press" @click="$emit('open', run)"><span>{{ run.createdAt }}</span><span>{{ run.results.map(result => result.target.name).join('、') }}</span><strong>{{ statusLabel(run.state) }}</strong></button>
    </div>
    <template #footer><QButton type="primary" @click="$emit('update:modelValue', false)">关闭</QButton></template>
  </QModal>
</template>
<script setup>
import QButton from '../QButton.vue'
import QModal from '../QModal.vue'
import { statusLabel } from '../../sources/remoteSyncState.js'
defineProps({ modelValue: Boolean, runs: Array, error: String })
defineEmits(['update:modelValue', 'refresh', 'open'])
</script>
