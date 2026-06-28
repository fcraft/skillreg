<template>
  <label
    :class="[
      'q-radio',
      `q-radio--${size}`,
      { 'q-radio--checked': checked, 'q-radio--disabled': disabled },
    ]"
  >
    <input
      type="radio"
      class="q-radio__native"
      :checked="checked"
      :disabled="disabled"
      :value="value"
      @change="onChange"
    />
    <span class="q-radio__visual">
      <span v-if="checked" class="q-radio__dot"></span>
    </span>
    <span v-if="label || $slots.default" class="q-radio__label">
      <slot>{{ label }}</slot>
    </span>
  </label>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number, Boolean],
    default: undefined,
  },
  value: {
    type: [String, Number, Boolean],
    required: true,
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

const emit = defineEmits(['update:modelValue'])

const checked = computed(() => props.modelValue === props.value)

function onChange(event) {
  if (event.target.checked) {
    emit('update:modelValue', props.value)
  }
}
</script>

<script>
export default {
  inheritAttrs: false,
}
</script>

<style scoped>
.q-radio {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-family: var(--qqx-font-family);
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-primary);
  user-select: none;
}

.q-radio--sm {
  font-size: var(--qqx-font-size-small);
}

.q-radio--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Hide native radio; visual replacement handles all states */
.q-radio__native {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.q-radio__visual {
  position: relative;
  display: grid;
  place-content: center;
  flex-shrink: 0;
  border: 2px solid var(--qqx-border-color);
  background: var(--qqx-bg-card);
  border-radius: 50%;
  transition: border-color var(--qqx-transition),
              background var(--qqx-transition),
              box-shadow var(--qqx-transition);
}

/* Size: md (18px) */
.q-radio--md .q-radio__visual {
  width: 18px;
  height: 18px;
}

/* Size: sm (14px) */
.q-radio--sm .q-radio__visual {
  width: 14px;
  height: 14px;
}

/* Hover — skip when disabled or checked */
.q-radio:not(.q-radio--disabled):not(.q-radio--checked):hover .q-radio__visual {
  border-color: var(--qqx-brand);
}

/* Checked */
.q-radio--checked .q-radio__visual {
  border-color: var(--qqx-brand);
}

/* Inner dot */
.q-radio__dot {
  display: block;
  border-radius: 50%;
  background: var(--qqx-brand);
  animation: q-radio-pop 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes q-radio-pop {
  from { transform: scale(0); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.q-radio--md .q-radio__dot {
  width: 6px;
  height: 6px;
}

.q-radio--sm .q-radio__dot {
  width: 4px;
  height: 4px;
}

/* Focus visible */
.q-radio__native:focus-visible + .q-radio__visual {
  outline: 2px solid var(--qqx-brand);
  outline-offset: 2px;
}
</style>
