<template>
  <Teleport to="body">
    <Transition name="qqx-modal">
      <div v-if="modelValue" class="qqx-modal-overlay" @click.self="handleOverlayClick">
        <div ref="panel" class="qqx-modal" :style="{ width: width }" role="dialog" aria-modal="true" :aria-label="title || undefined" tabindex="-1">
          <div class="qqx-modal__header">
            <slot name="title">
              <h2 class="qqx-modal__title">{{ title }}</h2>
            </slot>
            <button class="qqx-modal__close q-press" aria-label="关闭弹窗" @click="close">
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
import { ref } from 'vue'
import { useModalFocus } from '../composables/useModalFocus.js'
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
const panel = ref(null)
useModalFocus(() => props.modelValue, panel, close)

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
  z-index: var(--sr-z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--sr-space-4);
  background: var(--sr-overlay-scrim);
}

.qqx-modal {
  outline: none;
  background: var(--sr-overlay-bg);
  border: none;
  border-radius: var(--sr-radius-lg);
  max-width: calc(100vw - 32px);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--sr-shadow-lg);
}

.qqx-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sr-space-3);
  padding: var(--sr-dialog-padding) var(--sr-dialog-padding) var(--sr-space-3);
}

.qqx-modal__title {
  font-size: var(--sr-text-dialog-title);
  font-weight: var(--sr-weight-semibold);
  line-height: 1.4;
  color: var(--sr-text-primary);
}

.qqx-modal__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--sr-control-height-sm);
  height: var(--sr-control-height-sm);
  border: none;
  background: transparent;
  color: var(--sr-text-secondary);
  border-radius: var(--sr-radius-sm);
  flex-shrink: 0;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
}

.qqx-modal__close:hover {
  background: var(--sr-action-bg-hover);
  color: var(--sr-text-primary);
}

.qqx-modal__body {
  margin-inline: calc(var(--sr-dialog-padding) - 3px);
  padding: 3px 3px var(--sr-dialog-padding);
  overflow-y: auto;
  flex: 1;
}

.qqx-modal__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sr-space-2);
  padding: var(--sr-space-3) var(--sr-dialog-padding) var(--sr-dialog-padding);
}

/* Workbench Dialog Entrance (300ms / 180ms) */
.qqx-modal-enter-active {
  transition: opacity 260ms var(--sr-ease-smooth);
}

.qqx-modal-leave-active {
  transition: opacity 180ms var(--sr-ease-standard);
}

.qqx-modal-enter-active .qqx-modal {
  transition: transform 280ms var(--sr-ease-smooth), opacity 220ms var(--sr-ease-smooth);
}

.qqx-modal-leave-active .qqx-modal {
  transition: transform 180ms var(--sr-ease-standard), opacity 160ms var(--sr-ease-standard);
}

.qqx-modal-enter-from,
.qqx-modal-leave-to {
  opacity: 0;
}

.qqx-modal-enter-from .qqx-modal,
.qqx-modal-leave-to .qqx-modal {
  transform: translateY(12px) scale(0.96);
  opacity: 0;
}

@media (max-width: 760px) {
  .qqx-modal-overlay {
    padding: var(--sr-space-3);
  }

  .qqx-modal {
    width: calc(100vw - 24px) !important;
    max-width: none;
  }
}

@media (pointer: coarse) {
  .qqx-modal__close {
    width: 40px;
    height: 40px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .qqx-modal-enter-active,
  .qqx-modal-leave-active,
  .qqx-modal-enter-active .qqx-modal,
  .qqx-modal-leave-active .qqx-modal {
    transition: opacity 80ms linear;
  }

  .qqx-modal-enter-from .qqx-modal,
  .qqx-modal-leave-to .qqx-modal {
    transform: none;
  }
}
</style>
