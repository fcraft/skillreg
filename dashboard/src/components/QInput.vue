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
  gap: 6px;
}

.qqx-input__label {
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-bold);
  color: var(--sr-text-secondary);
}

.qqx-input {
  width: 100%;
  height: var(--sr-control-height-md);
  padding: 0 12px;
  background: var(--sr-control-bg);
  border: 1px solid transparent;
  border-radius: var(--sr-radius-sm);
  color: var(--sr-text-primary);
  font-size: var(--sr-text-body);
  font-family: inherit;
  outline: none;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              box-shadow 140ms var(--sr-ease-standard);
}

.qqx-input::placeholder {
  color: var(--sr-text-tertiary);
}

.qqx-input:hover:not(:focus):not(:disabled) {
  background: var(--sr-control-bg-hover);
}

.qqx-input:focus {
  background: var(--sr-control-bg-active);
  box-shadow: var(--sr-control-focus-shadow);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              box-shadow 180ms var(--sr-ease-standard);
}

.qqx-input[aria-invalid="true"] {
  border-color: var(--sr-danger);
  background: var(--sr-control-bg-danger);
}

.qqx-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
