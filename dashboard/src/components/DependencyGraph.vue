<template>
  <section class="graph-section">
    <div class="section-header">
      <h2>依赖关系图</h2>
      <div class="graph-controls">
        <span class="graph-hint" v-if="collapsedCount">{{ collapsedCount }} 个大仓库已折叠</span>
        <button class="graph-ctrl-btn" @click="expandAll">展开全部</button>
        <button class="graph-ctrl-btn" @click="collapseAll">折叠全部</button>
      </div>
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
import { ref, reactive, onMounted, onUnmounted, watch, computed } from 'vue'
import { forceSimulation, forceLink, forceManyBody, forceX, forceY, forceCollide, forceCenter } from 'd3-force'
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

// Persisted layout so collapse/expand toggles don't reshuffle the whole graph.
// nodeId -> { x, y } captured on every tick; reused when re-rendering.
const positionCache = new Map()
// Persistent zoom layer. The <g> that carries the pan/zoom transform is created
// once and never removed, so toggling a repo (which rebuilds the graph) never
// re-applies the transform programmatically — which is what caused the
// spurious zoom animation on every click.
let zoomGroup = null
let zoomBehavior = null

// Number of child skills above which a repo is collapsed by default, so big
// repos (e.g. mattpocock-skills with ~38 skills) don't crowd out everything.
const COLLAPSE_THRESHOLD = 8

// Set of repo paths the user has explicitly toggled, mapping path -> collapsed?
// When a path is absent, the default (based on COLLAPSE_THRESHOLD) applies.
const collapseOverrides = reactive({})

// Count skills per repo (submodulePath).
const skillCountByRepo = computed(() => {
  const map = {}
  for (const s of state.skills) {
    if (s.submodulePath) map[s.submodulePath] = (map[s.submodulePath] || 0) + 1
  }
  return map
})

function isRepoCollapsed(repoPath) {
  if (repoPath in collapseOverrides) return collapseOverrides[repoPath]
  return (skillCountByRepo.value[repoPath] || 0) > COLLAPSE_THRESHOLD
}

const collapsedCount = computed(() => {
  return state.repoNodes.filter(r => isRepoCollapsed(r.path)).length
})

function toggleRepo(repoPath) {
  collapseOverrides[repoPath] = !isRepoCollapsed(repoPath)
  render()
}

function expandAll() {
  for (const r of state.repoNodes) collapseOverrides[r.path] = false
  render()
}

