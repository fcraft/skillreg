<template>
  <div class="qqx-tabs">
    <div ref="navRef" class="qqx-tabs__nav">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :ref="(el) => setTabRef(tab.key, el)"
        :class="['qqx-tabs__item', { 'qqx-tabs__item--active': modelValue === tab.key }]"
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
  display: flex;
  gap: var(--qqx-space-xl);
  border-bottom: 1px solid var(--qqx-border-color);
  margin-bottom: var(--qqx-space-xl);
  position: relative;
}

.qqx-tabs__item {
  position: relative;
  padding: var(--qqx-space-sm) 0;
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-regular);
  color: var(--qqx-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: inherit;
  transition: color 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.qqx-tabs__item:not(.qqx-tabs__item--active):hover {
  color: var(--qqx-text-primary);
}

.qqx-tabs__item--active {
  color: var(--qqx-text-primary);
  font-weight: var(--qqx-font-semibold);
}

.qqx-tabs__indicator {
  position: absolute;
  bottom: -1px;
  height: 2px;
  background: var(--qqx-brand);
  border-radius: 1px;
  transition: left 0.15s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.qqx-tabs__content {
  /* Slide-up animation applied via key + class */
}
</style>
