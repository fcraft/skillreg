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
  background: var(--sr-overlay-scrim);
}

/* Single glass layer on reading drawer; inner panes stay transparent */
.drawer-panel {
  width: min(920px, calc(100vw - 32px));
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: var(--sr-radius-xl) 0 0 var(--sr-radius-xl);
  background: var(--sr-glass-reading-bg);
  backdrop-filter: var(--sr-glass-reading-filter);
  -webkit-backdrop-filter: var(--sr-glass-reading-filter);
  box-shadow: var(--sr-shadow-lg);
  overflow: hidden;
  animation: slide-in var(--sr-duration-slow) var(--sr-ease-smooth);
}

.drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sr-space-4);
  padding: var(--sr-space-5) var(--sr-space-5) var(--sr-space-4);
}

.drawer-header h2 {
  margin: 0;
  color: var(--sr-text-primary);
  font-size: var(--sr-text-page-title);
  font-weight: var(--sr-weight-semibold);
  letter-spacing: -0.015em;
}

.drawer-header p {
  margin: var(--sr-space-1) 0 0;
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-compact);
  font-family: var(--sr-font-mono);
}

.close-button {
  min-height: var(--sr-control-height-sm);
  border: none;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-control-bg);
  color: var(--sr-text-primary);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-semibold);
  padding: 0 12px;
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.close-button:hover {
  background: var(--sr-control-bg-hover);
}

.drawer-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: var(--sr-space-3);
  padding: 0 var(--sr-space-5) var(--sr-space-5);
  overflow: hidden;
}

.tree-pane {
  min-width: 0;
  overflow: auto;
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  padding: var(--sr-space-2);
}

.pane-title {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: var(--sr-space-2) var(--sr-space-3);
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-micro);
  font-weight: var(--sr-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.pane-state {
  padding: var(--sr-space-4);
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-card-title);
}

.pane-state.error {
  color: var(--sr-role-rose-ink);
}

@keyframes slide-in {
  from { transform: translateX(16px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@media (max-width: 760px) {
  .drawer-panel {
    width: 100vw;
    border-radius: 0;
  }

  .drawer-header {
    padding: var(--sr-space-4);
  }

  .drawer-body {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(180px, 36%) minmax(0, 1fr);
    padding: 0 var(--sr-space-4) var(--sr-space-4);
  }
}

@media (prefers-reduced-motion: reduce) {
  .drawer-panel { animation: none; }
}
</style>
