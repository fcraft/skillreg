<template>
  <Teleport to="body">
    <Transition name="cp">
      <div v-if="isOpen" class="command-panel-backdrop" @mousedown.self="close">
        <div
          ref="panelRef"
          class="command-panel"
          role="dialog"
          aria-modal="true"
          aria-label="全局搜索"
        >
          <div class="command-panel-search">
            <Search :size="20" class="search-icon" />
            <input
              ref="searchInput"
              v-model="query"
              placeholder="搜索 Skill、页面或操作"
              class="search-input"
              role="combobox"
              aria-label="搜索 Skill、页面或操作"
              aria-autocomplete="list"
              aria-expanded="true"
              aria-controls="command-panel-results"
              :aria-activedescendant="activeItemId"
              autocomplete="off"
              spellcheck="false"
            />
          </div>
          <div id="command-panel-results" class="command-panel-results" role="listbox">
            <div
              v-for="section in sections"
              :key="section.name"
              class="command-section"
              role="group"
              :aria-label="section.name"
            >
              <div class="command-section-title" aria-hidden="true">{{ section.name }}</div>
              <div
                v-for="item in section.items"
                :key="item.id"
                :id="optionId(item)"
                :class="['command-item', { active: activeIndex === flatIndex(item) }]"
                role="option"
                :aria-selected="activeIndex === flatIndex(item)"
                @click="execute(item)"
                @mouseenter="activeIndex = flatIndex(item)"
              >
                <component :is="item.icon" :size="16" v-if="item.icon" class="command-item-icon" />
                <div class="command-item-text">
                  <span class="command-item-title">
                    <template v-for="(part, index) in highlightParts(item.title)" :key="index">
                      <mark v-if="part.match" class="command-match">{{ part.text }}</mark>
                      <template v-else>{{ part.text }}</template>
                    </template>
                  </span>
                  <span class="command-item-desc" v-if="item.description">
                    <template v-for="(part, index) in highlightParts(item.description)" :key="index">
                      <mark v-if="part.match" class="command-match">{{ part.text }}</mark>
                      <template v-else>{{ part.text }}</template>
                    </template>
                  </span>
                </div>
                <div class="command-item-meta">
                  <span v-if="hasQuery" class="command-kind">{{ kindLabel(item.section) }}</span>
                  <kbd v-if="item.shortcut" class="command-shortcut">{{ item.shortcut }}</kbd>
                </div>
              </div>
            </div>
            <div v-if="!hasResults" class="command-empty">无匹配结果</div>
          </div>
          <div class="command-panel-footer">
            <span>{{ resultSummary }}</span>
            <div class="command-panel-hints" aria-hidden="true">
              <span><kbd>↑</kbd><kbd>↓</kbd> 选择</span>
              <span><kbd>Enter</kbd> 打开</span>
              <span><kbd>Esc</kbd> 关闭</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Search } from 'lucide-vue-next'
import { useCommands } from '../composables/useCommands.js'

const { searchCommands } = useCommands()

const isOpen = ref(false)
const query = ref('')
const activeIndex = ref(0)
const searchInput = ref(null)
const panelRef = ref(null)
let previouslyFocused = null

const hasQuery = computed(() => Boolean(query.value.trim()))

const sections = computed(() => {
  const cmds = searchCommands(query.value)
  if (hasQuery.value) {
    return cmds.length ? [{ name: '搜索结果', items: cmds }] : []
  }

  const nav = cmds.filter(c => c.section === 'navigation')
  const actions = cmds.filter(c => c.section === 'action')
  const skills = cmds.filter(c => c.section === 'skill')

  const result = []
  if (nav.length) result.push({ name: '页面导航', items: nav })
  if (actions.length) result.push({ name: '快捷操作', items: actions })
  if (skills.length) result.push({ name: 'Skill 定位', items: skills })
  return result
})

const flatItems = computed(() => {
  const flat = []
  for (const section of sections.value) {
    for (const item of section.items) {
      flat.push(item)
    }
  }
  return flat
})

