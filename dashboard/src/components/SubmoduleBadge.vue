<template>
  <span v-if="submodulePath" class="submodule-badge" @click.stop="navigate" title="查看所属仓库">
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
    </svg>
    {{ displayPath }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  submodulePath: { type: String, default: null },
})

const router = useRouter()

const displayPath = computed(() => {
  return props.submodulePath.replace(/^repos\//, '')
})

function navigate() {
  router.push({ name: 'repos', query: { submodule: props.submodulePath } })
}
</script>

<style scoped>
.submodule-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 0 4px;
  border-radius: var(--qqx-radius-xs);
  background: transparent;
  color: var(--qqx-text-tertiary);
  cursor: pointer;
  transition: background var(--qqx-transition),
              color var(--qqx-transition);
}
.submodule-badge:hover {
  background: var(--qqx-bg-elevated);
  color: var(--qqx-brand);
}
</style>
