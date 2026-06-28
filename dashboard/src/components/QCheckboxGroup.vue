<template>
  <div class="q-checkbox-group">
    <QCheckbox
      v-for="opt in options"
      :key="opt.value"
      :model-value="modelValue.includes(opt.value)"
      :label="opt.label"
      :disabled="disabled || opt.disabled"
      :size="size"
      @update:model-value="(val) => toggle(opt.value, val)"
    />
  </div>
</template>

<script setup>
import QCheckbox from './QCheckbox.vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
  options: {
    type: Array,
    required: true,
    // Array of { label: String, value: any, disabled?: Boolean }
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

function toggle(optValue, checked) {
  const next = [...props.modelValue]
  if (checked) {
    next.push(optValue)
  } else {
    const idx = next.indexOf(optValue)
    if (idx !== -1) next.splice(idx, 1)
  }
  emit('update:modelValue', next)
}
</script>

<style scoped>
.q-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
