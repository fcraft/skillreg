<template>
  <section class="graph-section">
    <div class="section-header">
      <h2>依赖关系图</h2>
    </div>
    <div class="graph-container" ref="container">
      <svg ref="svg"></svg>
    </div>

    <!-- Legend -->
    <div class="graph-legend">
      <div class="legend-item" v-for="item in legendItems" :key="item.label">
        <span class="legend-dot" :style="{ background: item.color, width: item.size + 'px', height: item.size + 'px' }"></span>
        <span class="legend-label">{{ item.label }}</span>
      </div>
      <div class="legend-divider"></div>
      <div class="legend-item">
        <span class="legend-line"></span>
        <span class="legend-label">contains</span>
      </div>
      <div class="legend-item">
        <span class="legend-line legend-line--dashed"></span>
        <span class="legend-label">depends-on</span>
      </div>
    </div>

    <!-- Popover -->
    <Teleport to="body">
      <Transition name="qqx-popover">
        <div
          v-if="popover.node"
          class="graph-popover"
          :style="{ top: popover.top + 'px', left: popover.left + 'px' }"
        >
          <div class="popover-header">
            <span class="popover-name">{{ popover.node.name }}</span>
            <span class="popover-badge" :style="{ background: popover.color + '1a', color: popover.color }">
              {{ popover.typeLabel }}
            </span>
          </div>
          <div v-if="popover.node.description" class="popover-desc">{{ popover.node.description }}</div>
          <div v-if="popover.node.submodulePath && !popover.node.isSubmoduleRoot" class="popover-meta">
            仓库: {{ popover.node.submodulePath.replace('repos/', '') }}
          </div>
          <div v-if="popover.node.path" class="popover-path">{{ popover.node.path }}</div>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force'
import { select } from 'd3-selection'
import { drag } from 'd3-drag'
import { zoom, zoomIdentity } from 'd3-zoom'

import { useData } from '../composables/useData.js'
import { useRouter } from 'vue-router'
import { useSkillDetail } from '../composables/useSkillDetail.js'

const { state } = useData()
const router = useRouter()
const { show } = useSkillDetail()

const container = ref(null)
const svg = ref(null)
let simulation = null
let resizeObserver = null
let popoverTimer = null

const GRAPH_COLORS = {
  'isolated-skill': '#10b981',
  'repo-root':      '#f59e0b',
  'repo-cli':       '#6366f1',
  'repo-skill':     '#3b82f6',
  'cli-skill':      '#818cf8',
  'container':      '#6b7280',
}

const TYPE_LABELS = {
  'isolated-skill': '孤立 Skill',
  'repo-root':      '仓库',
  'repo-cli':       'CLI 仓库',
  'repo-skill':     'Skill 仓库',
  'cli-skill':      'CLI Skill',
  'container':      '未知',
}

const legendItems = [
  { label: '孤立 Skill', color: GRAPH_COLORS['isolated-skill'], size: 14 },
  { label: '仓库', color: GRAPH_COLORS['repo-root'], size: 20 },
  { label: 'CLI 仓库', color: GRAPH_COLORS['repo-cli'], size: 20 },
  { label: 'Skill 仓库', color: GRAPH_COLORS['repo-skill'], size: 20 },
  { label: 'CLI Skill', color: GRAPH_COLORS['cli-skill'], size: 14 },
]

const popover = reactive({ node: null, top: 0, left: 0, color: '', typeLabel: '' })

function getNodeColor(d) {
  return GRAPH_COLORS[d.graphType || d.type] || GRAPH_COLORS.container
}

function getNodeRadius(d) {
  if (d.isSubmoduleRoot || d.graphType === 'repo-cli' || d.graphType === 'repo-skill' || d.graphType === 'repo-root') return 20
  return 14
}

function showPopover(event, d) {
  clearTimeout(popoverTimer)
  popoverTimer = setTimeout(() => {
    const color = getNodeColor(d)
    popover.node = d
    popover.color = color
    popover.typeLabel = TYPE_LABELS[d.graphType || d.type] || '未知'

    const rect = event.target.closest('g').getBoundingClientRect()
    let x = rect.left + rect.width / 2
    let y = rect.top - 8

    // Clamp to viewport
    const pw = 260, ph = 120
    if (x - pw / 2 < 8) x = pw / 2 + 8
    if (x + pw / 2 > window.innerWidth - 8) x = window.innerWidth - pw / 2 - 8
    if (y - ph < 8) y = rect.bottom + 8

    popover.left = x
    popover.top = y
  }, 300)
}

function hidePopover() {
  clearTimeout(popoverTimer)
  popover.node = null
}

