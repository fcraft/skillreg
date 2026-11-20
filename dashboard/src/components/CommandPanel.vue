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
  z-index: var(--sr-z-command);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 8vh var(--sr-space-5) var(--sr-space-6);
  background: var(--sr-overlay-scrim);
}

.command-panel {
  width: 100%;
  max-width: 840px;
  max-height: min(680px, calc(100dvh - 64px));
  display: flex;
  flex-direction: column;
  padding: var(--sr-space-4);
  gap: var(--sr-space-3);
  background: var(--sr-glass-bg);
  backdrop-filter: var(--sr-glass-filter);
  -webkit-backdrop-filter: var(--sr-glass-filter);
  border: none;
  border-radius: var(--sr-radius-lg);
  box-shadow: var(--sr-shadow-lg);
  overflow: hidden;
  animation: cp-slide-up var(--sr-duration-normal) var(--sr-ease-smooth);
}

.command-panel-search {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  min-height: 44px;
  padding: 0 14px;
  border-radius: var(--sr-radius-md);
  background: var(--sr-control-bg);
  flex-shrink: 0;
  transition: box-shadow 180ms var(--sr-ease-standard);
}

.command-panel-search:focus-within {
  box-shadow: var(--sr-control-focus-shadow);
}

.search-icon {
  color: var(--sr-text-tertiary);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--sr-text-body);
  color: var(--sr-text-primary);
  font-family: var(--sr-font-sans);
}

.search-input::placeholder {
  color: var(--sr-text-tertiary);
}

.command-panel-results {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: 2px;
}

.command-section-title {
  position: sticky;
  top: 0;
  z-index: 1;
  font-size: var(--sr-text-micro);
  font-weight: var(--sr-weight-bold);
  color: var(--sr-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: var(--sr-space-3) 10px var(--sr-space-1);
  background: var(--sr-sticky-bg);
  backdrop-filter: var(--sr-sticky-filter);
}

.command-item {
  display: flex;
  align-items: center;
  gap: var(--sr-space-3);
  min-height: 44px;
  padding: 8px 10px;
  border-radius: var(--sr-radius-sm);
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.command-item:not(.active):hover {
  background: var(--sr-bg-hover);
}

.command-item.active {
  background: var(--sr-action-bg-selected);
}

.command-item-icon {
  color: var(--sr-text-secondary);
  flex-shrink: 0;
}

.command-item.active .command-item-icon {
  color: var(--sr-accent);
}

.command-item-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.command-item-title {
  font-size: var(--sr-text-card-title);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
  line-height: 1.45;
}

.command-item-desc {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.command-match {
  color: var(--sr-accent);
  background: transparent;
  font-weight: var(--sr-weight-semibold);
}

.command-item-meta {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  flex-shrink: 0;
}

.command-kind {
  color: var(--sr-text-secondary);
  background: var(--sr-content-bg);
  border-radius: var(--sr-radius-badge);
  padding: 2px 8px;
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
}

.command-shortcut {
  font-family: var(--sr-font-mono);
  font-size: var(--sr-text-micro);
  color: var(--sr-text-tertiary);
  background: var(--sr-control-bg);
  padding: 2px 6px;
  border-radius: var(--sr-radius-xs);
  flex-shrink: 0;
}

.command-empty {
  text-align: center;
  padding: var(--sr-space-5);
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-card-title);
}

.command-panel-footer {
  min-height: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sr-space-4);
  padding: var(--sr-space-1) 6px 0;
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-compact);
  flex-shrink: 0;
}

.command-panel-hints {
  display: flex;
  align-items: center;
  gap: var(--sr-space-3);
}

.command-panel-hints span {
  display: flex;
  align-items: center;
  gap: var(--sr-space-1);
}

.command-panel-hints kbd {
  min-width: 22px;
  padding: 2px 6px;
  border-radius: var(--sr-radius-xs);
  background: var(--sr-control-bg);
  color: var(--sr-text-secondary);
  font-family: var(--sr-font-mono);
  font-size: var(--sr-text-micro);
  text-align: center;
}

.cp-enter-active,
.cp-leave-active {
  transition: opacity var(--sr-duration-fast) var(--sr-ease-standard);
}

.cp-enter-from,
.cp-leave-to {
  opacity: 0;
}

.cp-leave-active .command-panel {
  animation: cp-slide-up 140ms var(--sr-ease-standard) reverse;
}

@keyframes cp-slide-up {
  from { opacity: 0; transform: translateY(-6px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@media (max-width: 760px) {
  .command-panel-backdrop { padding: var(--sr-space-3); }
  .command-panel { max-width: none; max-height: calc(100dvh - 24px); }
  .command-panel-hints span:first-child { display: none; }
  .command-item-desc { max-width: 58vw; }
}

@media (prefers-reduced-motion: reduce) {
  .command-panel, .cp-leave-active .command-panel { animation: none; }
}
</style>
