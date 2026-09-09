<template>
  <div class="q-loading" role="status" aria-live="polite">
    <LoaderCircle class="q-loading__indicator" :size="16" aria-hidden="true" />
    <span><slot>正在加载…</slot></span>
  </div>
</template>
<script setup>
import { LoaderCircle } from 'lucide-vue-next'
</script>
<style scoped>
.q-loading { display: flex; align-items: center; gap: 8px; min-height: 32px; color: var(--qqx-text-secondary); font-size: 13px; }
.q-loading__indicator { flex-shrink: 0; animation: q-loading-spin 800ms linear infinite; }
@keyframes q-loading-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .q-loading__indicator { animation: none; } }
</style>
