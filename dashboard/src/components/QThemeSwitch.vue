<template>
  <div class="qqx-theme-switch">
    <button
      v-for="option in options"
      :key="option.value"
      :class="['qqx-theme-switch__item', { 'qqx-theme-switch__item--active': current === option.value }]"
      @click="setTheme(option.value)"
    >
      <component :is="option.icon" :size="14" class="qqx-theme-switch__icon" />
      <span class="qqx-theme-switch__label">{{ option.label }}</span>
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Sun, Moon, Monitor } from 'lucide-vue-next'

const options = [
  { value: 'light', label: '浅色', icon: Sun },
  { value: 'dark', label: '深色', icon: Moon },
  { value: 'system', label: '系统', icon: Monitor }
]

const current = ref('light')

function applyTheme(theme) {
  document.documentElement.dataset.palette = 'mist'
  document.documentElement.dataset.style = 'glass'
  if (theme === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    document.documentElement.dataset.theme = prefersDark ? 'dark' : 'light'
  } else {
    document.documentElement.dataset.theme = theme
  }
}

function setTheme(theme) {
  current.value = theme
  localStorage.setItem('qqx-theme', theme)
  applyTheme(theme)
}

onMounted(() => {
  const saved = localStorage.getItem('qqx-theme') || 'light'
  current.value = saved
  applyTheme(saved)

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (current.value === 'system') {
      applyTheme('system')
    }
  })
})
</script>

<style scoped>
.qqx-theme-switch {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  height: var(--sr-control-height-sm);
  padding: 3px;
  border: none;
  border-radius: var(--sr-radius-md);
  background: var(--sr-control-bg);
}

.qqx-theme-switch__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 26px;
  padding: 0 10px;
  border: none;
  background: transparent;
  color: var(--sr-text-secondary);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-medium);
  border-radius: var(--sr-radius-sm);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
  white-space: nowrap;
}

.qqx-theme-switch__item:not(.qqx-theme-switch__item--active):hover {
  color: var(--sr-text-primary);
}

.qqx-theme-switch__item--active {
  background: var(--sr-bg-floating);
  color: var(--sr-text-primary);
  font-weight: var(--sr-weight-semibold);
  box-shadow: var(--sr-shadow-sm);
}

.qqx-theme-switch__icon {
  display: flex;
  align-items: center;
}

.qqx-theme-switch__label {
  font-size: var(--sr-text-compact);
}

@media (max-width: 760px) {
  .qqx-theme-switch__label {
    display: none;
  }

  .qqx-theme-switch__item {
    padding: 0 8px;
  }
}

@media (pointer: coarse) {
  .qqx-theme-switch {
    height: auto;
  }

  .qqx-theme-switch__item {
    min-height: 36px;
  }
}
</style>
