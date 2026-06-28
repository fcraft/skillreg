<template>
  <div class="qqx-layout">
    <div
      v-if="sidebarOpen"
      class="qqx-layout__backdrop"
      @click="sidebarOpen = false"
    ></div>
    <aside :class="['qqx-layout__sidebar', { 'qqx-layout__sidebar--open': sidebarOpen }]">
      <div class="qqx-layout__logo">
        <slot name="logo">
          <span class="qqx-layout__logo-text">S</span>
          <span class="qqx-layout__logo-label">Skills Dashboard</span>
        </slot>
      </div>
      <nav class="qqx-layout__nav">
        <slot name="sidebar" />
      </nav>
      <div class="qqx-layout__user">
        <slot name="user" />
      </div>
    </aside>
    <main class="qqx-layout__main">
      <header v-if="$slots.header" class="qqx-layout__header">
        <button class="qqx-layout__hamburger" @click="sidebarOpen = !sidebarOpen">
          <span></span>
          <span></span>
          <span></span>
        </button>
        <slot name="header" />
      </header>
      <div class="qqx-layout__content">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const sidebarOpen = ref(false)
</script>

<style scoped>
.qqx-layout {
  display: flex;
  height: 100vh;
  background: var(--qqx-bg-base);
}

.qqx-layout__sidebar {
  width: var(--qqx-sidebar-width);
  background: var(--qqx-bg-surface);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--qqx-border-color);
  flex-shrink: 0;
  transition: background-color 0.3s ease;
}

.qqx-layout__logo {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-lg) var(--qqx-space-lg);
}

.qqx-layout__logo-text {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: var(--qqx-brand);
  color: #fff;
  font-weight: var(--qqx-font-semibold);
  font-size: var(--qqx-font-size-label);
  border-radius: var(--qqx-radius-xs);
}

.qqx-layout__logo-label {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.qqx-layout__nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--qqx-space-sm) var(--qqx-space-sm);
}

.qqx-layout__user {
  padding: var(--qqx-space-md);
  border-top: 1px solid var(--qqx-border-color);
}

.qqx-layout__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.qqx-layout__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--qqx-space-md) var(--qqx-space-xl);
  border-bottom: 1px solid var(--qqx-border-color);
  background: var(--qqx-bg-surface);
}

.qqx-layout__content {
  flex: 1;
  overflow-y: auto;
  padding: var(--qqx-space-2xl);
  background: var(--qqx-bg-base);
  transition: background-color 0.3s ease;
}

/* Hamburger button — hidden on desktop */
.qqx-layout__hamburger {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  width: 36px;
  height: 36px;
  padding: 8px;
  background: transparent;
  border: none;
  border-radius: var(--qqx-radius-xs);
  cursor: pointer;
  flex-shrink: 0;
  transition: background-color var(--qqx-transition);
}

.qqx-layout__hamburger:hover {
  background: var(--qqx-bg-hover);
}

.qqx-layout__hamburger span {
  display: block;
  width: 100%;
  height: 2px;
  background: var(--qqx-text-primary);
  border-radius: 1px;
  transition: all var(--qqx-transition);
}

/* Backdrop overlay — hidden on desktop */
.qqx-layout__backdrop {
  display: none;
}

/* ========== Tablet & Mobile: < 1024px ========== */
@media (max-width: 1023px) {
  .qqx-layout__hamburger {
    display: flex;
  }

  .qqx-layout__sidebar {
    position: fixed;
    left: -240px;
    top: 0;
    bottom: 0;
    z-index: var(--z-sticky);
    transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                background-color 0.3s ease;
  }

  .qqx-layout__sidebar--open {
    left: 0;
  }

  .qqx-layout__backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: calc(var(--z-sticky) - 1);
    background: var(--qqx-bg-backdrop);
    backdrop-filter: blur(2px);
    animation: qqx-fade-in 0.2s ease;
  }
}

/* ========== Mobile: < 768px ========== */
@media (max-width: 767px) {
  .qqx-layout__content {
    padding: var(--qqx-space-lg);
  }

  .qqx-layout__header {
    padding: var(--qqx-space-sm) var(--qqx-space-lg);
  }
}

@keyframes qqx-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
