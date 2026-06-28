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
  brand: 'var(--qqx-brand)',
  success: '#22c55e',
  warn: '#eab308',
  error: '#ef4444',
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
  z-index: var(--z-notification);
  min-width: 280px;
  max-width: 520px;
  border-radius: var(--qqx-radius-md);
  box-shadow: 0px 8px 32px rgba(0, 0, 0, 0.12), 0px 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.q-toast--bottom { bottom: 28px; }
.q-toast--top { top: 28px; }

.q-toast-inner {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
}

/* Frosted glass backgrounds */
.q-toast--brand .q-toast-inner {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid rgba(0, 153, 255, 0.18);
}

.q-toast--success .q-toast-inner {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.q-toast--warn .q-toast-inner {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid rgba(234, 179, 8, 0.25);
}

.q-toast--error .q-toast-inner {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

/* Dark mode frosted glass */
[data-theme="dark"] .q-toast--brand .q-toast-inner,
[data-theme="dark"] .q-toast--success .q-toast-inner,
[data-theme="dark"] .q-toast--warn .q-toast-inner,
[data-theme="dark"] .q-toast--error .q-toast-inner {
  background: rgba(23, 23, 23, 0.88);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
}

[data-theme="dark"] .q-toast--brand .q-toast-inner { border-color: rgba(51, 173, 255, 0.25); }
[data-theme="dark"] .q-toast--success .q-toast-inner { border-color: rgba(34, 197, 94, 0.25); }
[data-theme="dark"] .q-toast--warn .q-toast-inner { border-color: rgba(234, 179, 8, 0.3); }
[data-theme="dark"] .q-toast--error .q-toast-inner { border-color: rgba(239, 68, 68, 0.3); }

/* Icon */
.q-toast-icon {
  display: flex;
  flex-shrink: 0;
}

.q-toast--brand .q-toast-icon { color: var(--qqx-brand); }
.q-toast--success .q-toast-icon { color: #22c55e; }
.q-toast--warn .q-toast-icon { color: #eab308; }
.q-toast--error .q-toast-icon { color: #ef4444; }

[data-theme="dark"] .q-toast--success .q-toast-icon { color: #4ade80; }
[data-theme="dark"] .q-toast--warn .q-toast-icon { color: #facc15; }

/* Message */
.q-toast-msg {
  flex: 1;
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-primary);
  line-height: 1.4;
}

/* Action button */
.q-toast-action {
  flex-shrink: 0;
  padding: 4px 10px;
  border: none;
  border-radius: var(--qqx-radius-xs);
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
  cursor: pointer;
  font-family: inherit;
  transition: opacity 0.15s;
}

.q-toast--brand .q-toast-action { background: var(--qqx-brand-fill-bg); color: #fff; }
.q-toast--success .q-toast-action { background: #22c55e; color: #fff; }
.q-toast--warn .q-toast-action { background: #eab308; color: #1a1a1a; }
.q-toast--error .q-toast-action { background: #ef4444; color: #fff; }

.q-toast-action:hover { opacity: 0.85; }

/* Close */
.q-toast-close {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  color: var(--qqx-text-tertiary);
  font-size: 16px;
  cursor: pointer;
  border-radius: var(--qqx-radius-xs);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}

.q-toast-close:hover { background: var(--qqx-bg-hover); color: var(--qqx-text-primary); }

/* Progress bar */
.q-toast-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  transform-origin: left;
  transition: transform 30ms linear;
}

/* Transitions */
.toast-enter-active { animation: toast-in 0.3s ease-out; }
.toast-leave-active { animation: toast-in 0.2s ease-in reverse; }

@keyframes toast-in {
  from { opacity: 0; transform: translateX(-50%) translateY(12px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}
</style>
