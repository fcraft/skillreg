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
  position: relative;
  isolation: isolate;
  display: flex;
  height: 100vh;
  background: var(--sr-bg-rail);
  overflow: hidden;
}

/* Single subtle Workbench ambient wash behind transparent rail/header */
.qqx-layout::before {
  content: '';
  position: fixed;
  inset: -12%;
  z-index: -1;
  pointer-events: none;
  background:
    radial-gradient(48% 42% at 10% 8%, var(--sr-ambient-1), transparent 72%),
    radial-gradient(42% 38% at 88% 12%, var(--sr-ambient-2), transparent 70%),
    radial-gradient(50% 45% at 50% 96%, var(--sr-ambient-3), transparent 74%);
  filter: blur(42px);
}

.qqx-layout__sidebar {
  width: var(--sr-sidebar-width);
  background: var(--sr-sidebar-bg);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  padding: 0 var(--sr-space-2);
  transition: background-color var(--sr-duration-normal) var(--sr-ease-standard);
}

.qqx-layout__logo {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  height: var(--sr-topbar-height);
  padding: 0 var(--sr-space-2);
  flex-shrink: 0;
}

.qqx-layout__logo-text {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background: var(--sr-accent);
  color: var(--sr-text-inverse);
  font-weight: var(--sr-weight-semibold);
  font-size: var(--sr-text-card-title);
  border-radius: var(--sr-radius-sm);
  flex-shrink: 0;
}

.qqx-layout__logo-label {
  font-size: var(--sr-text-body);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
  letter-spacing: -0.01em;
}

.qqx-layout__nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--sr-space-2) 0;
}

.qqx-layout__user {
  padding: var(--sr-space-3) var(--sr-space-2) calc(var(--sr-space-3) + var(--sr-safe-area-bottom));
}

.qqx-layout__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.qqx-layout__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sr-space-3);
  height: var(--sr-topbar-height);
  padding: 0 var(--sr-space-4) 0 var(--sr-space-2);
  background: transparent;
  flex-shrink: 0;
}

.qqx-layout__content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin: 0 var(--sr-space-2) var(--sr-space-2) 0;
  padding: var(--sr-space-4) var(--sr-gutter) var(--sr-space-5);
  border-radius: var(--sr-radius-xl);
  background: var(--sr-canvas-bg);
  transition: background-color var(--sr-duration-normal) var(--sr-ease-standard);
}

/* Hamburger button — hidden on desktop */
.qqx-layout__hamburger {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  width: var(--sr-control-height-sm);
  height: var(--sr-control-height-sm);
  padding: 8px;
  background: transparent;
  border: none;
  border-radius: var(--sr-radius-sm);
  cursor: pointer;
  flex-shrink: 0;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.qqx-layout__hamburger:hover {
  background: var(--sr-action-bg-hover);
}

.qqx-layout__hamburger span {
  display: block;
  width: 100%;
  height: 1.75px;
  background: var(--sr-text-primary);
  border-radius: var(--sr-radius-pill);
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
    left: calc(var(--sr-sidebar-width) * -1 - 24px);
    top: 0;
    bottom: 0;
    z-index: var(--sr-z-drawer);
    background: var(--sr-glass-reading-bg);
    backdrop-filter: var(--sr-glass-reading-filter);
    -webkit-backdrop-filter: var(--sr-glass-reading-filter);
    border-radius: 0 var(--sr-radius-xl) var(--sr-radius-xl) 0;
    box-shadow: var(--sr-shadow-lg);
    transition: left var(--sr-duration-slow) var(--sr-ease-standard),
                background-color var(--sr-duration-normal) var(--sr-ease-standard);
  }

  .qqx-layout__sidebar--open {
    left: 0;
  }

  .qqx-layout__backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: calc(var(--sr-z-drawer) - 1);
    background: var(--sr-overlay-scrim);
    animation: qqx-fade-in var(--sr-duration-normal) var(--sr-ease-standard);
  }

  .qqx-layout__content {
    margin: 0 var(--sr-space-2) var(--sr-space-2) var(--sr-space-2);
  }
}

/* ========== Narrow Mobile: <= 760px (Zero outer margin & radius) ========== */
@media (max-width: 760px) {
  .qqx-layout__header {
    padding: 0 var(--sr-gutter);
  }

  .qqx-layout__content {
    margin: 0;
    border-radius: 0;
    padding: var(--sr-space-3) var(--sr-gutter) calc(var(--sr-space-5) + var(--sr-safe-area-bottom));
  }

  .qqx-layout__sidebar {
    width: 100vw;
    left: -100vw;
    padding: var(--sr-space-4);
    border-radius: 0;
    box-shadow: none;
    background: var(--sr-bg-panel);
    backdrop-filter: none;
  }

  .qqx-layout__backdrop {
    display: none;
  }
}

@media (prefers-reduced-transparency: reduce), (prefers-contrast: more) {
  .qqx-layout::before {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .qqx-layout__sidebar {
    transition: none;
  }
}

@media (pointer: coarse) {
  .qqx-layout__hamburger {
    width: 40px;
    height: 40px;
  }
}

@keyframes qqx-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
