<template>
  <Teleport to="body">
    <Transition name="cp">
      <div v-if="isOpen" class="command-panel-backdrop" @click="close">
        <div ref="panelRef" class="command-panel" @click.stop>
          <div class="command-panel-search">
            <Search :size="18" class="search-icon" />
            <input
              ref="searchInput"
              v-model="query"
              placeholder="搜索命令或页面..."
              class="search-input"
            />
          </div>
          <div class="command-panel-results">
            <template v-for="section in sections" :key="section.name">
              <div class="command-section-title">{{ section.name }}</div>
              <div
                v-for="item in section.items"
                :key="item.id"
                :class="['command-item', { active: activeIndex === flatIndex(item) }]"
                @click="execute(item)"
                @mouseenter="activeIndex = flatIndex(item)"
              >
                <component :is="item.icon" :size="16" v-if="item.icon" class="command-item-icon" />
                <div class="command-item-text">
                  <span class="command-item-title">{{ item.title }}</span>
                  <span class="command-item-desc" v-if="item.description">{{ item.description }}</span>
                </div>
                <kbd v-if="item.shortcut" class="command-shortcut">{{ item.shortcut }}</kbd>
              </div>
            </template>
            <div v-if="!hasResults" class="command-empty">无匹配结果</div>
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

const sections = computed(() => {
  const cmds = searchCommands(query.value)
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

function close() {
  isOpen.value = false
}

function execute(item) {
  item.action()
  close()
}

// Watch: reset active index when query changes
watch(query, () => {
  activeIndex.value = 0
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
  // Open: Ctrl+K or Cmd+K — disable in input/textarea to allow typing 'k'
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    // Only intercept when NOT focused in a text input (allow typing "k" with Ctrl in inputs)
    if (isOpen.value) {
      // Panel already open: Ctrl+K does nothing special (user may want to type 'k' in search)
      return
    }
    e.preventDefault()
    isOpen.value = true
    return
  }

  if (!isOpen.value) return

  // Escape: close
  if (e.key === 'Escape') {
    e.preventDefault()
    close()
    return
  }

  // Arrow navigation
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

  // Enter: execute selected command
  if (e.key === 'Enter') {
    const item = flatItems.value[activeIndex.value]
    if (item) {
      e.preventDefault()
      item.action()
      close()
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
/* ===== Backdrop ===== */
.command-panel-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-command);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
  background: var(--qqx-bg-backdrop);
  backdrop-filter: blur(16px) saturate(180%);
}

/* ===== Panel ===== */
.command-panel {
  width: 100%;
  max-width: 600px;
  background: var(--qqx-modal-bg);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-lg);
  box-shadow: var(--qqx-modal-shadow);
  overflow: hidden;
}

/* ===== Search ===== */
.command-panel-search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: var(--qqx-space-lg);
  border-bottom: 1px solid var(--qqx-border-color);
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
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-primary);
  font-family: var(--qqx-font-family);
}

.search-input::placeholder {
  color: var(--qqx-text-tertiary);
}

/* ===== Results ===== */
.command-panel-results {
  max-height: 320px;
  overflow-y: auto;
  padding: var(--qqx-space-sm);
}

.command-section-title {
  font-size: var(--qqx-font-size-tiny);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-quaternary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: var(--qqx-space-sm) var(--qqx-space-md) var(--qqx-space-xs);
}

/* ===== Items ===== */
.command-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px var(--qqx-space-md);
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

/* ===== Empty state ===== */
.command-empty {
  text-align: center;
  padding: var(--qqx-space-xl);
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-label);
}

/* ===== Transitions ===== */
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
</style>