function render() {
  if (!container.value || !svg.value) return
  if (state.skills.length === 0 && state.repoNodes.length === 0) return

  const width = container.value.clientWidth
  const height = Math.max(container.value.clientHeight, 400)

  const svgEl = select(svg.value)
  svgEl.selectAll('*').remove()
  svgEl.attr('width', width).attr('height', height)

  const g = svgEl.append('g')

  const zoomBehavior = zoom()
    .scaleExtent([0.5, 3])
    .on('zoom', (event) => g.attr('transform', event.transform))
  svgEl.call(zoomBehavior)

  // Merge skills + repoNodes
  const allNodes = [...state.skills.map(s => ({ ...s })), ...state.repoNodes.map(r => ({ ...r }))]
  const links = state.relationships.map(r => ({
    source: r.from,
    target: r.to,
    type: r.type
  }))

  // Ensure all relationship endpoints exist as nodes
  const nodeIds = new Set(allNodes.map(n => n.id))
  for (const link of links) {
    if (!nodeIds.has(link.source)) {
      allNodes.push({ id: link.source, name: link.source, type: 'container', graphType: 'container' })
      nodeIds.add(link.source)
    }
    if (!nodeIds.has(link.target)) {
      allNodes.push({ id: link.target, name: link.target, type: 'container', graphType: 'container' })
      nodeIds.add(link.target)
    }
  }

  simulation = forceSimulation(allNodes)
    .force('link', forceLink(links).id(d => d.id).distance(100))
    .force('charge', forceManyBody().strength(-80))
    .force('center', forceCenter(width / 2, height / 2))
    .force('collide', forceCollide(30))

  // Links
  const link = g.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', 'var(--qqx-border-color)')
    .attr('stroke-width', 1.5)
    .attr('stroke-dasharray', d => d.type === 'depends-on' ? '4,4' : null)

  // Nodes
  const node = g.append('g')
    .selectAll('g')
    .data(allNodes)
    .join('g')
    .style('cursor', 'pointer')
    .call(drag()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
      })
      .on('drag', (event, d) => {
        d.fx = event.x
        d.fy = event.y
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0)
        d.fx = null
        d.fy = null
      })
    )
    .on('click', (event, d) => {
      event.stopPropagation()
      hidePopover()
      if (d.isSubmoduleRoot) {
        router.push({ name: 'repos', query: { submodule: d.path } })
      } else if (d.submodulePath) {
        router.push({ name: 'repos', query: { submodule: d.submodulePath, skill: d.name } })
      } else {
        show(d.name || d.id)
      }
    })
    .on('mouseenter', function (event, d) {
      select(this).select('circle').attr('stroke', '#0099ff').attr('stroke-width', 2)
      showPopover(event, d)
    })
    .on('mouseleave', function () {
      select(this).select('circle').attr('stroke', null)
      hidePopover()
    })

  node.append('circle')
    .attr('r', d => getNodeRadius(d))
    .attr('fill', d => getNodeColor(d))
    .attr('opacity', 0.85)

  node.append('text')
    .text(d => d.name)
    .attr('dy', d => getNodeRadius(d) + 12)
    .attr('text-anchor', 'middle')
    .attr('font-size', '11px')
    .attr('fill', 'var(--qqx-text-secondary)')

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)

    node.attr('transform', d => `translate(${d.x},${d.y})`)
  })
}

onMounted(() => {
  try { render() } catch (e) { console.error('DependencyGraph render error:', e) }
  resizeObserver = new ResizeObserver(() => {
    if (simulation) simulation.stop()
    try { render() } catch (e) { console.error('DependencyGraph resize render error:', e) }
  })
  if (container.value) resizeObserver.observe(container.value)
})

onUnmounted(() => {
  if (simulation) simulation.stop()
  if (resizeObserver) resizeObserver.disconnect()
  clearTimeout(popoverTimer)
})

watch(() => [state.skills, state.repoNodes, state.relationships], render, { deep: true })
</script>

<style scoped>
.graph-section {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 160px);
  position: relative;
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  margin-bottom: var(--qqx-space-lg);
  flex-shrink: 0;
}

.section-header h2 {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
}

.graph-container {
  flex: 1;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-surface);
  overflow: hidden;
}

.graph-container svg {
  display: block;
  width: 100%;
  cursor: grab;
}

.graph-container svg:active {
  cursor: grabbing;
}

/* Legend */
.graph-legend {
  position: absolute;
  top: 60px;
  right: 12px;
  background: var(--qqx-bg-card);
  border: 1px solid var(--qqx-border-color);
  border-radius: 12px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 10;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-dot {
  border-radius: 9999px;
  flex-shrink: 0;
}

.legend-label {
  font-size: 12px;
  color: var(--qqx-text-secondary);
  white-space: nowrap;
}

.legend-divider {
  height: 1px;
  background: var(--qqx-border-color);
  margin: 2px 0;
}

.legend-line {
  width: 20px;
  height: 0;
  border-top: 1.5px solid var(--qqx-border-color);
  flex-shrink: 0;
}

.legend-line--dashed {
  border-top-style: dashed;
}

/* Popover */
.graph-popover {
  position: fixed;
  transform: translateX(-50%) translateY(-100%);
  background: var(--qqx-bg-card);
  border: 1px solid var(--qqx-border-color);
  border-radius: 12px;
  padding: 10px 14px;
  min-width: 200px;
  max-width: 280px;
  z-index: var(--z-tooltip, 1000);
  pointer-events: none;
}

.popover-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.popover-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--qqx-text-primary);
}

.popover-badge {
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 9999px;
  white-space: nowrap;
}

.popover-desc {
  font-size: 12px;
  color: var(--qqx-text-secondary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 4px;
}

.popover-meta {
  font-size: 12px;
  color: var(--qqx-text-tertiary);
  margin-bottom: 2px;
}

.popover-path {
  font-size: 11px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--qqx-text-tertiary);
}

/* Popover transition */
.qqx-popover-enter-active {
  transition: opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}
.qqx-popover-leave-active {
  transition: opacity 0.1s cubic-bezier(0.4, 0, 0.2, 1);
}
.qqx-popover-enter-from,
.qqx-popover-leave-to {
  opacity: 0;
}
</style>
