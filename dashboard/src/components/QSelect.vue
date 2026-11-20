<template>
  <div class="q-select">
    <label v-if="label" :for="id" class="q-select__label">{{ label }}</label>
    <button :id="id" ref="trigger" type="button" role="combobox" class="q-select__trigger"
      :disabled="disabled" :aria-label="label || placeholder" aria-haspopup="listbox"
      :aria-expanded="open" :aria-controls="open ? listId : undefined"
      :aria-activedescendant="open && active >= 0 ? listId + '-' + active : undefined"
      @click="open ? close() : show()" @keydown="keydown" @blur="close">
      <span :class="{ 'q-select__placeholder': !selected }">{{ selected?.label || placeholder }}</span>
      <ChevronDown :size="16" :class="{ 'q-select__chevron-open': open }" />
    </button>
    <Teleport to="body">
      <Transition name="q-select-menu">
        <div v-if="open" :id="listId" ref="menu" role="listbox" :aria-label="label || placeholder"
          class="q-select__menu" :style="menuStyle" @mousedown.prevent>
          <div v-for="(option, index) in options" :id="listId + '-' + index" :key="option.value" role="option"
            class="q-select__option" :class="{ 'is-active': active === index }"
            :aria-selected="option.value === modelValue" :aria-disabled="option.disabled || undefined"
            @pointermove="!option.disabled && (active = index)" @click="choose(index)">
            <span>{{ option.label }}</span><Check v-if="option.value === modelValue" :size="16" />
          </div>
          <p v-if="!options.length" class="q-select__empty">暂无选项</p>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
