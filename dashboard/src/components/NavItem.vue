<template>
  <router-link :to="to" class="nav-item" active-class="nav-item--active">
    <span class="nav-item__icon">
      <component :is="icon" :size="18" />
    </span>
    <span class="nav-item__label">{{ label }}</span>
  </router-link>
</template>

<script setup>
defineProps({
  to: { type: [String, Object], required: true },
  icon: { type: [Object, Function], required: true },
  label: { type: String, required: true },
})
</script>

<style scoped>
.nav-item {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-secondary);
  border-radius: var(--qqx-radius-xs);
  text-decoration: none;
  transition: color var(--qqx-transition),
              background-color var(--qqx-transition);
}

/* Only hover on non-active items — QQX spec §6.4 */
.nav-item:not(.nav-item--active):hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-primary);
}

.nav-item--active {
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
  font-weight: var(--qqx-font-semibold);
}

.nav-item__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  flex-shrink: 0;
}

.nav-item__label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
