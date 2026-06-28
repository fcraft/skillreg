<template>
  <Teleport to="body">
    <Transition name="qqx-modal">
      <div v-if="modelValue" class="qqx-modal-overlay" @click.self="handleOverlayClick">
        <div class="qqx-modal" :style="{ width: width }">
          <div class="qqx-modal__header">
            <slot name="title">
              <h2 class="qqx-modal__title">{{ title }}</h2>
            </slot>
            <button class="qqx-modal__close" @click="close">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>
          <div class="qqx-modal__body">
            <slot />
          </div>
          <div v-if="$slots.footer" class="qqx-modal__footer">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  width: {
    type: String,
    default: '480px'
  },
  closeOnOverlay: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue'])

function close() {
  emit('update:modelValue', false)
}

function handleOverlayClick() {
  if (props.closeOnOverlay) {
    close()
  }
}
</script>

<style scoped>
.qqx-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-overlay-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--qqx-bg-backdrop);
  backdrop-filter: blur(4px);
}

.qqx-modal {
  background: var(--qqx-modal-bg);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-lg);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--qqx-modal-shadow);
}

.qqx-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--qqx-space-xl) var(--qqx-space-xl) var(--qqx-space-lg);
}

.qqx-modal__title {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
}

.qqx-modal__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--qqx-text-secondary);
  border-radius: var(--qqx-radius-xs);
  transition: all var(--qqx-transition);
}

.qqx-modal__close:hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-primary);
}

.qqx-modal__body {
  padding: 0 var(--qqx-space-xl) var(--qqx-space-xl);
  overflow-y: auto;
  flex: 1;
}

.qqx-modal__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-lg) var(--qqx-space-xl);
  border-top: 1px solid var(--qqx-border-color);
}

/* Transition */
.qqx-modal-enter-active,
.qqx-modal-leave-active {
  transition: opacity 0.2s ease;
}

.qqx-modal-enter-active .qqx-modal,
.qqx-modal-leave-active .qqx-modal {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.qqx-modal-enter-from,
.qqx-modal-leave-to {
  opacity: 0;
}

.qqx-modal-enter-from .qqx-modal,
.qqx-modal-leave-to .qqx-modal {
  transform: scale(0.95);
  opacity: 0;
}

/* ========== Responsive: Mobile ========== */
@media (max-width: 767px) {
  .qqx-modal {
    width: calc(100% - 32px) !important;
    max-width: none;
  }
}
</style>
