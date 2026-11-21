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
  background: var(--sr-content-bg);
  border: none;
  border-radius: var(--sr-radius-lg);
  overflow: hidden;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.qqx-card--hoverable:hover {
  background: var(--sr-content-bg-hover);
}

.qqx-card--empty {
  background: var(--sr-fill-quaternary);
  border: none;
  border-radius: var(--sr-radius-md);
  box-shadow: none;
}

.qqx-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sr-space-4) var(--sr-space-5) var(--sr-space-2);
}

.qqx-card__title {
  font-size: var(--sr-text-card-title);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
}

.qqx-card__body {
  padding: var(--sr-space-4) var(--sr-space-5) var(--sr-space-5);
}

.qqx-card__footer {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  padding: var(--sr-space-3) var(--sr-space-5) var(--sr-space-4);
}

@media (max-width: 760px) {
  .qqx-card {
    min-width: 0;
    word-break: break-word;
  }

  .qqx-card__body {
    padding: var(--sr-space-4);
  }

  .qqx-card__header {
    padding: var(--sr-space-3) var(--sr-space-4) var(--sr-space-2);
  }

  .qqx-card__footer {
    padding: var(--sr-space-3) var(--sr-space-4);
  }
}
</style>
