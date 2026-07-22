import { createRouter, createWebHistory } from 'vue-router'
import SkillGrid from '../components/SkillGrid.vue'
import SubmoduleStatus from '../components/SubmoduleStatus.vue'
import SkillSyncManager from '../components/SkillSyncManager.vue'
import DependencyGraph from '../components/DependencyGraph.vue'
import GitLog from '../components/GitLog.vue'
import ProjectManager from '../components/ProjectManager.vue'
import ComponentPlayground from '../components/ComponentPlayground.vue'
import SourceManager from '../components/SourceManager.vue'

const routes = [
  { path: '/', redirect: '/skills' },
  { path: '/skills', name: 'skills', component: SkillGrid },
  { path: '/repos', name: 'repos', component: SubmoduleStatus },
  { path: '/sources', name: 'sources', component: SourceManager },
  { path: '/sync', name: 'sync', component: SkillSyncManager },
  { path: '/projects', name: 'projects', component: ProjectManager },
  { path: '/graph', name: 'graph', component: DependencyGraph },
  { path: '/logs', name: 'logs', component: GitLog },
  { path: '/playground', name: 'playground', component: ComponentPlayground },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
