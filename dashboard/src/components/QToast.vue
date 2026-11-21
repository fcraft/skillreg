<template>
  <Teleport to="body">
    <Transition name="toast" @after-leave="onAfterLeave">
      <div v-if="visible" :class="['q-toast', `q-toast--${position}`, `q-toast--${tint}`]">
        <div class="q-toast-inner">
          <span class="q-toast-icon">
            <CircleCheck v-if="tint === 'success'" :size="18" />
            <TriangleAlert v-else-if="tint === 'warn'" :size="18" />
            <CircleX v-else-if="tint === 'error'" :size="18" />
            <Info v-else :size="18" />
          </span>
          <span class="q-toast-msg">{{ message }}</span>
          <button v-if="actionLabel" class="q-toast-action" @click="$emit('action')">{{ actionLabel }}</button>
          <button v-if="closable" class="q-toast-close" @click="dismiss">&times;</button>
        </div>
        <div v-if="duration > 0" class="q-toast-bar" :style="barStyle"></div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { CircleCheck, TriangleAlert, CircleX, Info } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  message: { type: String, default: '' },
  tint: { type: String, default: 'brand', validator: v => ['brand', 'success', 'warn', 'error'].includes(v) },
  position: { type: String, default: 'bottom', validator: v => ['top', 'bottom'].includes(v) },
  duration: { type: Number, default: 3500 },
  actionLabel: { type: String, default: '' },
  closable: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'action'])
const visible = ref(false)
let timer = null
let barTimer = null
const barProgress = ref(100)

const barStyle = computed(() => ({
  background: TINT_COLORS[props.tint],
  transform: `scaleX(${barProgress.value / 100})`,
}))

const TINT_COLORS = {
  brand: 'var(--sr-accent)',
  success: 'var(--sr-role-sage-solid)',
  warn: 'var(--sr-role-amber-solid)',
  error: 'var(--sr-role-rose-solid)',
}

function dismiss() {
  visible.value = false
}

function onAfterLeave() {
  emit('update:modelValue', false)
}

function startTimer() {
  clearTimeout(timer)
  clearInterval(barTimer)
  if (props.duration > 0) {
    barProgress.value = 100
    const interval = 30
    barTimer = setInterval(() => {
      barProgress.value -= (interval / props.duration) * 100
      if (barProgress.value <= 0) barProgress.value = 0
    }, interval)
    timer = setTimeout(() => { dismiss() }, props.duration)
  }
}

watch(() => props.modelValue, (val) => {
  if (val) {
    visible.value = true
    startTimer()
  }
}, { immediate: true })

watch(() => props.message, (val) => {
  // If already visible and message changes, restart timer
  if (visible.value && val) startTimer()
})

onUnmounted(() => {
  clearTimeout(timer)
  clearInterval(barTimer)
})
</script>

<style scoped>
.q-toast {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  z-index: var(--sr-z-toast);
  min-width: 280px;
  max-width: 520px;
  border-radius: var(--sr-radius-lg);
  box-shadow: var(--sr-shadow-md);
  overflow: hidden;
  background: var(--sr-glass-bg);
  backdrop-filter: var(--sr-glass-filter);
  -webkit-backdrop-filter: var(--sr-glass-filter);
}

.q-toast--bottom { bottom: calc(24px + var(--sr-safe-area-bottom)); }
.q-toast--top { top: calc(24px + var(--sr-safe-area-top)); }

.q-toast-inner {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: transparent;
}

.q-toast-icon {
  display: flex;
  flex-shrink: 0;
}

.q-toast--brand .q-toast-icon { color: var(--sr-accent); }
.q-toast--success .q-toast-icon { color: var(--sr-role-sage-ink); }
.q-toast--warn .q-toast-icon { color: var(--sr-role-amber-ink); }
.q-toast--error .q-toast-icon { color: var(--sr-role-rose-ink); }

.q-toast-msg {
  flex: 1;
  font-size: var(--sr-text-card-title);
  font-weight: var(--sr-weight-medium);
  color: var(--sr-text-primary);
  line-height: 1.45;
}

.q-toast-action {
  flex-shrink: 0;
  min-height: 28px;
  padding: 0 10px;
  border: none;
  border-radius: var(--sr-radius-sm);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-semibold);
  cursor: pointer;
  font-family: inherit;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.q-toast--brand .q-toast-action { background: var(--sr-accent); color: var(--sr-text-inverse); }
.q-toast--success .q-toast-action { background: var(--sr-role-sage-solid); color: var(--sr-role-on-solid); }
.q-toast--warn .q-toast-action { background: var(--sr-role-amber-solid); color: var(--sr-role-on-solid); }
.q-toast--error .q-toast-action { background: var(--sr-role-rose-solid); color: var(--sr-role-on-solid); }

.q-toast-close {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--sr-text-tertiary);
  font-size: 16px;
  cursor: pointer;
  border-radius: var(--sr-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
}

.q-toast-close:hover { background: var(--sr-action-bg-hover); color: var(--sr-text-primary); }

.q-toast-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  transform-origin: left;
  transition: transform 30ms linear;
}

.toast-enter-active { animation: toast-in var(--sr-duration-normal) var(--sr-ease-smooth); }
.toast-leave-active { animation: toast-in 140ms var(--sr-ease-standard) reverse; }

@keyframes toast-in {
  from { opacity: 0; transform: translateX(-50%) translateY(10px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active, .toast-leave-active { animation: none; }
}
</style>