const hasResults = computed(() => flatItems.value.length > 0)
const resultSummary = computed(() => hasQuery.value
  ? `${flatItems.value.length} 个结果`
  : `${flatItems.value.length} 项可用`)

const itemIndexMap = computed(() => {
  const map = {}
  flatItems.value.forEach((item, idx) => {
    map[item.id] = idx
  })
  return map
})

function flatIndex(item) {
  return itemIndexMap.value[item.id] ?? -1
}

function optionId(item) {
  return `command-option-${flatIndex(item)}`
}

const activeItemId = computed(() => {
  const item = flatItems.value[activeIndex.value]
  return item ? optionId(item) : undefined
})

function kindLabel(section) {
  return {
    navigation: '页面',
    action: '操作',
    skill: 'Skill',
  }[section] || section
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&')
}

function highlightParts(value) {
  const text = String(value ?? '')
  if (!hasQuery.value) return [{ text, match: false }]

  const tokens = query.value
    .normalize('NFKC')
    .split(/[\s\-_/\\.:]+/gu)
    .map(token => token.trim())
    .filter(Boolean)
    .sort((left, right) => right.length - left.length)
  if (!tokens.length) return [{ text, match: false }]

  const matches = new Set(tokens.map(token => token.toLocaleLowerCase()))
  const pattern = new RegExp(`(${tokens.map(escapeRegExp).join('|')})`, 'giu')
  return text.split(pattern).filter(Boolean).map(part => ({
    text: part,
    match: matches.has(part.normalize('NFKC').toLocaleLowerCase()),
  }))
}

function open() {
  previouslyFocused = document.activeElement
  isOpen.value = true
}

function close() {
  if (!isOpen.value) return
  isOpen.value = false
  nextTick(() => {
    if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus()
    previouslyFocused = null
  })
}

function execute(item) {
  item.action()
  close()
}

// Watch: reset active index when query changes
watch(query, () => {
  activeIndex.value = 0
})

watch(() => flatItems.value.length, (length) => {
  activeIndex.value = length ? Math.min(activeIndex.value, length - 1) : 0
})

// Watch: auto-focus search input when panel opens
watch(isOpen, (val) => {
  if (val) {
    activeIndex.value = 0
    query.value = ''
    nextTick(() => {
      searchInput.value?.focus()
    })
  }
})

// Watch: scroll active item into view
watch(activeIndex, () => {
  nextTick(() => {
    const activeEl = panelRef.value?.querySelector('.command-item.active')
    activeEl?.scrollIntoView({ block: 'nearest' })
  })
})

function onKeyDown(e) {
  if (e.isComposing) return

  if ((e.ctrlKey || e.metaKey) && e.key.toLocaleLowerCase() === 'k') {
    e.preventDefault()
    if (!isOpen.value) open()
    return
  }

  if (!isOpen.value) return

  if (e.key === 'Escape') {
    e.preventDefault()
    close()
    return
  }

  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    if (e.key === 'ArrowDown') {
      if (flatItems.value.length > 0) {
        activeIndex.value = Math.min(activeIndex.value + 1, flatItems.value.length - 1)
      }
    } else {
      activeIndex.value = Math.max(activeIndex.value - 1, 0)
    }
    return
  }

  if (e.key === 'Enter') {
    const item = flatItems.value[activeIndex.value]
    if (item) {
      e.preventDefault()
      execute(item)
    }
    return
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
})
</script>

<style scoped>
.command-panel-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-command);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 8vh var(--qqx-space-xl) var(--qqx-space-2xl);
  background: var(--qqx-bg-backdrop);
  backdrop-filter: blur(16px) saturate(180%);
}

.command-panel {
  width: 100%;
  max-width: 840px;
  max-height: min(720px, calc(100dvh - 64px));
  display: flex;
  flex-direction: column;
  background: var(--qqx-modal-bg);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-lg);
  box-shadow: var(--qqx-modal-shadow);
  overflow: hidden;
}

