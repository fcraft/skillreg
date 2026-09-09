<template>
  <section class="q-disclosure" :class="{ 'q-disclosure--open': expanded }">
    <button type="button" class="q-disclosure__trigger q-press" :aria-expanded="expanded" :aria-controls="id" @click="toggle">
      <ChevronRight :size="14" class="q-disclosure__chevron" aria-hidden="true" />
      <span class="q-disclosure__title"><slot name="title">{{ title }}</slot></span>
    </button>
    <div :id="id" class="q-disclosure__region" :aria-hidden="!expanded" :inert="!expanded">
      <div class="q-disclosure__content"><slot v-if="rendered" /></div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { ChevronRight } from 'lucide-vue-next'
defineProps({ id: { type: String, required: true }, title: String })
const emit = defineEmits(['toggle'])
const expanded = ref(false), rendered = ref(false)
function toggle() {
  expanded.value = !expanded.value
  if (expanded.value) rendered.value = true
  emit('toggle', expanded.value)
}
</script>

<style scoped>
.q-disclosure__trigger { display: flex; gap: 8px; align-items: center; width: 100%; padding: 8px 0; border: 0; border-radius: var(--qqx-radius-xs); background: transparent; color: var(--qqx-text-primary); text-align: left; cursor: pointer; font: inherit; --q-press-scale: 0.99; }
.q-disclosure__trigger:not([aria-expanded="true"]):hover { background: var(--qqx-bg-hover); }
.q-disclosure__title { flex: 1; min-width: 0; }
.q-disclosure__chevron { flex-shrink: 0; transition: transform 180ms cubic-bezier(0.2, 0, 0, 1); }
.q-disclosure--open > .q-disclosure__trigger .q-disclosure__chevron { transform: rotate(90deg); }
.q-disclosure__region { display: grid; grid-template-rows: 0fr; opacity: 0; transition: grid-template-rows 180ms cubic-bezier(0.2, 0, 0, 1), opacity 120ms ease-out; }
.q-disclosure--open > .q-disclosure__region { grid-template-rows: 1fr; opacity: 1; }
.q-disclosure__content { min-height: 0; overflow: hidden; }
@media (prefers-reduced-motion: reduce) {
  .q-disclosure__region, .q-disclosure__chevron { transition: none; }
}
</style>
