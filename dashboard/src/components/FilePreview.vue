<template>
  <div class="file-preview">
    <div v-if="!path" class="empty-state">选择左侧文件进行预览</div>
    <div v-else-if="loading" class="empty-state">加载中...</div>
    <div v-else-if="error" class="empty-state error">{{ error }}</div>
    <div v-else-if="file?.binary" class="empty-state">二进制文件不可预览，大小 {{ formatSize(file.size) }}</div>
    <template v-else-if="file">
      <div class="preview-header">
        <span class="file-name">{{ path }}</span>
        <span class="file-meta">{{ file.language }} · {{ formatSize(file.size) }}</span>
      </div>
      <pre><code>{{ file.content }}</code></pre>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  skill: { type: Object, required: true },
  path: { type: String, default: '' }
})

const loading = ref(false)
const error = ref('')
const file = ref(null)

watch(() => [props.skill?.id, props.path], loadFile, { immediate: true })

async function loadFile() {
  file.value = null
  error.value = ''
  if (!props.skill?.id || !props.path) return

  loading.value = true
  try {
    const res = await fetch(`/api/skill-file?skill=${encodeURIComponent(props.skill.id)}&path=${encodeURIComponent(props.path)}`)
    const payload = await res.json()
    if (!res.ok) throw new Error(payload.error || '文件预览失败')
    file.value = payload
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function formatSize(size = 0) {
  if (size < 1024) return `${size} B`
  return `${(size / 1024).toFixed(1)} KB`
}
</script>

<style scoped>
.file-preview {
  min-width: 0;
  min-height: 320px;
  height: 100%;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--qqx-border-color);
  background: var(--qqx-bg-card);
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--qqx-space-lg);
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  border-bottom: 1px solid var(--qqx-border-color);
}

.file-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
}

.file-meta {
  flex-shrink: 0;
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
}

pre {
  flex: 1;
  margin: 0;
  padding: var(--qqx-space-lg);
  overflow: auto;
  background: var(--qqx-bg-elevated);
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-small);
  line-height: 1.6;
}

code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  white-space: pre-wrap;
  word-break: break-word;
}

.empty-state {
  flex: 1;
  display: grid;
  place-items: center;
  padding: var(--qqx-space-xl);
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-caption);
  text-align: center;
}

.empty-state.error {
  color: var(--qqx-brand);
}

@media (max-width: 768px) {
  .file-preview {
    border-left: 0;
    border-top: 1px solid var(--qqx-border-color);
  }
}
</style>
