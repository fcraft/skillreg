<template>
  <label
    :class="[
      'q-checkbox',
      `q-checkbox--${size}`,
      { 'q-checkbox--checked': modelValue, 'q-checkbox--disabled': disabled },
    ]"
  >
    <input
      type="checkbox"
      class="q-checkbox__native"
      :checked="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.checked)"
    />
    <span class="q-checkbox__visual">
      <svg v-if="modelValue" class="q-checkbox__check" viewBox="0 0 12 12" fill="none">
        <path d="M2.5 6L5 8.5L9.5 3.5" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </span>
    <span v-if="label || $slots.default" class="q-checkbox__label">
      <slot>{{ label }}</slot>
    </span>
  </label>
</template>

<script setup>
defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  label: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md'].includes(v),
  },
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
.q-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-family: var(--qqx-font-family);
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-primary);
  user-select: none;
}

.q-checkbox--sm {
  font-size: var(--qqx-font-size-small);
}

.q-checkbox--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Hide native checkbox; visual replacement handles all states */
.q-checkbox__native {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.q-checkbox__visual {
  position: relative;
  display: grid;
  place-content: center;
  flex-shrink: 0;
  border: 2px solid var(--qqx-border-color);
  background: var(--qqx-bg-card);
  transition: border-color var(--qqx-transition),
              background var(--qqx-transition),
              box-shadow var(--qqx-transition);
}

/* Size: md (18px) */
.q-checkbox--md .q-checkbox__visual {
  width: 18px;
  height: 18px;
  border-radius: 6px;
}

/* Size: sm (14px) */
.q-checkbox--sm .q-checkbox__visual {
  width: 14px;
  height: 14px;
  border-radius: 4px;
}

/* Hover — skip when disabled or checked */
.q-checkbox:not(.q-checkbox--disabled):not(.q-checkbox--checked):hover .q-checkbox__visual {
  border-color: var(--qqx-brand);
}

/* Checked */
.q-checkbox--checked .q-checkbox__visual {
  background: var(--qqx-brand);
  border-color: var(--qqx-brand);
}

.q-checkbox--sm .q-checkbox__check {
  width: 9px;
  height: 9px;
}

.q-checkbox--md .q-checkbox__check {
  width: 12px;
  height: 12px;
}

/* Focus visible */
.q-checkbox__native:focus-visible + .q-checkbox__visual {
  outline: 2px solid var(--qqx-brand);
  outline-offset: 2px;
}

/* Checkmark micro-animation: scale-in on check */
.q-checkbox__check {
  display: block;
  animation: q-check-pop 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes q-check-pop {
  from { transform: scale(0); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
</style>
