<template>
  <div :class="['qqx-card', { 'qqx-card--empty': empty, 'qqx-card--hoverable': hoverable }]">
    <div v-if="title || $slots.header" class="qqx-card__header">
      <h3 v-if="title" class="qqx-card__title">{{ title }}</h3>
      <slot name="header" />
    </div>
    <div class="qqx-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="qqx-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: ''
  },
  empty: {
    type: Boolean,
    default: false
  },
  hoverable: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.qqx-card {
  background: var(--qqx-bg-card);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-lg);
  overflow: hidden;
  transition: all var(--qqx-transition);
}

.qqx-card--hoverable:hover {
  border-color: var(--qqx-brand);
}

.qqx-card--empty {
  background: var(--qqx-bg-overlay);
  border: 1px dashed var(--qqx-border-dashed);
  border-radius: var(--qqx-radius-sm);
  box-shadow: none;
}

.qqx-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--qqx-space-lg) var(--qqx-space-xl);
  border-bottom: 1px solid var(--qqx-border-color);
}

.qqx-card__title {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
}

.qqx-card__body {
  padding: var(--qqx-space-xl);
}

.qqx-card__footer {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-md) var(--qqx-space-xl);
  border-top: 1px solid var(--qqx-border-color);
}

/* ========== Responsive: Mobile ========== */
@media (max-width: 767px) {
  .qqx-card {
    min-width: 0;
    word-break: break-word;
  }

  .qqx-card__body {
    padding: var(--qqx-space-lg);
  }

  .qqx-card__header {
    padding: var(--qqx-space-md) var(--qqx-space-lg);
  }

  .qqx-card__footer {
    padding: var(--qqx-space-sm) var(--qqx-space-lg);
  }
}
</style>
