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
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  overflow: hidden;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sr-space-4);
  padding: var(--sr-space-3) var(--sr-space-4);
}

.file-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--sr-text-primary);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-semibold);
  font-family: var(--sr-font-mono);
}

.file-meta {
  flex-shrink: 0;
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-meta);
}

pre {
  flex: 1;
  margin: 0;
  padding: var(--sr-space-4);
  overflow: auto;
  background: transparent;
  color: var(--sr-text-primary);
  font-size: var(--sr-text-compact);
  line-height: 1.65;
}

code {
  font-family: var(--sr-font-mono);
  white-space: pre-wrap;
  word-break: break-word;
}

.empty-state {
  flex: 1;
  display: grid;
  place-items: center;
  padding: var(--sr-space-5);
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-card-title);
  text-align: center;
}

.empty-state.error {
  color: var(--sr-role-rose-ink);
}
</style>
