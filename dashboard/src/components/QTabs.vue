<template>
  <div class="qqx-tabs">
    <div ref="navRef" class="qqx-tabs__nav">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :ref="(el) => setTabRef(tab.key, el)"
        :class="['qqx-tabs__item', 'q-press', { 'qqx-tabs__item--active': modelValue === tab.key }]"
        :aria-pressed="modelValue === tab.key"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
      <div class="qqx-tabs__indicator" :style="indicatorStyle" />
    </div>
    <div :key="modelValue" class="qqx-tabs__content qqx-animate-slide-up">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'

const props = defineProps({
  tabs: {
    type: Array,
    required: true,
  },
  modelValue: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue'])

const navRef = ref(null)
const tabRefs = {}

function setTabRef(key, el) {
  if (el) tabRefs[key] = el
}

const indicatorStyle = ref({ left: '0px', width: '0px' })

function updateIndicator() {
  const nav = navRef.value
  const activeTab = tabRefs[props.modelValue]
  if (!nav || !activeTab) return
  const navRect = nav.getBoundingClientRect()
  const tabRect = activeTab.getBoundingClientRect()
  indicatorStyle.value = {
    left: (tabRect.left - navRect.left) + 'px',
    width: tabRect.width + 'px',
  }
}

function switchTab(key) {
  if (key !== props.modelValue) {
    emit('update:modelValue', key)
  }
}

watch(() => props.modelValue, async () => {
  await nextTick()
  updateIndicator()
})

onMounted(() => {
  nextTick(() => updateIndicator())
})
</script>

<style scoped>
.qqx-tabs__nav {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  border-radius: var(--sr-radius-md);
  background: var(--sr-control-bg);
  margin-bottom: var(--sr-space-4);
  position: relative;
  flex-wrap: wrap;
}

.qqx-tabs__item {
  position: relative;
  min-height: 26px;
  padding: 0 12px;
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-medium);
  color: var(--sr-text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--sr-radius-sm);
  cursor: pointer;
  font-family: inherit;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
}

.qqx-tabs__item:not(.qqx-tabs__item--active):hover {
  color: var(--sr-text-primary);
}

.qqx-tabs__item--active {
  background: var(--sr-action-bg-selected);
  color: var(--sr-text-primary);
  font-weight: var(--sr-weight-semibold);
}

.qqx-tabs__indicator {
  display: none;
}

@media (pointer: coarse) {
  .qqx-tabs__item {
    min-height: 40px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .qqx-tabs__content { animation: none; }
}
</style>
