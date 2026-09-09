<template>
  <QModal :model-value="modelValue" title="连接与目录设置" width="680px" @update:model-value="$emit('update:modelValue', $event)">
    <div v-if="connection" class="ssh-form">
      <div><strong>{{ connection.name }}</strong><p class="ssh-muted">{{ connection.host }} · {{ statusLabel(connection.status) }}</p></div>
      <div class="ssh-actions"><QButton type="secondary" :disabled="busy" @click="$emit('check')">检查连接</QButton><QButton type="ghost" @click="$emit('edit')">编辑连接</QButton><QButton type="ghost" :disabled="busy || targets.length > 0" @click="$emit('remove', 'connection', connection)">移除连接</QButton></div>
      <p v-if="connection.error" class="ssh-error" role="alert">{{ connection.error }}</p>
      <p v-if="connection.status === 'host-key-untrusted'" class="ssh-muted">请先在本机终端确认该主机指纹并建立 SSH 信任，再重新检查</p>
      <div class="ssh-row"><h3>安装目录</h3><QButton type="secondary" size="small" @click="$emit('addTarget')">添加目标</QButton></div>
      <div v-for="target in targets" :key="target.id" class="ssh-target-row"><div><strong>{{ target.name }}</strong><code class="ssh-path">{{ target.path }}</code><p class="ssh-muted">{{ observedSummary(observationFor(target.id)) }}</p></div><QButton type="ghost" size="small" :disabled="busy" @click="$emit('remove', 'target', target)">移除</QButton></div>
      <p v-if="!targets.length" class="ssh-muted">发现全局 Agent 目录，或指定项目内的安装目标</p>
      <p v-if="error" class="ssh-error" role="alert">{{ error }}</p>
    </div>
    <template #footer><QButton type="ghost" @click="$emit('addConnection')">添加连接</QButton><QButton type="primary" @click="$emit('update:modelValue', false)">完成</QButton></template>
  </QModal>
</template>
<script setup>
import QModal from '../QModal.vue'
import QButton from '../QButton.vue'
import { observedSummary, statusLabel } from '../../sources/remoteSyncState.js'
defineProps({ modelValue: Boolean, connection: Object, targets: Array, observationFor: Function, busy: Boolean, error: String })
defineEmits(['update:modelValue', 'check', 'edit', 'remove', 'addTarget', 'addConnection'])
</script>