.command-panel-search {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  min-height: 64px;
  padding: var(--qqx-space-lg) var(--qqx-space-xl);
  border-bottom: 1px solid var(--qqx-border-color);
  flex-shrink: 0;
}

.search-icon {
  color: var(--qqx-text-tertiary);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--qqx-font-size-body);
  color: var(--qqx-text-primary);
  font-family: var(--qqx-font-family);
}

.search-input::placeholder {
  color: var(--qqx-text-tertiary);
}

.command-panel-results {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: var(--qqx-space-md);
}

.command-section-title {
  position: sticky;
  top: 0;
  z-index: 1;
  font-size: var(--qqx-font-size-tiny);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-quaternary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: var(--qqx-space-md) var(--qqx-space-md) var(--qqx-space-xs);
  background: var(--qqx-modal-bg);
}

.command-item {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  min-height: 58px;
  padding: 10px var(--qqx-space-md);
  border-radius: var(--qqx-radius-xs);
  cursor: pointer;
  transition: background-color var(--qqx-transition);
}

.command-item:not(.active):hover {
  background: var(--qqx-bg-subtle);
}

.command-item.active {
  background: var(--qqx-brand-light);
}

.command-item-icon {
  color: var(--qqx-text-secondary);
  flex-shrink: 0;
}

.command-item.active .command-item-icon {
  color: var(--qqx-brand);
}

.command-item-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.command-item-title {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
  line-height: 1.4;
}

.command-item-desc {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.command-match {
  color: var(--qqx-brand);
  background: transparent;
  font-weight: var(--qqx-font-semibold);
}

.command-item-meta {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  flex-shrink: 0;
}

.command-kind {
  color: var(--qqx-text-tertiary);
  background: var(--qqx-bg-elevated);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  padding: 2px 8px;
  font-size: var(--qqx-font-size-tiny);
}

.command-shortcut {
  font-family: inherit;
  font-size: var(--qqx-font-size-tiny);
  color: var(--qqx-text-quaternary);
  background: var(--qqx-bg-subtle);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--qqx-border-color);
  flex-shrink: 0;
}

.command-empty {
  text-align: center;
  padding: var(--qqx-space-xl);
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-label);
}

.command-panel-footer {
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--qqx-space-lg);
  padding: var(--qqx-space-sm) var(--qqx-space-xl);
  border-top: 1px solid var(--qqx-border-color);
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
  flex-shrink: 0;
}

.command-panel-hints {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-lg);
}

.command-panel-hints span {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-xs);
}

.command-panel-hints kbd {
  min-width: 22px;
  padding: 2px 5px;
  border: 1px solid var(--qqx-border-color);
  border-radius: 4px;
  background: var(--qqx-bg-subtle);
  color: var(--qqx-text-secondary);
  font-family: inherit;
  font-size: var(--qqx-font-size-tiny);
  text-align: center;
}

.cp-enter-active {
  transition: opacity 0.15s ease;
}

.cp-leave-active {
  transition: opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.cp-enter-from,
.cp-leave-to {
  opacity: 0;
}

.command-panel {
  animation: cp-slide-up 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.cp-leave-active .command-panel {
  animation: cp-slide-up 0.15s cubic-bezier(0.4, 0, 0.2, 1) reverse;
}

@keyframes cp-slide-up {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 767px) {
  .command-panel-backdrop {
    padding: var(--qqx-space-md);
  }

  .command-panel {
    max-width: none;
    max-height: calc(100dvh - 24px);
  }

  .command-panel-search {
    min-height: 56px;
    padding: var(--qqx-space-md) var(--qqx-space-lg);
  }

  .command-panel-results {
    padding: var(--qqx-space-sm);
  }

  .command-panel-footer {
    padding: var(--qqx-space-sm) var(--qqx-space-lg);
  }

  .command-panel-hints span:first-child {
    display: none;
  }

  .command-item-desc {
    max-width: 58vw;
  }
}
</style>
