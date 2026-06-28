<template>
  <button
    :class="[
      'qqx-btn',
      `qqx-btn--${type}`,
      `qqx-btn--${size}`,
      {
        'qqx-btn--disabled': disabled,
        'qqx-btn--pill': pill,
        'qqx-btn--muted': muted,
        'qqx-btn--tint-brand': tint === 'brand',
        'qqx-btn--tint-danger': tint === 'danger',
      },
    ]"
    :disabled="disabled"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'secondary',
    validator: (v) => ['primary', 'secondary', 'ghost', 'text', 'danger'].includes(v)
  },
  size: {
    type: String,
    default: 'medium',
    validator: (v) => ['small', 'medium', 'large'].includes(v)
  },
  pill: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  muted: {
    type: Boolean,
    default: false
  },
  tint: {
    type: String,
    default: null,
    validator: (v) => v === null || ['brand', 'danger'].includes(v)
  }
})

defineEmits(['click'])
</script>

<style scoped>
.qqx-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  font-weight: var(--qqx-font-medium);
  transition: color 0.15s cubic-bezier(0.4, 0, 0.2, 1),
              background-color 0.15s cubic-bezier(0.4, 0, 0.2, 1),
              border-color 0.15s cubic-bezier(0.4, 0, 0.2, 1),
              transform 150ms ease-out;
  white-space: nowrap;
  user-select: none;
}

/* Active press feedback — press: FastOutSlowIn 100ms, release: ease-out 150ms */
.qqx-btn:active:not(:disabled) {
  transform: scale(0.97);
  transition-duration: 100ms;
  transition-timing-function: cubic-bezier(0.4, 0.0, 0.2, 1.0);
}

/* Focus ring */
.qqx-btn:focus-visible {
  outline: none;
  box-shadow: var(--qqx-shadow-focus);
}

/* Sizes */
.qqx-btn--small {
  padding: 4px 10px;
  font-size: var(--qqx-font-size-small);
  border-radius: var(--qqx-radius-xs);
}

.qqx-btn--medium {
  padding: 8px 16px;
  font-size: var(--qqx-font-size-label);
  border-radius: var(--qqx-radius-xs);
}

.qqx-btn--large {
  padding: 10px 20px;
  font-size: var(--qqx-font-size-body);
  border-radius: var(--qqx-radius-md);
}

/* Pill shape */
.qqx-btn--pill {
  border-radius: var(--qqx-radius-full);
}

/* Types */
.qqx-btn--primary {
  background: var(--qqx-brand-fill-bg);
  color: #ffffff;
  box-shadow: var(--qqx-shadow-button);
}

.qqx-btn--primary:hover:not(:disabled) {
  background: var(--qqx-brand-fill-hover-bg);
}

.qqx-btn--secondary {
  background: var(--qqx-bg-subtle);
  color: var(--qqx-text-primary);
}

.qqx-btn--secondary:hover:not(:disabled) {
  background: var(--qqx-bg-hover);
}

.qqx-btn--ghost {
  background: transparent;
  color: var(--qqx-text-primary);
}

.qqx-btn--ghost:hover:not(:disabled) {
  background: var(--qqx-bg-hover);
}

.qqx-btn--text {
  background: transparent;
  color: var(--qqx-brand);
  padding-left: 0;
  padding-right: 0;
}

.qqx-btn--text:hover:not(:disabled) {
  color: var(--qqx-brand-hover);
}

.qqx-btn--danger {
  background: #e53e3e;
  color: #ffffff;
}

.qqx-btn--danger:hover:not(:disabled) {
  background: #f56565;
}

/* Tint variants */

/* Ghost tint — color accent only, transparent background */
.qqx-btn--ghost.qqx-btn--tint-brand {
  color: var(--qqx-brand);
}

.qqx-btn--ghost.qqx-btn--tint-brand:hover:not(:disabled) {
  color: var(--qqx-brand-hover);
}

.qqx-btn--ghost.qqx-btn--tint-danger {
  color: #e53e3e;
}

.qqx-btn--ghost.qqx-btn--tint-danger:hover:not(:disabled) {
  color: #f56565;
}

/* Secondary tint — subtle background + color accent */
.qqx-btn--secondary.qqx-btn--tint-brand {
  color: var(--qqx-brand);
  background: #e6f4ff;
}

.qqx-btn--secondary.qqx-btn--tint-brand:hover:not(:disabled) {
  color: var(--qqx-brand-hover);
  background: #d4ebfc;
}

.qqx-btn--secondary.qqx-btn--tint-danger {
  color: #e53e3e;
  background: #fef0f0;
}

.qqx-btn--secondary.qqx-btn--tint-danger:hover:not(:disabled) {
  color: #f56565;
  background: #fde2e2;
}

/* Dark mode tint overrides */
[data-theme="dark"] .qqx-btn--secondary.qqx-btn--tint-brand {
  background: #0d1f33;
}

[data-theme="dark"] .qqx-btn--secondary.qqx-btn--tint-brand:hover:not(:disabled) {
  background: #162d45;
}

[data-theme="dark"] .qqx-btn--secondary.qqx-btn--tint-danger {
  background: #2d1010;
}

[data-theme="dark"] .qqx-btn--secondary.qqx-btn--tint-danger:hover:not(:disabled) {
  background: #3d1818;
}

/* Muted ghost — secondary text at rest, tint color only on hover */
.qqx-btn--ghost.qqx-btn--muted {
  color: var(--qqx-text-secondary);
}

.qqx-btn--ghost.qqx-btn--muted:hover:not(:disabled) {
  color: var(--qqx-text-primary);
}

.qqx-btn--ghost.qqx-btn--muted.qqx-btn--tint-brand:hover:not(:disabled) {
  color: var(--qqx-brand);
}

.qqx-btn--ghost.qqx-btn--muted.qqx-btn--tint-danger:hover:not(:disabled) {
  color: #e53e3e;
}

/* Disabled */
.qqx-btn--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
