<template>
  <span
    class="sr-provider-icon"
    :class="{
      'sr-provider-icon--multicolor': resolved.multicolor,
      'sr-provider-icon--shared': resolved.isShared,
      'sr-provider-icon--legacy': resolved.isLegacy,
      'sr-provider-icon--fallback': resolved.isFallback,
    }"
    :style="boxStyle"
    :data-provider-icon="resolved.key"
    :aria-hidden="decorative ? 'true' : undefined"
    :role="decorative ? undefined : 'img'"
    :aria-label="decorative ? undefined : ariaLabel"
    v-html="resolved.svg"
  />
</template>

<script>
let instanceCounter = 0
</script>

<script setup>
import { computed } from 'vue'
import { getProviderIcon } from '../sources/providerIcons.js'

const props = defineProps({
  /** Explicit icon key (e.g. "claude") or full target/agent object */
  icon: {
    type: [String, Object],
    default: null,
  },
  /** Target or built-in agent record ({ icon, agentKind, agent, id, path, relPath, shared, legacy }) */
  target: {
    type: Object,
    default: null,
  },
  agentKind: {
    type: String,
    default: null,
  },
  path: {
    type: String,
    default: null,
  },
  size: {
    type: [Number, String],
    default: 16,
  },
  decorative: {
    type: Boolean,
    default: true,
  },
  label: {
    type: String,
    default: '',
  },
})

const uid = `picon${++instanceCounter}`

const resolved = computed(() => {
  const source = props.target || (typeof props.icon === 'object' && props.icon !== null
    ? props.icon
    : {
        icon: typeof props.icon === 'string' ? props.icon : null,
        agentKind: props.agentKind,
        path: props.path,
      })
  return getProviderIcon(source, { idPrefix: uid })
})

const boxStyle = computed(() => {
  const px = typeof props.size === 'number' ? `${props.size}px` : String(props.size)
  return {
    width: px,
    height: px,
  }
})

const ariaLabel = computed(() => props.label || resolved.value.key)
</script>

<style scoped>
.sr-provider-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  line-height: 1;
  color: currentColor;
  pointer-events: none;
  vertical-align: middle;
}

.sr-provider-icon :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}

.sr-provider-icon--shared {
  color: var(--sr-role-blue-ink);
}

.sr-provider-icon--fallback {
  color: var(--sr-text-secondary);
}

.sr-provider-icon--legacy {
  color: var(--sr-text-secondary);
}

.sr-provider-icon--multicolor {
  border-radius: 22%;
  overflow: hidden;
}
</style>
