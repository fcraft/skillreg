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
  display: flex;
  gap: 2px;
  background: var(--qqx-bg-elevated);
  border-radius: var(--qqx-radius-full);
  padding: 3px;
  border: 1px solid var(--qqx-border-color);
}

.qqx-theme-switch__item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: none;
  background: transparent;
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  border-radius: var(--qqx-radius-full);
  transition: all var(--qqx-transition);
  white-space: nowrap;
}

.qqx-theme-switch__item:hover {
  color: var(--qqx-text-primary);
}

.qqx-theme-switch__item--active {
  background: var(--qqx-bg-card);
  color: var(--qqx-text-primary);
  font-weight: var(--qqx-font-medium);
  box-shadow: var(--qqx-shadow-button);
}

.qqx-theme-switch__icon {
  display: flex;
  align-items: center;
}

.qqx-theme-switch__label {
  font-size: var(--qqx-font-size-small);
}

/* ========== Responsive: Mobile ========== */
@media (max-width: 767px) {
  .qqx-theme-switch__label {
    display: none;
  }

  .qqx-theme-switch__item {
    padding: 4px 8px;
  }
}
</style>
