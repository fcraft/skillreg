<template>
  <QModal :model-value="Boolean(run)" title="同步执行记录" width="720px" @update:model-value="!$event && $emit('close')">
    <div v-if="run" class="ssh-form" aria-live="polite">
      <div class="ssh-row"><strong>{{ statusLabel(run.state) }}</strong><span>{{ run.progress.completed }} / {{ run.progress.total }} 项</span></div>
      <progress v-if="isActiveRun(run)" :value="run.progress.completed" :max="run.progress.total || 1" />
      <p class="ssh-muted">{{ run.createdAt }}<template v-if="isActiveRun(run)"> · {{ run.currentSkill || '准备中' }}</template></p><code class="ssh-path">{{ run.id }}</code><p class="ssh-muted">来源：{{ run.workspace }}</p>
      <p v-if="run.error" class="ssh-error">{{ run.error.message }}</p>
      <section v-for="result in run.results" :key="result.target.id" class="ssh-preview-target">
        <div class="ssh-row"><strong class="ssh-provider-label"><ProviderIcon :target="result.target" :size="16" /><span>{{ result.target.name }}</span></strong><span>{{ statusLabel(result.state) }}</span></div><code class="ssh-path">{{ result.target.path }}</code>
        <p v-if="result.error" class="ssh-error">{{ result.error.message }}</p>
        <div v-for="skill in result.skills" :key="skill.name" class="ssh-run-skill">
          <div class="ssh-row"><span>{{ skill.name }}</span><span>{{ statusLabel(skill.state) }}{{ skill.changed === false ? ' · 内容一致' : '' }}</span></div>
          <p v-if="skill.error" class="ssh-error">{{ skill.error.message }}</p>
        </div>
      </section>
      <p v-if="run.cancelRequested && isActiveRun(run)" class="ssh-muted">当前 Skill 完成后停止后续安装</p><p v-if="error" class="ssh-error" role="alert">{{ error }}</p>
    </div>
    <template #footer>
      <QButton v-if="isActiveRun(run)" type="secondary" :disabled="busy || run.cancelRequested" @click="$emit('cancel')">停止后续同步</QButton>
      <QButton v-else-if="run && run.state !== 'succeeded'" type="secondary" :disabled="busy" @click="$emit('retry')">重新预览失败目标</QButton>
      <QButton type="primary" @click="$emit('close')">关闭</QButton>
    </template>
  </QModal>
</template>
<script setup>
import QModal from '../QModal.vue'
import QButton from '../QButton.vue'
import ProviderIcon from '../ProviderIcon.vue'
import { isActiveRun, statusLabel } from '../../sources/remoteSyncState.js'
defineProps({ run: Object, busy: Boolean, error: String })
defineEmits(['close', 'retry', 'cancel'])
</script>
