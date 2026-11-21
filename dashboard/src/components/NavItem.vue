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
  gap: var(--sr-space-2);
  min-height: var(--sr-control-height-md);
  padding: 0 10px;
  font-size: var(--sr-text-body);
  font-weight: var(--sr-weight-medium);
  color: var(--sr-text-secondary);
  border-radius: var(--sr-radius-sm);
  text-decoration: none;
  transition: color var(--sr-duration-fast) var(--sr-ease-standard),
              background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.nav-item:not(.nav-item--active):hover {
  background: var(--sr-bg-hover);
  color: var(--sr-text-primary);
}

.nav-item--active {
  background: var(--sr-nav-bg-selected);
  color: var(--sr-text-primary);
  font-weight: var(--sr-weight-semibold);
}

.nav-item--active:hover {
  background: var(--sr-nav-bg-selected-hover);
  color: var(--sr-text-primary);
}

.nav-item__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  flex-shrink: 0;
  color: inherit;
}

.nav-item__label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (pointer: coarse) {
  .nav-item {
    min-height: 40px;
  }
}
</style>
