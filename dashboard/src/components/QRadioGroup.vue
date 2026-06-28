<template>
  <div class="q-radio-group">
    <QRadio
      v-for="opt in options"
      :key="opt.value"
      :model-value="modelValue"
      :value="opt.value"
      :label="opt.label"
      :disabled="disabled || opt.disabled"
      :size="size"
      @update:model-value="(val) => emit('update:modelValue', val)"
    />
  </div>
</template>

<script setup>
import QRadio from './QRadio.vue'

defineProps({
  modelValue: {
    type: [String, Number],
    default: undefined,
  },
  options: {
    type: Array,
    required: true,
    // Array of { label: String, value: String|Number, disabled?: Boolean }
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
</script>

<style scoped>
.q-radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
