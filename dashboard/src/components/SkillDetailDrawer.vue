<template>
  <Teleport to="body">
    <div v-if="open" class="drawer-backdrop" @click.self="$emit('close')">
      <aside class="drawer-panel" role="dialog" aria-modal="true" :aria-label="`${skill?.name || ''} 文件详情`">
        <header class="drawer-header">
          <div>
            <h2>{{ skill?.name }}</h2>
            <p>{{ skill?.path }}</p>
          </div>
          <button class="close-button" type="button" @click="$emit('close')">关闭</button>
        </header>

        <div class="drawer-body">
          <section class="tree-pane">
            <div class="pane-title">目录结构</div>
            <div v-if="loading" class="pane-state">加载中...</div>
            <div v-else-if="error" class="pane-state error">{{ error }}</div>
            <FileTree
              v-else-if="tree"
              :nodes="tree.children || []"
              :selected-path="selectedPath"
              @select="selectedPath = $event"
            />
            <div v-else class="pane-state">暂无目录数据</div>
          </section>

          <FilePreview :skill="skill" :path="selectedPath" />
        </div>
      </aside>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import FileTree from './FileTree.vue'
import FilePreview from './FilePreview.vue'

const props = defineProps({
  skill: { type: Object, default: null },
  open: { type: Boolean, default: false }
})

defineEmits(['close'])

const loading = ref(false)
const error = ref('')
const tree = ref(null)
const selectedPath = ref('')

watch(() => [props.open, props.skill?.id], loadTree, { immediate: true })

async function loadTree() {
  tree.value = null
  selectedPath.value = ''
  error.value = ''
  if (!props.open || !props.skill?.id) return

  loading.value = true
  try {
    const res = await fetch(`/api/skill-tree?skill=${encodeURIComponent(props.skill.id)}`)
    const payload = await res.json()
    if (!res.ok) throw new Error(payload.error || '目录加载失败')
    tree.value = payload.tree || payload
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.drawer-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-overlay-top);
  display: flex;
  justify-content: flex-end;
  background: var(--qqx-bg-backdrop);
}

.drawer-panel {
  width: min(920px, calc(100vw - 32px));
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--qqx-bg-card);
  box-shadow: var(--qqx-shadow-dropdown);
  animation: slide-in var(--qqx-transition);
}

.drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--qqx-space-lg);
  padding: var(--qqx-space-xl);
  border-bottom: 1px solid var(--qqx-border-color);
}

.drawer-header h2 {
  margin: 0;
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
}

.drawer-header p {
  margin: var(--qqx-space-xs) 0 0;
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
}

.close-button {
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-surface);
  color: var(--qqx-text-secondary);
  padding: 6px 14px;
  cursor: pointer;
  transition: all var(--qqx-transition);
}

.close-button:hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-primary);
}

.drawer-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  overflow: hidden;
}

.tree-pane {
  min-width: 0;
  overflow: auto;
  background: var(--qqx-bg-surface);
}

.pane-title {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  border-bottom: 1px solid var(--qqx-border-color);
  background: var(--qqx-bg-surface);
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
}

.pane-state {
  padding: var(--qqx-space-lg);
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-caption);
}

.pane-state.error {
  color: var(--qqx-brand);
}

@keyframes slide-in {
  from { transform: translateX(16px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@media (max-width: 768px) {
  .drawer-panel {
    width: 100vw;
  }

  .drawer-body {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(180px, 36%) minmax(0, 1fr);
  }
}
</style>