<script setup>
import { computed, nextTick, onUnmounted, ref, useId, watch } from 'vue'
import { Check, ChevronDown } from 'lucide-vue-next'
import { positionDropdown } from '../overlays/dropdownPosition.js'
const props = defineProps({
  modelValue: [String, Number], options: { type: Array, default: () => [] },
  label: String, placeholder: { type: String, default: '请选择' }, disabled: Boolean,
})
const emit = defineEmits(['update:modelValue', 'change'])
const id = useId(), listId = id + '-options'
const trigger = ref(null), menu = ref(null), open = ref(false), active = ref(-1), menuStyle = ref({})
const selected = computed(() => props.options.find(option => option.value === props.modelValue))
let query = '', queryTimer
function close() { open.value = false; query = ''; clearTimeout(queryTimer) }
function place() {
  if (!open.value || !trigger.value || !menu.value) return
  const rect = trigger.value.getBoundingClientRect()
  if (!rect.width || !rect.height) { close(); return }
  const width = Math.min(rect.width, innerWidth - 16)
  const maxHeight = Math.max(40, Math.min(280, Math.max(rect.top - 12, innerHeight - rect.bottom - 12)))
  const height = Math.min(menu.value.scrollHeight, maxHeight)
  const point = positionDropdown(rect, { viewportWidth: innerWidth, viewportHeight: innerHeight, menuWidth: width, menuHeight: height })
  menuStyle.value = { left: point.left + 'px', top: point.top + 'px', width: width + 'px', maxHeight: maxHeight + 'px' }
}
function reveal() { nextTick(() => menu.value?.children[active.value]?.scrollIntoView({ block: 'nearest' })) }
function show(last = false) {
  if (props.disabled) return
  active.value = props.options.findIndex(option => option.value === props.modelValue && !option.disabled)
  if (active.value < 0) active.value = last ? props.options.findLastIndex(option => !option.disabled) : props.options.findIndex(option => !option.disabled)
  open.value = true
  nextTick(() => { if (open.value) { place(); nextTick(place); reveal() } })
}
function choose(index) {
  const option = props.options[index]
  if (!option || option.disabled) return
  if (option.value !== props.modelValue) { emit('update:modelValue', option.value); emit('change', option.value) }
  close()
  trigger.value?.focus({ preventScroll: true })
}
function move(direction) {
  for (let offset = 1; offset <= props.options.length; offset++) {
    const index = (active.value + direction * offset + props.options.length) % props.options.length
    if (!props.options[index].disabled) { active.value = index; reveal(); return }
  }
}
function keydown(event) {
  if (event.isComposing || props.disabled) return
  if (event.key === 'Escape' && open.value) { event.preventDefault(); event.stopPropagation(); close(); return }
  if (event.key === 'Tab') { close(); return }
  if (['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(event.key)) {
    event.preventDefault()
    if (!open.value) { show(event.key === 'ArrowUp' || event.key === 'End'); return }
    if (event.key === 'Enter' || event.key === ' ') choose(active.value)
    else if (event.key === 'Home' || event.key === 'End') {
      active.value = event.key === 'Home' ? props.options.findIndex(option => !option.disabled) : props.options.findLastIndex(option => !option.disabled)
      reveal()
    } else move(event.key === 'ArrowDown' ? 1 : -1)
  } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
    if (!open.value) show()
    query += event.key.toLocaleLowerCase()
    clearTimeout(queryTimer); queryTimer = setTimeout(() => { query = '' }, 600)
    const index = props.options.findIndex(option => !option.disabled && option.label.toLocaleLowerCase().startsWith(query))
    if (index >= 0) { active.value = index; reveal() }
  }
}
function outside(event) { if (!trigger.value?.contains(event.target) && !menu.value?.contains(event.target)) close() }
function scroll(event) { if (!menu.value?.contains(event.target)) close() }
watch(open, value => {
  const method = value ? 'addEventListener' : 'removeEventListener'
  document[method]('pointerdown', outside, true)
  document[method]('transitionend', place, true)
  window[method]('resize', place)
  window[method]('scroll', scroll, true)
})
watch(() => [props.disabled, props.options, props.modelValue], close)
onUnmounted(() => {
  clearTimeout(queryTimer)
  document.removeEventListener('pointerdown', outside, true)
  document.removeEventListener('transitionend', place, true)
  window.removeEventListener('resize', place)
  window.removeEventListener('scroll', scroll, true)
})
</script>
<style scoped>
.q-select { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.q-select__label { font-size: var(--sr-text-compact); font-weight: var(--sr-weight-bold); color: var(--sr-text-secondary); }
.q-select__trigger {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  width: 100%; height: var(--sr-control-height-md); padding: 0 12px;
  border: 1px solid transparent; border-radius: var(--sr-radius-sm);
  background: var(--sr-control-bg); color: var(--sr-text-primary);
  font: inherit; font-size: var(--sr-text-body); text-align: left; cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard), box-shadow 140ms var(--sr-ease-standard);
}
.q-select__trigger > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.q-select__trigger svg { flex-shrink: 0; color: var(--sr-text-secondary); transition: transform var(--sr-duration-fast) var(--sr-ease-standard); }
.q-select__trigger:not(:disabled):not([aria-expanded="true"]):hover { background: var(--sr-control-bg-hover); }
.q-select__trigger:focus-visible, .q-select__trigger[aria-expanded="true"] {
  outline: none; background: var(--sr-control-bg-active); box-shadow: var(--sr-control-focus-shadow);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard), box-shadow 180ms var(--sr-ease-standard);
}
.q-select__trigger:disabled { opacity: 0.45; cursor: not-allowed; }
.q-select__placeholder { color: var(--sr-text-tertiary); }
.q-select__chevron-open { transform: rotate(180deg); }
.q-select__menu {
  position: fixed; z-index: var(--z-overlay-top); overflow-y: auto; box-sizing: border-box;
  padding: 5px; border: none; border-radius: var(--sr-radius-md);
  background: var(--sr-glass-bg); backdrop-filter: var(--sr-glass-filter); -webkit-backdrop-filter: var(--sr-glass-filter);
  box-shadow: var(--sr-shadow-md); color: var(--sr-text-primary);
  font-family: var(--sr-font-sans); font-size: var(--sr-text-body);
}
.q-select__option {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  min-height: 32px; padding: 5px 8px; border-radius: var(--sr-radius-menu-item);
  cursor: pointer; box-sizing: border-box;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}
.q-select__option span { min-width: 0; overflow-wrap: anywhere; }
.q-select__option svg { flex-shrink: 0; }
.q-select__option[aria-selected="true"] { background: var(--sr-action-bg-selected); color: var(--sr-accent); font-weight: var(--sr-weight-semibold); }
.q-select__option.is-active:not([aria-selected="true"]):not([aria-disabled="true"]) { background: var(--sr-bg-hover); }
.q-select__option[aria-disabled="true"] { opacity: 0.4; cursor: not-allowed; }
.q-select__empty { padding: 8px 10px; color: var(--sr-text-tertiary); font-size: var(--sr-text-compact); }
.q-select-menu-enter-active, .q-select-menu-leave-active { transition: opacity var(--sr-duration-fast) var(--sr-ease-standard); }
.q-select-menu-enter-from, .q-select-menu-leave-to { opacity: 0; }
@media (pointer: coarse) {
  .q-select__trigger { min-height: 40px; }
  .q-select__option { min-height: 44px; }
}
@media (prefers-reduced-motion: reduce) {
  .q-select__trigger, .q-select__trigger svg, .q-select-menu-enter-active, .q-select-menu-leave-active { transition: none; }
}
</style>
