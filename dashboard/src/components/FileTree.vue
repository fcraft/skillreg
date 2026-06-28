<template>
  <ul class="file-tree" :class="{ root: depth === 0 }">
    <li v-for="node in nodes" :key="node.path || node.name" class="tree-item">
      <button
        class="tree-row"
        :class="{ active: node.type === 'file' && node.path === selectedPath }"
        type="button"
        :style="{ paddingLeft: `${depth * 12 + 8}px` }"
        @click="handleClick(node)"
      >
        <span class="node-icon">{{ node.type === 'dir' ? (isOpen(node) ? '▾' : '▸') : '·' }}</span>
        <span class="node-name">{{ node.name }}</span>
      </button>
      <FileTree
        v-if="node.type === 'dir' && isOpen(node) && node.children?.length"
        :nodes="node.children"
        :selected-path="selectedPath"
        :depth="depth + 1"
        @select="$emit('select', $event)"
      />
    </li>
  </ul>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  nodes: { type: Array, required: true },
  selectedPath: { type: String, default: '' },
  depth: { type: Number, default: 0 }
})

const emit = defineEmits(['select'])
const openDirs = ref(new Set(['']))

function isOpen(node) {
  return openDirs.value.has(node.path)
}

function handleClick(node) {
  if (node.type === 'dir') {
    const next = new Set(openDirs.value)
    if (next.has(node.path)) next.delete(node.path)
    else next.add(node.path)
    openDirs.value = next
    return
  }
  emit('select', node.path)
}
</script>

<style scoped>
.file-tree {
  list-style: none;
  margin: 0;
  padding: 0;
}

.file-tree.root {
  padding: var(--qqx-space-sm);
}

.tree-row {
  width: 100%;
  min-height: 30px;
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  border: 0;
  border-radius: var(--qqx-radius-xs);
  background: transparent;
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  text-align: left;
  cursor: pointer;
  transition: background var(--qqx-transition), color var(--qqx-transition);
}

.tree-row:not(.active):hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-primary);
}

.tree-row.active {
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
}

.node-icon {
  width: 12px;
  color: var(--qqx-text-tertiary);
  flex-shrink: 0;
}

.node-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
