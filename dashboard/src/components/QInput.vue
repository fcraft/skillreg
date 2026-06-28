<template>
  <div class="qqx-input-wrapper">
    <label v-if="label" class="qqx-input__label">{{ label }}</label>
    <input
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      class="qqx-input"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'text'
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:modelValue'])
</script>

<style scoped>
.qqx-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-sm);
}

.qqx-input__label {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.qqx-input {
  width: 100%;
  height: 40px;
  /* Border is a constant 2px (unfocused uses the muted border color, focused
     uses brand). Keeping the width fixed avoids layout/padding shifts during
     the focus transition that made the text jitter. padding compensates so
     the 2px border fits inside the 40px box (border-box). */
  padding: 7px 11px;
  background: var(--qqx-input-bg);
  border: 2px solid var(--qqx-input-border);
  border-radius: var(--qqx-radius-xs);
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-label);
  outline: none;
  transition: border-color var(--qqx-transition), background var(--qqx-transition);
}

.qqx-input::placeholder {
  color: var(--qqx-text-secondary);
}

/* Focus (flat): only color changes — border → brand, faint 0.05 brand tint.
   No outer ring, no inset shadow, no width change → no jitter. */
.qqx-input:focus {
  border-color: var(--qqx-brand);
  box-shadow: none;
  background: color-mix(in srgb, var(--qqx-brand-light) 50%, transparent);
}

.qqx-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