function collapseAll() {
  for (const r of state.repoNodes) collapseOverrides[r.path] = true
  render()
}

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
  // If the extended data (repoNodes/relationships) hasn't loaded yet, skip
  // this render — a later watch tick will re-render once it arrives. Without
  // this guard, the first paint sees an empty repoNodes array, seeds every
  // repo-root node at the d3 default origin (0,0), and caches those bad
  // positions — which is why repos pile up in the top-left until a manual
  // refresh clears the cache.
  if (state.skills.length === 0 && state.repoNodes.length === 0) return
  if (state.repoNodes.length === 0 && state.relationships.length === 0) return

  // Stop any prior simulation so repeated renders (collapse/expand toggles,
  // resize) don't leave orphaned simulations ticking in the background.
  if (simulation) {
    simulation.stop()
    simulation = null
  }

  const width = container.value.clientWidth
  const height = Math.max(container.value.clientHeight, 400)

  const svgEl = select(svg.value)
  svgEl.attr('width', width).attr('height', height)

  // Set up the persistent zoom layer exactly once. The zoom behavior and its
  // internal transform live on the <svg> element; the <g> that mirrors the
  // transform is never recreated, so toggles don't dispatch a fresh zoom event
  // (the cause of the phantom zoom-in on every node click).
  if (!zoomBehavior) {
    zoomBehavior = zoom()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        if (zoomGroup) zoomGroup.attr('transform', event.transform)
      })
    svgEl.call(zoomBehavior)
    zoomGroup = svgEl.append('g').attr('class', 'graph-zoom-root')
  } else {
    // Re-attach listeners in case the <svg> DOM node was swapped (e.g. v-if).
    svgEl.call(zoomBehavior)
  }
  if (!zoomGroup || svgEl.select('.graph-zoom-root').empty()) {
    zoomGroup = svgEl.append('g').attr('class', 'graph-zoom-root')
  }
  // Rebuild only the graph contents, leaving the zoom layer + its transform
  // untouched so the viewport stays exactly where the user left it.
  zoomGroup.selectAll('*').remove()
  const g = zoomGroup

  // Merge skills + repoNodes, hiding child skills of collapsed repos.
  const visibleSkills = state.skills.filter(s => {
    if (s.submodulePath && isRepoCollapsed(s.submodulePath)) return false
    return true
  })
  // Index repo nodes by path so child skills can be seeded near their parent.
  const repoNodeByPath = new Map(state.repoNodes.map(r => [r.path, r]))

  // Decide whether this render is an incremental tweak (collapse/expand) or
  // a fresh layout (first paint, workspace switch, data refresh). The key
  // signal: did we previously cache positions for THIS set of nodes?
  // - Empty cache (first paint, or after workspace switch) → fresh layout.
  // - Cache populated but covering a DIFFERENT node set (workspace switched,
  //   skills changed substantially) → also fresh: detect by checking that
  //   the repoNodes are actually present in the cache. When the first render
  //   ran with repoNodes=[] (extended data not yet loaded), the cache holds
  //   only skill positions, so a later render with real repoNodes would be
  //   wrongly treated as incremental and skip the seed rings.
  const candidateIds = new Set([
    ...visibleSkills.map(s => s.id),
    ...state.repoNodes.map(r => r.id),
  ])
  let matched = 0
  let repoMatched = 0
  for (const id of candidateIds) if (positionCache.has(id)) matched++
  for (const r of state.repoNodes) if (positionCache.has(r.id)) repoMatched++
  const isIncremental = candidateIds.size > 0
    && matched / candidateIds.size >= 0.5
    // If repoNodes exist now but none of them are cached, the cache was
    // built from an earlier render that ran before repoNodes loaded — treat
    // it as stale and force a fresh layout so seed rings get applied.
    && (state.repoNodes.length === 0 || repoMatched > 0)
  if (!isIncremental) positionCache.clear()

  // Restore a node's previous position, or seed it near its parent repo so
  // newly-revealed children expand outward instead of flying in from origin.
  function seedPosition(node, parentPath) {
    const cached = positionCache.get(node.id)
    if (cached) {
      node.x = cached.x
      node.y = cached.y
      return
    }
    const parentPos = parentPath ? positionCache.get(parentPath) : null
    if (parentPos) {
      // Small random offset around the parent for a natural fan-out.
      const angle = Math.random() * Math.PI * 2
      const dist = 30 + Math.random() * 40
      node.x = parentPos.x + Math.cos(angle) * dist
      node.y = parentPos.y + Math.sin(angle) * dist
    }
    // Nodes without a parent AND without a pre-assigned seed keep d3's
    // default (handled by initializeNodes). assignInitialSeeds() below
    // pre-seeds repo roots and standalone skills on rings around the center.
  }

  // For a fresh layout (not incremental), pre-assign seed positions so the
  // graph starts in a sensible shape: repo roots on an inner ring, standalone
  // skills on an outer ring. This gives the "repos in the middle, isolated
  // skills around" layout on first paint WITHOUT needing a strong center
  // force to maintain it at runtime.
  if (!isIncremental) {
    const cx = width / 2
    const cy = height / 2
    const ringR = Math.min(width, height) * 0.18
    const outerR = Math.min(width, height) * 0.34

    // Repo roots: evenly spaced on the inner ring.
    state.repoNodes.forEach((r, i) => {
      if (positionCache.has(r.id)) return
      const angle = state.repoNodes.length > 1
        ? (i / state.repoNodes.length) * Math.PI * 2
        : 0
      positionCache.set(r.id, {
        x: cx + Math.cos(angle) * ringR,
        y: cy + Math.sin(angle) * ringR,
      })
    })

    // Standalone skills (no submodulePath): evenly spaced on the outer ring.
    const standalone = visibleSkills.filter(s => !s.submodulePath)
    standalone.forEach((s, i) => {
      if (positionCache.has(s.id)) return
      const angle = standalone.length > 1
        ? (i / standalone.length) * Math.PI * 2 + 0.4
        : 0
      positionCache.set(s.id, {
        x: cx + Math.cos(angle) * outerR,
        y: cy + Math.sin(angle) * outerR,
      })
    })
  }
  const allNodes = [
    ...visibleSkills.map(s => {
      const node = { ...s }
      seedPosition(node, s.submodulePath)
      return node
    }),
    ...state.repoNodes.map(r => {
      const node = {
        ...r,
        _collapsed: isRepoCollapsed(r.path),
        _childCount: skillCountByRepo.value[r.path] || 0,
      }
      seedPosition(node, null)
      return node
    }),
  ]
  const visibleIds = new Set(allNodes.map(n => n.id))
  // Drop links whose endpoints are hidden (collapsed repo children).
  const links = state.relationships
    .filter(r => visibleIds.has(r.from) && visibleIds.has(r.to))
    .map(r => ({ source: r.from, target: r.to, type: r.type }))

  // Ensure all relationship endpoints exist as nodes
  const nodeIds = new Set(allNodes.map(n => n.id))
  for (const link of links) {
    if (!nodeIds.has(link.source)) {
      const node = { id: link.source, name: link.source, type: 'container', graphType: 'container' }
      seedPosition(node, null)
      allNodes.push(node)
      nodeIds.add(link.source)
    }
    if (!nodeIds.has(link.target)) {
      const node = { id: link.target, name: link.target, type: 'container', graphType: 'container' }
      seedPosition(node, null)
      allNodes.push(node)
      nodeIds.add(link.target)
    }
  }

  // Scale forces with node count so dense graphs spread out more.
  const n = allNodes.length
  // Stronger repulsion + longer links for breathing room.
  const charge = n > 120 ? -300 : n > 60 ? -220 : -160

  // Link distance by relationship type: "contains" edges (repo -> its child
  // skill) stay short so a repo and its skills hold together as one cluster;
  // "depends-on" edges can be long to keep the dependency visible.
  function linkDistance(link) {
    return link.type === 'contains' ? 60 : 150
  }

  // Weak uniform gravity — just enough to prevent drift, NOT strong enough
  // to collapse the graph into a tight clump. The "repos in center, isolated
  // on periphery" layout comes from the initial seed ring, not from runtime
  // center-pulling.
  const gravity = 0.025

  // First paint converges from scratch (high alpha); subsequent re-renders
  // (collapse/expand) start from the cached layout with a gentle alpha so the
  // existing graph barely moves and only the changed region settles.
  simulation = forceSimulation(allNodes)
    .force('link', forceLink(links).id(d => d.id).distance(linkDistance))
    .force('charge', forceManyBody().strength(charge))
    // forceCenter: translates the whole layout's centroid to canvas center —
    // direct, alpha-independent, guarantees overall centering even when
    // seed positions or the container size weren't ready on first paint.
    .force('center', forceCenter(width / 2, height / 2))
    // forceX/forceY: weak uniform pull to prevent drift; layout shape is
    // determined by the seed rings + link forces, not by strong gravity.
    .force('x', forceX(width / 2).strength(gravity))
    .force('y', forceY(height / 2).strength(gravity))
    .force('collide', forceCollide(d => getNodeRadius(d) + 10))
    .alpha(isIncremental ? 0.35 : 1)
    .alphaDecay(isIncremental ? 0.08 : 0.0228)

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
        // Pulse alpha to 0.3 but let it decay to 0 (alphaTarget stays 0), so
        // that pressing-and-holding a node without dragging lets the layout
        // settle and stop — instead of running forever and scattering nodes.
        if (!event.active) simulation.alphaTarget(0).alpha(0.3).restart()
        d.fx = d.x
        d.fy = d.y
      })
      .on('drag', (event, d) => {
        d.fx = event.x
        d.fy = event.y
        // Keep the simulation warm only while the pointer actually moves.
        simulation.alpha(0.15).restart()
      })
      .on('end', (event, d) => {
        // Release the dragged node, then trigger a settle pass: a higher
        // alpha pulse lets the weak center-gravity (forceX/forceY) pull any
        // nodes that were pushed aside back toward the cluster, so the graph
        // contracts back together instead of staying spread out.
        d.fx = null
        d.fy = null
        simulation.alphaTarget(0).alpha(0.6).restart()
      })
    )
    .on('click', (event, d) => {
      event.stopPropagation()
      hidePopover()
      if (d.isSubmoduleRoot) {
        // Collapsible repos: toggle on click; small repos navigate as before.
        if ((d._childCount || 0) > 0) {
          toggleRepo(d.path)
        } else {
          router.push({ name: 'repos', query: { submodule: d.path } })
        }
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

  // Dashed outer ring marks a collapsible repo (so users know it's clickable).
  node.filter(d => d.isSubmoduleRoot && (d._childCount || 0) > 0)
    .append('circle')
    .attr('r', d => getNodeRadius(d) + 4)
    .attr('fill', 'none')
    .attr('stroke', d => getNodeColor(d))
    .attr('stroke-width', 1)
    .attr('stroke-dasharray', '3,2')
    .attr('opacity', 0.6)

  // Child-count badge for collapsed repos.
  const collapsedRepos = node.filter(d => d.isSubmoduleRoot && d._collapsed && (d._childCount || 0) > 0)
  collapsedRepos.append('circle')
    .attr('cx', d => getNodeRadius(d) - 2)
    .attr('cy', d => -(getNodeRadius(d) - 2))
    .attr('r', 9)
    .attr('fill', '#ef4444')
  collapsedRepos.append('text')
    .text(d => d._childCount)
    .attr('x', d => getNodeRadius(d) - 2)
    .attr('y', d => -(getNodeRadius(d) - 2))
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', '9px')
    .attr('font-weight', '600')
    .attr('fill', '#fff')

  // +/− indicator inside collapsible repo nodes.
  node.filter(d => d.isSubmoduleRoot && (d._childCount || 0) > 0)
    .append('text')
    .text(d => d._collapsed ? '+' : '−')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', '14px')
    .attr('font-weight', '700')
    .attr('fill', '#fff')
    .style('pointer-events', 'none')

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

    // Persist positions so the next render can resume from this layout
    // instead of relayouting the entire graph from scratch.
    for (const d of allNodes) {
      positionCache.set(d.id, { x: d.x, y: d.y })
    }
  })
}

onMounted(() => {
  // Defer first render to the next frame so the browser has finished layout
  // and container.clientWidth/Height are non-zero — without this, render()
  // reads 0 for width and seeds all nodes near the origin (top-left pile).
  requestAnimationFrame(() => {
    try { render() } catch (e) { console.error('DependencyGraph render error:', e) }
  })
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

.graph-controls {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  margin-left: auto;
}

.graph-hint {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
}

.graph-ctrl-btn {
  padding: 4px 12px;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-surface);
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  font-family: inherit;
  cursor: pointer;
  transition: all var(--qqx-transition);
}

.graph-ctrl-btn:hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-primary);
  border-color: var(--qqx-brand);
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
