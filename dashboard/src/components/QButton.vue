<template>
  <button
    :class="[
      'qqx-btn',
      'q-press',
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
  gap: var(--sr-space-2);
  border: none;
  font-weight: var(--sr-weight-semibold);
  white-space: nowrap;
  user-select: none;
  border-radius: var(--sr-radius-sm);
  line-height: 1;
}

.qqx-btn:focus-visible {
  outline: 2px solid var(--sr-accent);
  outline-offset: 2px;
}

/* Workbench Glass Control Heights: 32px (sm) / 38px (md) */
.qqx-btn--small {
  min-height: var(--sr-control-height-sm);
  padding: 0 10px;
  font-size: var(--sr-text-compact);
  border-radius: var(--sr-radius-sm);
}

.qqx-btn--medium {
  min-height: var(--sr-control-height-md);
  padding: 0 14px;
  font-size: var(--sr-text-body);
  border-radius: var(--sr-radius-sm);
}

.qqx-btn--large {
  min-height: var(--sr-control-height-md);
  padding: 0 16px;
  font-size: var(--sr-text-body);
  border-radius: var(--sr-radius-sm);
}

.qqx-btn--pill {
  border-radius: var(--sr-radius-pill);
}

/* Types — Zero decorative borders & shadows */
.qqx-btn--primary {
  background: var(--sr-accent);
  color: var(--sr-text-inverse);
}

.qqx-btn--primary:hover:not(:disabled) {
  background: var(--sr-accent-strong);
}

.qqx-btn--secondary {
  background: var(--sr-control-bg);
  color: var(--sr-text-primary);
}

.qqx-btn--secondary:hover:not(:disabled) {
  background: var(--sr-control-bg-hover);
}

.qqx-btn--ghost {
  background: transparent;
  color: var(--sr-text-primary);
}

.qqx-btn--ghost:hover:not(:disabled) {
  background: var(--sr-action-bg-hover);
}

.qqx-btn--ghost:active:not(:disabled) {
  background: var(--sr-action-bg-pressed);
}

.qqx-btn--text {
  background: transparent;
  color: var(--sr-accent);
  padding-left: 6px;
  padding-right: 6px;
}

.qqx-btn--text:hover:not(:disabled) {
  color: var(--sr-accent-strong);
  background: var(--sr-action-bg-hover);
}

.qqx-btn--danger {
  background: var(--sr-role-rose-solid);
  color: var(--sr-role-on-solid);
}

.qqx-btn--danger:hover:not(:disabled) {
  background: var(--sr-role-rose-hover);
}

/* Ghost tint variants */
.qqx-btn--ghost.qqx-btn--tint-brand {
  color: var(--sr-accent);
}

.qqx-btn--ghost.qqx-btn--tint-brand:hover:not(:disabled) {
  color: var(--sr-accent-strong);
  background: var(--sr-action-bg-hover);
}

.qqx-btn--ghost.qqx-btn--tint-danger {
  color: var(--sr-role-rose-ink);
}

.qqx-btn--ghost.qqx-btn--tint-danger:hover:not(:disabled) {
  background: var(--sr-role-rose-surface);
}

/* Secondary semantic tint variants (AA >= 4.5:1 in both Light & Dark) */
.qqx-btn--secondary.qqx-btn--tint-brand {
  color: var(--sr-role-blue-ink);
  background: var(--sr-role-blue-surface);
}

.qqx-btn--secondary.qqx-btn--tint-brand:hover:not(:disabled) {
  background: color-mix(in srgb, var(--sr-accent) 16%, var(--sr-role-blue-surface));
}

.qqx-btn--secondary.qqx-btn--tint-danger {
  color: var(--sr-role-rose-ink);
  background: var(--sr-role-rose-surface);
}

.qqx-btn--secondary.qqx-btn--tint-danger:hover:not(:disabled) {
  background: color-mix(in srgb, var(--sr-role-rose-solid) 16%, var(--sr-role-rose-surface));
}

/* Muted ghost — secondary text at rest, accent only on hover */
.qqx-btn--ghost.qqx-btn--muted {
  color: var(--sr-text-secondary);
}

.qqx-btn--ghost.qqx-btn--muted:hover:not(:disabled) {
  color: var(--sr-text-primary);
}

.qqx-btn--ghost.qqx-btn--muted.qqx-btn--tint-brand:hover:not(:disabled) {
  color: var(--sr-accent);
}

.qqx-btn--ghost.qqx-btn--muted.qqx-btn--tint-danger:hover:not(:disabled) {
  color: var(--sr-role-rose-ink);
}

.qqx-btn--disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (pointer: coarse) {
  .qqx-btn--small,
  .qqx-btn--medium,
  .qqx-btn--large {
    min-height: 40px;
  }
}
</style>
