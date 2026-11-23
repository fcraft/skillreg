<template>
  <div class="sync-manager">
    <!-- Header -->
    <div class="sync-header">
      <div class="sync-header-left">
        <h2 class="sync-title">Sync 工具</h2>
        <span class="sync-count" v-if="!loading">{{ skills.length }} skills &middot; {{ targets.length }} targets</span>
      </div>
      <div class="sync-header-actions">
        <div class="sync-view-tabs">
          <button :class="['sync-view-tab', { 'sync-view-tab--active': activeView === 'targets' }]" @click="activeView = 'targets'">目标</button>
          <button :class="['sync-view-tab', { 'sync-view-tab--active': activeView === 'projects' }]" @click="activeView = 'projects'">项目组</button>
        </div>
        <QButton v-if="activeView === 'targets'" type="ghost" size="small" @click="openAddTargetModal">+ 新增目标</QButton>
        <QButton v-if="activeView === 'targets'" type="ghost" size="small" @click="openDiscoverHome">
          <Search :size="14" /> 发现本机 Agent
        </QButton>
        <QButton type="ghost" size="small" @click="loadAll(true)"><RefreshCw :size="14" /> 刷新</QButton>
        <QButton v-if="activeView === 'targets'" type="primary" size="small" :disabled="syncing" @click="openSyncAllConfirm">
          <RefreshCw :size="14" /> {{ syncing ? '同步中...' : '全部同步' }}
        </QButton>
      </div>
    </div>

    <!-- Errors & Loading -->
    <div v-if="error" class="sync-error">{{ error }}</div>
    <div v-if="loading" class="sync-loading">加载同步状态...</div>
    <div v-else-if="!skills.length" class="sync-empty">未发现 skill</div>

    <!-- Main Content -->
    <template v-if="!loading && skills.length">
      <!-- Target View -->
      <template v-if="activeView === 'targets'">
      <div v-if="!allTargets.length" class="sync-empty-targets">
        <p class="sync-empty-targets-title">还没有同步目标</p>
        <p class="sync-empty-targets-desc">可从内置 Agent 预设中选择目录，或手动新增自定义同步目标。</p>
        <div class="sync-empty-targets-actions">
          <QButton type="secondary" size="small" @click="openDiscoverHome"><Search :size="14" /> 发现本机 Agent</QButton>
          <QButton type="primary" size="small" @click="openAddTargetModal">+ 新增目标</QButton>
        </div>
      </div>

      <template v-else>
      <!-- Target Selection Tabs -->
      <div class="target-tabs-row">
        <div class="target-tabs">
          <div
            v-for="t in allTargets"
            :key="t.path"
            class="target-tab-wrapper"
          >
            <button
              :class="['target-tab', { 'target-tab--active': activeTarget === t.path, 'target-tab--project': t._project }]"
              @click="switchTarget(t.path)"
            >
              <span class="target-tab-header">
                <ProviderIcon :target="t" :size="16" class="target-tab-icon" />
                <span class="target-tab-name">{{ t._label || t.label || t.name }}</span>
                <span v-if="targetBadgeText(t)" class="target-tab-badge" :class="{ 'target-tab-badge--shared': t.shared }">{{ targetBadgeText(t) }}</span>
              </span>
              <span class="target-tab-path" :title="t.path">{{ formatDisplayPath(t.path, t.relPath) }}</span>
            </button>
            <button
              class="target-tab-more"
              :class="{ 'target-tab-more--open': targetDropdownOpen === t.path }"
              @click.stop="toggleTargetDropdown(t.path)"
              title="更多操作"
            >
              <MoreHorizontal :size="14" />
            </button>
            <div v-if="targetDropdownOpen === t.path" class="target-dropdown" @click.stop>
              <template v-if="t.builtin">
                <button class="target-dropdown-item" @click="promoteBuiltinTarget(t)">
                  <Pencil :size="13" /> 保存为自定义目标
                </button>
                <button class="target-dropdown-item target-dropdown-item--danger" @click="hideBuiltinTarget(t)">
                  <Trash2 :size="13" /> 移出目标清单
                </button>
              </template>
              <template v-else>
                <button class="target-dropdown-item" @click="openRenameTarget(t)">
                  <Pencil :size="13" /> 重命名
                </button>
                <button class="target-dropdown-item target-dropdown-item--danger" @click="openDeleteTarget(t)">
                  <Trash2 :size="13" /> 删除
                </button>
              </template>
            </div>
          </div>
        </div>
        <div class="target-tab-actions">
          <QButton type="text" size="small" @click="openTargetFiles">管理目标文件</QButton>
          <QButton type="primary" size="small" :disabled="syncingInTarget" @click="syncActiveTarget">
            <RefreshCw :size="14" /> 同步 {{ activeTargetShort }}
          </QButton>
        </div>
      </div>

      <!-- Skill List for Active Target -->
      <QCard class="skill-list-card">
        <template #header>
          <span class="card-target-label">
            <ProviderIcon v-if="activeTargetObj" :target="activeTargetObj" :size="15" class="card-target-icon" />
            <span>Target: {{ activeTargetLabel }}</span>
          </span>
        </template>

        <!-- Installed Skills Section -->
        <div class="section-header">
          <h3>已安装 ({{ installedSkills.length }})</h3>
        </div>
        <div class="skill-list">
          <div v-for="entry in installedSkills" :key="entry.key" class="skill-list-row">
            <span class="skill-list-name" @click="showSkillDetail(entry.name)">{{ entry.name }}</span>
            <span class="skill-list-status" :class="entry.status">{{ entry.status }}</span>
            <div class="skill-list-actions">
              <QButton type="ghost" size="small"
                :disabled="syncingSkill === entry.name"
                @click="syncOneSkill(entry.name)">
                <RefreshCw :size="12" /> {{ syncingSkill === entry.name ? '...' : '同步' }}
              </QButton>
              <QButton type="ghost" size="small"
                @click="openDiff(entry.name)">
                Diff
              </QButton>
              <QButton type="secondary" tint="danger" size="small"
                :disabled="removingSkill === entry.name"
                @click="uninstallSkill(entry.name)">
                {{ removingSkill === entry.name ? '卸载中...' : '卸载' }}
              </QButton>
            </div>
          </div>
          <div v-if="!installedSkills.length" class="sync-empty">此 target 中未安装任何 skill</div>
        </div>

        <!-- Available Skills Section -->
        <div v-if="availableSkills.length" class="section-header">
          <h3>可安装 ({{ availableSkills.length }})</h3>
        </div>
        <div v-if="availableSkills.length" class="skill-list">
          <div v-for="entry in availableSkills" :key="entry.key" class="skill-list-row">
            <span class="skill-list-name" @click="showSkillDetail(entry.name)">{{ entry.name }}</span>
            <span class="skill-list-status not-installed">未安装</span>
            <div class="skill-list-actions">
              <QButton type="secondary" tint="brand" size="small"
                :disabled="installingSkill === entry.name"
                @click="installSkill(entry.name)">
                {{ installingSkill === entry.name ? '安装中...' : '安装' }}
              </QButton>
            </div>
          </div>
        </div>
      </QCard>
      </template>
      </template>

      <!-- Project View -->
      <div v-if="activeView === 'projects'" class="sync-projects">
        <div v-if="!projects.length && !projectsLoading" class="sync-empty">暂无项目组，在「项目组」页面创建</div>
        <div v-for="p in projects" :key="p.id" class="sp-card">
          <div class="sp-card-header" @click="expandedProject = expandedProject === p.id ? null : p.id">
            <span class="sp-chevron" :class="{ 'sp-chevron--open': expandedProject === p.id }">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </span>
            <span class="sp-name">{{ p.name }}</span>
            <span class="sp-count">{{ p.targets?.length || 0 }} 个目标</span>
            <span v-if="syncingProjectId === p.id" class="sp-syncing">同步中...</span>
          </div>
          <div v-if="expandedProject === p.id" class="sp-card-body">
            <!-- Skill × Target matrix -->
            <div class="sp-matrix">
              <!-- Column headers -->
              <div class="sp-matrix-header">
                <div class="sp-matrix-header-skill">Skill</div>
                <div v-for="t in p.targets" :key="t" class="sp-matrix-header-target" :title="t">
                  <span class="sp-matrix-col-label">{{ getTargetLabel(t) }}</span>
                  <div class="sp-matrix-col-agents">
                    <span v-for="d in (discoveredProjectMap[t]?.agent_dirs || [])" :key="d.agent" class="sp-agent-tag">
                      <ProviderIcon :target="d" :size="12" />
                      <span>{{ d.agent }}</span>
                    </span>
                    <span v-if="!(discoveredProjectMap[t]?.agent_dirs?.length)" class="sp-agent-tag sp-agent-tag--warn">直接</span>
                  </div>
                  <div class="sp-matrix-col-actions">
                    <span @click.stop><QButton type="text" size="small" @click="syncProjectTarget(p, t)"><RefreshCw :size="12" /> 同步</QButton></span>
                  </div>
                </div>
              </div>
              <!-- Rows -->
              <div v-for="skill in projectSkills(p)" :key="skill.name" class="sp-matrix-row">
                <div class="sp-matrix-skill">
                  <span class="sp-matrix-skill-name" @click="showSkillDetail(skill.name)">{{ skill.name }}</span>
                  <span class="sp-matrix-skill-status" v-if="getProjectSkillSummary(skill.name, p)">{{ getProjectSkillSummary(skill.name, p) }}</span>
                </div>
                <div v-for="t in p.targets" :key="t" class="sp-matrix-cell"
                  :class="'sp-cell--' + getProjectCellStatus(skill.name, t)"
                  :title="getProjectCellTooltip(skill.name, t)"
                  @click="onProjectCellClick(skill.name, t, p)"
                >
                  <span class="sp-cell-dot"></span>
                  <span class="sp-cell-label">{{ getProjectCellLabel(skill.name, t) }}</span>
                  <button
                    v-if="getProjectCellStatus(skill.name, t) === 'none'"
                    class="sp-cell-install"
                    @click.stop="installProjectSkill(skill.name, t)"
                    :disabled="installingSkill === skill.name"
                  >安装</button>
                </div>
              </div>
            </div>
            <div v-if="!projectSkills(p).length" class="sync-empty">暂无 skill 数据</div>
            <div class="sp-card-footer">
              <QButton type="primary" size="small" :disabled="syncing" @click="syncProject(p)"><RefreshCw :size="14" /> 一键同步</QButton>
              <QButton type="secondary" tint="brand" size="small" :disabled="syncing" @click="installProjectAll(p)"><Download :size="14" /> 一键安装全部</QButton>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Diff Modal -->
    <QModal v-model="showDiff" :title="`${diffSkill} → ${formatDisplayPath(diffTarget)}`" :width="selectedDiffFile ? '900px' : '640px'">
      <div v-if="diffLoading" class="sync-loading">加载差异...</div>
      <div v-else-if="diffError" class="sync-error">{{ diffError }}</div>
      <div v-else>
        <!-- File diff view (when a file is selected) -->
        <template v-if="selectedDiffFile">
          <div class="diff-file-nav">
            <QButton type="text" size="small" @click="closeFilePreview">← 返回文件列表</QButton>
            <code class="diff-file-nav-path">{{ selectedDiffFile }}</code>
          </div>
          <div v-if="previewLoading" class="sync-loading">加载文件内容...</div>
          <div v-else-if="previewError" class="sync-error">{{ previewError }}</div>
          <QDiffViewer v-else
            :repo-content="previewSource"
            :target-content="previewTarget"
            :file-path="selectedDiffFile" />
        </template>

        <!-- File list view (default) -->
        <template v-else>
          <div class="diff-summary">
            <span v-if="diffSummary.unchanged" class="diff-stat unchanged">{{ diffSummary.unchanged }} unchanged</span>
            <span v-if="diffSummary.added" class="diff-stat added">{{ diffSummary.added }} added</span>
            <span v-if="diffSummary.modified" class="diff-stat modified">{{ diffSummary.modified }} modified</span>
            <span v-if="diffSummary.removed" class="diff-stat removed">{{ diffSummary.removed }} removed</span>
          </div>
          <div v-if="hasChanges" class="diff-file-list">
            <div v-for="file in changedFiles" :key="file.path"
              class="diff-file-row" :class="file.status"
              @click="openFilePreview(file)">
              <span class="diff-file-status">{{ file.status }}</span>
              <code class="diff-file-path">{{ file.path }}</code>
            </div>
          </div>
          <div v-else-if="diffFiles.length" class="diff-all-unchanged">
            所有 {{ diffSummary.unchanged }} 个文件内容一致，无差异
          </div>
          <div v-else class="sync-empty">目标目录中无此 skill</div>
        </template>
      </div>
    </QModal>

    <!-- Add Target Modal -->
    <QModal v-model="addTargetOpen" title="新增目标目录" width="520px">
      <div class="add-target-form">
        <div v-if="quickPresets.length" class="preset-section">
          <div class="preset-label">常见 Agent 预设（点击快速填充，也可下方手动自定义）</div>
          <div class="preset-chips">
            <button
              v-for="agent in quickPresets"
              :key="agent.id"
              type="button"
              class="preset-chip"
              :class="{ 'preset-chip--active': newTarget.agentKind === agent.id }"
              :title="formatDisplayPath(agent.path, agent.rel_path)"
              @click="applyAgentPreset(agent)"
            >
              <ProviderIcon :target="agent" :size="14" />
              <span>{{ agent.name }}</span>
              <code class="preset-chip-path">{{ formatDisplayPath(agent.path, agent.rel_path) }}</code>
            </button>
          </div>
        </div>
        <div class="form-field">
          <label class="form-label">名称</label>
          <input v-model="newTarget.name" type="text" class="form-input" placeholder="例如: agents 或自定义名称" />
        </div>
        <div class="form-field">
          <label class="form-label">路径</label>
          <div class="form-input-row">
            <input v-model="newTarget.path" type="text" class="form-input form-input-flex" placeholder="例如: ~/.agents/skills 或任意自定义目录" @input="newTarget.agentKind = null" />
            <QButton type="secondary" size="large" :disabled="pickingDirectory" @click="pickDirectory">
              <FolderOpen :size="14" /> {{ pickingDirectory ? '选择中...' : '选择目录' }}
            </QButton>
          </div>
        </div>
        <div v-if="addTargetError" class="sync-error">{{ addTargetError }}</div>
      </div>
      <template #footer>
        <QButton type="secondary" size="small" @click="addTargetOpen = false">取消</QButton>
        <QButton type="primary" size="small" :disabled="addTargetSaving" @click="addTarget">
          {{ addTargetSaving ? '添加中...' : '确认添加' }}
        </QButton>
      </template>
    </QModal>

    <!-- Target Files Management Modal -->
    <QModal v-model="targetFilesOpen" :title="`目标文件管理 — ${formatDisplayPath(targetFilesTarget)}`" width="640px">
      <div v-if="targetFilesLoading" class="sync-loading">扫描目标目录...</div>
      <div v-else-if="targetFilesError" class="sync-error">{{ targetFilesError }}</div>
        <div v-else-if="targetFilesData && targetFilesData.skills">
        <div v-if="!targetFilesData.exists" class="sync-error">
          目标目录不存在: {{ formatDisplayPath(targetFilesData.path) }}
        </div>
        <template v-else>
          <div class="target-files-info">
            共 {{ targetFilesData.skills.length }} 个 skill 目录 ·
            本仓库管理 {{ managedCount }} ·
            非本仓库 {{ unmanagedCount }}
          </div>
          <div v-if="targetFilesData.skills.length" class="target-files-list">
            <div v-for="item in targetFilesData.skills" :key="item.name" class="target-file-row" :class="{ 'is-unmanaged': !item.managed }">
              <span class="target-file-name">{{ item.name }}</span>
              <span v-if="item.managed" class="target-file-badge managed">本仓库管理</span>
              <span v-else class="target-file-badge unmanaged">非本仓库</span>
              <div class="target-file-actions">
                <QButton v-if="item.managed"
                  type="danger" size="small"
                  :disabled="removingSkill === item.name"
                  @click="removeSkillFromTarget(item.name)">
                  {{ removingSkill === item.name ? '删除中...' : '删除' }}
                </QButton>
                <QButton v-else
                  type="ghost" size="small"
                  :disabled="removingSkill === item.name"
                  @click="confirmRemoveUnmanaged(item.name)">
                  {{ removingSkill === item.name ? '删除中...' : '删除' }}
                </QButton>
              </div>
            </div>
          </div>
          <div v-else class="sync-empty">目标目录为空</div>
        </template>
      </div>
    </QModal>

    <!-- Skill Detail Modal (shared via App.vue) -->


    <!-- Sync All Confirmation Modal -->
    <QModal v-model="syncAllConfirmOpen" title="确认全部同步" width="560px">
      <div class="sync-all-confirm-body">
        <p class="sync-all-confirm-desc">仓库共管理 <strong>{{ skills.length }}</strong> 个 skill，以下目录将同步已安装的子集：</p>

        <div v-if="syncAllPreloading" class="sync-all-loading">正在加载各目标安装状态...</div>

        <!-- Named targets -->
        <div v-if="!syncAllPreloading" class="sync-all-section">
          <div class="sync-all-section-title">配置目标 ({{ syncAllNamedTargets.length }})</div>
          <div v-for="t in syncAllNamedTargets" :key="t.path" class="sync-all-target-row">
            <div class="sync-all-target-info">
              <span class="sync-all-target-name">
                <ProviderIcon :target="t" :size="15" />
                <span>{{ t.label || t.name }}</span>
              </span>
              <span class="sync-all-target-path" :title="t.path">{{ formatDisplayPath(t.path) }}</span>
            </div>
            <span class="sync-all-target-skill-count">
              {{ t.skillCount }} skill<span v-if="t.changedCount"> · <em class="sync-all-changed">{{ t.changedCount }} 需更新</em></span><span v-else> · <em class="sync-all-ok">无需更新</em></span>
            </span>
          </div>
          <div v-if="!syncAllNamedTargets.length" class="sync-all-empty">无配置目标</div>
        </div>

        <!-- Project targets -->
        <template v-if="!syncAllPreloading" v-for="[projId, group] in syncAllProjectTargets" :key="projId">
          <div class="sync-all-section">
            <div class="sync-all-section-title">
              {{ group.projectName }} ({{ group.targets.length }} 个目标 · 将同步 {{ group.unionCount }} skill
              <span v-if="group.unionChanged"> · <em class="sync-all-changed">{{ group.unionChanged }} 需更新</em></span>
              <span v-else> · <em class="sync-all-ok">无需更新</em></span>)
            </div>
            <div v-for="t in group.targets" :key="t.path" class="sync-all-target-row">
              <div class="sync-all-target-info">
                <span class="sync-all-target-name">
                  <ProviderIcon :path="t.path" :size="15" />
                  <span>{{ getTargetLabel(t.path) }}</span>
                </span>
                <span class="sync-all-target-path" :title="t.path">{{ formatDisplayPath(t.path) }}</span>
              </div>
              <span class="sync-all-target-skill-count">
                当前 {{ t.skillCount }} → 同步 {{ group.unionCount }}
                <span v-if="t.changedCount"> · <em class="sync-all-changed">本目标 {{ t.changedCount }} 需更新</em></span>
                <span v-else> · <em class="sync-all-ok">无需更新</em></span>
              </span>
            </div>
          </div>
        </template>

        <div v-if="!syncAllPreloading" class="sync-all-summary">
          共计 <strong>{{ syncAllNamedTargets.length + totalProjectTargetCount }}</strong> 个目标目录 · 仓库共 <strong>{{ skills.length }}</strong> skill
        </div>

        <!-- Sync progress -->
        <div v-if="syncAllRunning" class="sync-all-progress">
          <div class="sync-all-progress-bar">
            <div class="sync-all-progress-fill" :style="{ width: syncAllProgress + '%' }"></div>
          </div>
          <span class="sync-all-progress-text">{{ syncAllDone }} / {{ syncAllTotal }}</span>
          <span v-if="syncAllCurrent" class="sync-all-current">{{ syncAllCurrent }}</span>
        </div>
        <div v-if="syncAllError" class="sync-error">{{ syncAllError }}</div>
      </div>
      <template #footer>
        <QButton type="secondary" size="small" :disabled="syncAllRunning || syncAllPreloading" @click="syncAllConfirmOpen = false">取消</QButton>
        <QButton type="primary" size="small" :disabled="syncAllRunning || syncAllPreloading" @click="executeSyncAll">
          <RefreshCw :size="14" /> {{ syncAllPreloading ? '加载中...' : '确认同步' }}
        </QButton>
      </template>
    </QModal>

    <!-- Rename Target Modal -->
    <QModal v-model="renameTargetOpen" title="修改目标路径" width="420px">
      <div class="rename-target-form">
        <div class="form-field">
          <label class="form-label">当前目标</label>
          <div class="form-static-value">{{ renameTargetLabel }}</div>
          <div class="form-static-subvalue" :title="renameTargetOldPath">{{ formatDisplayPath(renameTargetOldPath) }}</div>
        </div>
        <div class="form-field">
          <label class="form-label">新路径</label>
          <input
            ref="renameInputRef"
            v-model="renameTargetNewPath"
            type="text"
            class="form-input"
            placeholder="输入新的目标路径"
            @keyup.enter="doRenameTarget"
            @keyup.escape="renameTargetOpen = false"
          />
        </div>
        <div v-if="renameTargetError" class="sync-error">{{ renameTargetError }}</div>
      </div>
      <template #footer>
        <QButton type="secondary" size="small" @click="renameTargetOpen = false">取消</QButton>
        <QButton type="primary" size="small" :disabled="renameTargetSaving || !renameTargetNewPath.trim()" @click="doRenameTarget">
          {{ renameTargetSaving ? '修改中...' : '确认' }}
        </QButton>
      </template>
    </QModal>

    <!-- Delete Target Confirmation Modal -->
    <QModal v-model="deleteTargetOpen" title="删除目标" width="480px">
      <div class="confirm-remove-body">
        <div class="confirm-warn-icon"><TriangleAlert :size="36" /></div>
        <p class="confirm-warn-text">
          确认删除目标 <strong>{{ deleteTargetLabel }}</strong>？
          此操作仅移除配置文件中的目标记录，不会删除磁盘上的文件。
        </p>
        <div class="form-static-subvalue" :title="deleteTargetPath">{{ formatDisplayPath(deleteTargetPath) }}</div>
        <div v-if="deleteTargetError" class="sync-error">{{ deleteTargetError }}</div>
      </div>
      <template #footer>
        <QButton type="secondary" size="small" @click="deleteTargetOpen = false">取消</QButton>
        <QButton type="danger" size="small" :disabled="deleteTargetSaving" @click="doDeleteTarget">
          {{ deleteTargetSaving ? '删除中...' : '确认删除' }}
        </QButton>
      </template>
    </QModal>

    <!-- Confirm Remove Unmanaged Modal -->
    <QModal v-model="confirmRemoveOpen" title="确认删除非本仓库 Skill" width="480px">
      <div class="confirm-remove-body">
        <div class="confirm-warn-icon"><TriangleAlert :size="36" /></div>
        <p class="confirm-warn-text">
          <strong>{{ confirmRemoveSkill }}</strong> 不在本仓库的管理范围内。
          删除后将无法通过此工具恢复。
        </p>
        <QCheckbox v-model="confirmRemoveChecked" label="我确认要删除此 skill" />
        <div v-if="confirmRemoveError" class="sync-error">{{ confirmRemoveError }}</div>
      </div>
      <template #footer>
        <QButton type="secondary" size="small" @click="confirmRemoveOpen = false">取消</QButton>
        <QButton type="danger" size="small" :disabled="!confirmRemoveChecked || removingSkill" @click="doRemoveUnmanaged">
          {{ removingSkill ? '删除中...' : '确认删除' }}
        </QButton>
      </template>
    </QModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FolderOpen, TriangleAlert, RefreshCw, Download, Search, MoreHorizontal, Pencil, Trash2 } from 'lucide-vue-next'
import QCard from './QCard.vue'
import QButton from './QButton.vue'
import QCheckbox from './QCheckbox.vue'
import QModal from './QModal.vue'
import QDiffViewer from './QDiffViewer.vue'
import ProviderIcon from './ProviderIcon.vue'
import { useSyncBridge } from '../composables/useSyncBridge.js'
import { useSkillDetail } from '../composables/useSkillDetail.js'
import { useToast } from '../composables/useToast.js'
import { useEventBus } from '../composables/useEventBus.js'
import { useData } from '../composables/useData.js'
import {
  executeSync, fetchSyncConfig, fetchSkills, fetchSkillsRefresh,
  fetchSyncStatus, fetchSkillDiff, fetchSkillFile, fetchTargetFile,
  fetchProjects, fetchTargetSkills,
  addSyncTarget, removeSyncTarget, renameSyncTarget,
  removeSkillFromTarget as removeSkillApi,
  fetchBuiltinAgents, setBuiltinAgentEnabled,
  fetchDiscover, selectWorkspaceDirectory,
} from '../api/index.js'
import {
  buildPresetDraft,
  formatAgentDisplayPath,
  normalizeTarget,
  pickQuickPresets,
  targetBadgeText,
} from '../sources/agentTargets.js'

const { emit, on } = useEventBus()
const openDiscoverHome = () => emit('open-agent-picker')
const unsubscribeTargets = on('agent-targets-changed', () => loadAll(true))
const toast = useToast()
const { state: bridgeState, mergeTargetStatus } = useSyncBridge()
const route = useRoute()
const router = useRouter()

const skills = ref([])
const targets = ref([])
const statusMap = ref({})
const loading = ref(true)
const syncing = ref(false)
const syncingInTarget = ref(false)
const syncingSkill = ref(null)
const error = ref(null)

const activeTarget = ref('')
const installingSkill = ref(null)
const activeView = ref('targets')

// Project view state
const projects = ref([])
const projectsLoading = ref(false)
const expandedProject = ref(null)
const syncingProjectId = ref(null)
const discoveredProjectMap = ref({})

function parseSyncCount(stdout) {
  // Parse "✅ skillname (N files)" from Python output
  const matches = stdout?.match(/✅\s+\S+\s+\((\d+)\s*files?\)/g) || []
  let fileCount = 0
  let skillCount = matches.length
  for (const m of matches) {
    const n = parseInt(m.match(/\((\d+)/)?.[1] || '0')
    fileCount += n
  }
  return { skillCount, fileCount }
}

async function syncProject(proj) {
  if (!proj) return
  syncing.value = true
  syncingProjectId.value = proj.id
  error.value = null
  let totalFiles = 0
  let totalSkills = 0
  try {
    for (const t of (proj.targets || [])) {
      const data = await executeSync(t)
      if (!data?.success) throw new Error(data?.stderr || '同步失败')
      const { skillCount, fileCount } = parseSyncCount(data.stdout || '')
      totalFiles += fileCount
      totalSkills += skillCount
    }
    await refreshTargets(proj.targets || [])
    toast.success(`同步完成: ${totalSkills} 个 skill · ${totalFiles} 个文件`)
  } catch (e) {
    toast.error('同步失败: ' + e.message)
  } finally {
    syncing.value = false
    syncingProjectId.value = null
  }
}

async function syncProjectTarget(proj, targetPath) {
  syncingInTarget.value = true
  error.value = null
  try {
    const data = await executeSync(targetPath)
    if (!data?.success) throw new Error(data?.stderr || '同步失败')
    const { skillCount, fileCount } = parseSyncCount(data.stdout || '')
    await refreshTargets([targetPath])
    toast.success(`同步 ${getTargetLabel(targetPath)}: ${skillCount} skill · ${fileCount} 文件`)
  } catch (e) {
    toast.error(`同步失败: ${e.message}`)
  } finally {
    syncingInTarget.value = false
  }
}

async function installProjectSkill(skillName, targetPath) {
  installingSkill.value = skillName
  try {
    const data = await executeSync(targetPath, { skills: [skillName] })
    if (!data?.success) throw new Error(data?.stderr || '安装失败')
    const { fileCount } = parseSyncCount(data.stdout || '')
    await refreshTargets([targetPath])
    toast.success(`已安装 ${skillName} → ${getTargetLabel(targetPath)} (${fileCount} 文件)`)
  } catch (e) {
    toast.error(`安装失败: ${e.message}`)
  } finally {
    installingSkill.value = null
  }
}

async function installProjectAll(proj) {
  syncing.value = true
  syncingProjectId.value = proj.id
  let totalFiles = 0
  let totalSkills = 0
  try {
    for (const t of (proj.targets || [])) {
      const data = await executeSync(t)
      if (!data?.success) throw new Error(data?.stderr || '安装失败')
      const { skillCount, fileCount } = parseSyncCount(data.stdout || '')
      totalFiles += fileCount
      totalSkills += skillCount
    }
    await refreshTargets(proj.targets || [])
    toast.success(`安装完成: ${totalSkills} 个 skill · ${totalFiles} 个文件`)
  } catch (e) {
    toast.error('安装失败: ' + e.message)
  } finally {
    syncing.value = false
    syncingProjectId.value = null
  }
}

function getTargetLabel(targetPath) {
  const configured = allTargets.value.find(t => t.path === targetPath)
  if (configured) return configured._label || configured.label || configured.name
  const parts = targetPath.replace(/\/+$/, '').split('/')
  return parts[parts.length - 1] || targetPath
}

function formatDisplayPath(targetPath, relPath = null) {
  return formatAgentDisplayPath(targetPath, relPath)
}

function projectSkills(proj) {
  // Return skills that are relevant to this project (installed in any project target)
  const skillSet = new Set()
  for (const t of (proj.targets || [])) {
    for (const skill of skills.value) {
      if (getProjectCellStatus(skill.name, t) !== 'none') {
        skillSet.add(skill.name)
      }
    }
  }
  // If nothing installed, show first few available skills for context
  if (!skillSet.size) {
    skills.value.slice(0, 8).forEach(s => skillSet.add(s.name))
  }
  return skills.value.filter(s => skillSet.has(s.name))
}

function getProjectSkillSummary(skillName, proj) {
  let installed = 0
  let changed = 0
  const totalTargets = (proj.targets || []).length
  for (const t of (proj.targets || [])) {
    const st = getProjectCellStatus(skillName, t)
    if (st === 'unchanged') installed++
    else if (st === 'changed') changed++
    else if (st !== 'none') installed++
  }
  if (installed === 0) return ''
  if (changed) return `${installed}/${totalTargets}`
  if (installed === totalTargets) return `${totalTargets}/${totalTargets}`
  return `${installed}/${totalTargets}`
}

function getProjectCellStatus(skillName, targetPath) {
  const agents = discoveredProjectMap.value[targetPath]?.agent_dirs || []
  if (agents.length) {
    let anyInstalled = false
    let anyChanged = false
    for (const d of agents) {
      const st = statusMap.value[skillName]?.[d.path]
      if (st === 'unchanged') anyInstalled = true
      else if (st === 'changed') { anyInstalled = true; anyChanged = true }
      else if (st === 'missing') anyInstalled = true
    }
    if (anyChanged) return 'changed'
    if (anyInstalled) return 'unchanged'
    return 'none'
  }
  // No agent dirs — check if installed directly at target root
  const st = statusMap.value[skillName]?.[targetPath]
  if (st) return st
  return 'none'
}

function getProjectCellLabel(skillName, targetPath) {
  const st = getProjectCellStatus(skillName, targetPath)
  const map = { unchanged: '已同步', changed: '有变更', missing: '缺失', none: '-' }
  return map[st] || '-'
}

function getProjectCellTooltip(skillName, targetPath) {
  const agents = discoveredProjectMap.value[targetPath]?.agent_dirs || []
  if (!agents.length) {
    const st = statusMap.value[skillName]?.[targetPath]
    return st ? `${targetPath}: ${st}` : '未安装'
  }
  const parts = agents.map(d => {
    const st = statusMap.value[skillName]?.[d.path] || '未安装'
    return `${d.agent}: ${st}`
  })
  return parts.join('\n')
}

function resolveActualTarget(skillName, targetPath) {
  // Find the actual agent dir path for this skill+target combination
  const agents = discoveredProjectMap.value[targetPath]?.agent_dirs || []
  if (agents.length) {
    // Prefer an agent dir where this skill is installed
    for (const d of agents) {
      if (statusMap.value[skillName]?.[d.path]) return d.path
    }
    // Fallback: first agent dir
    return agents[0].path
  }
  return targetPath
}

function onProjectCellClick(skillName, targetPath, proj) {
  const actualTarget = resolveActualTarget(skillName, targetPath)
  diffSkill.value = skillName
  diffTarget.value = actualTarget
  showDiff.value = true
  diffLoading.value = true
  diffError.value = null
  diffFiles.value = []
  diffSummary.value = {}
  selectedDiffFile.value = null
  fetchSkillDiff(skillName, actualTarget)
    .then(data => {
      diffFiles.value = data.files || []
      diffSummary.value = data.summary || {}
    })
    .catch(e => { diffError.value = e.message })
    .finally(() => { diffLoading.value = false })
}

let projectsLoadPromise = null

async function loadProjects() {
  if (projectsLoadPromise) return projectsLoadPromise
  projectsLoading.value = true
  projectsLoadPromise = (async () => {
    try {
      projects.value = await fetchProjects()
      const allTargets = projects.value.flatMap(p => p.targets || [])
      const results = await Promise.allSettled(
        allTargets.map(t => fetchDiscover(t).then(d => ({ target: t, data: d })))
      )
      for (const r of results) {
        if (r.status === 'fulfilled') {
          discoveredProjectMap.value[r.value.target] = r.value.data
        }
      }
    } catch { /* silently ignore */ }
    finally {
      projectsLoading.value = false
      projectsLoadPromise = null
    }
  })()
  return projectsLoadPromise
}

const searchQuery = ref('')
const statusFilter = ref(null)

const statusFilters = [
  { key: null, label: '全部' },
  { key: 'unchanged', label: '已同步' },
  { key: 'changed', label: '已变更' },
  { key: 'missing', label: '缺失' },
  { key: 'not-installed', label: '未安装' },
]

// Diff modal state
const showDiff = ref(false)
const diffSkill = ref('')
const diffTarget = ref('')
const diffFiles = ref([])
const diffSummary = ref({})
const diffLoading = ref(false)
const diffError = ref(null)

// File preview state
const selectedDiffFile = ref(null)
const previewSource = ref('')
const previewTarget = ref('')
const previewLoading = ref(false)
const previewError = ref('')

const hasChanges = computed(() => {
  return diffSummary.value.added > 0 || diffSummary.value.modified > 0 || diffSummary.value.removed > 0
})

const changedFiles = computed(() => {
  return diffFiles.value.filter(f => f.status !== 'unchanged')
})

// Add target modal state
const addTargetOpen = ref(false)
const addTargetSaving = ref(false)
const addTargetError = ref('')
const newTarget = ref({ name: '', path: '', agentKind: null })
const pickingDirectory = ref(false)
const builtinCatalog = ref([])

const quickPresets = computed(() => pickQuickPresets(builtinCatalog.value, 8))

async function loadBuiltinCatalog() {
  try {
    const data = await fetchBuiltinAgents(true)
    builtinCatalog.value = data.agents || []
  } catch {
    // non-fatal — manual target form stays usable
  }
}

function openAddTargetModal() {
  addTargetError.value = ''
  newTarget.value = { name: '', path: '', agentKind: null }
  addTargetOpen.value = true
  if (!builtinCatalog.value.length) {
    loadBuiltinCatalog()
  }
}

function applyAgentPreset(agent) {
  newTarget.value = buildPresetDraft(agent)
  addTargetError.value = ''
}

async function pickDirectory() {
  if (pickingDirectory.value) return
  pickingDirectory.value = true
  addTargetError.value = ''
  try {
    const result = await selectWorkspaceDirectory(newTarget.value.path || null)
    if (!result.cancelled && result.path) {
      newTarget.value.path = result.path
      newTarget.value.agentKind = null
    }
  } catch (e) {
    if (e?.code === 'directory_picker_unavailable' || e?.status === 501) {
      addTargetError.value = '当前环境不支持系统目录选择器，请直接手动输入绝对路径或 ~/ 开头路径'
    } else {
      addTargetError.value = e?.message || '无法打开目录选择器，请手动输入路径'
    }
  } finally {
    pickingDirectory.value = false
  }
}

onMounted(() => {
  loadAll()
  loadProjects()
  document.addEventListener('click', onDocumentClick)
})

onUnmounted(() => {
  unsubscribeTargets()
  document.removeEventListener('click', onDocumentClick)
})

// Watch ?skill=X — switch to target containing this skill
// Load project target statuses when switching to project view
// Also watch projects.length so statuses load when projects arrive after view switch
watch([activeView, () => projects.value.length], async ([view]) => {
  if (view === 'projects' && projects.value.length) {
    for (const p of projects.value) {
      for (const t of (p.targets || [])) {
        if (!Object.values(statusMap.value).some(m => m[t] !== undefined)) {
          await loadStatusForTarget(t)
        }
      }
    }
  }
})

watch(() => route.query.skill, (skillName) => {
  if (skillName && targets.value.length) {
    for (const t of targets.value) {
      const hasSkill = skills.value.some(s => s.name === skillName)
      if (hasSkill) {
        activeTarget.value = t.path
        break
      }
    }
  }
}, { immediate: true })

watch(() => route.query.onboarding, (value) => {
  if (value !== 'target') return
  activeView.value = 'targets'
  openAddTargetModal()
  const query = { ...route.query }
  delete query.onboarding
  router.replace({ query })
}, { immediate: true })

// Sync route query ↔ view state
watch(() => route.query.view, (view) => {
  if (view === 'targets' || view === 'projects') {
    activeView.value = view
  }
}, { immediate: true })

watch([() => route.query.project, () => projects.value.length], ([projectId]) => {
  if (projectId && projects.value.length) {
    expandedProject.value = projectId
  }
}, { immediate: true })

watch(activeView, (view) => {
  const current = route.query.view
  if (current !== view) {
    router.replace({ query: { ...route.query, view } })
  }
})

watch(expandedProject, (projId) => {
  const current = route.query.project
  if (current !== projId) {
    const query = { ...route.query }
    if (projId) {
      query.project = projId
    } else {
      delete query.project
    }
    router.replace({ query })
  }
})

// ---- Data Loading ----

async function loadAll(fullRefresh = false) {
  loading.value = true
  error.value = null
  try {
    const [config, data] = await Promise.all([
      fetchSyncConfig(),
      fullRefresh ? fetchSkillsRefresh() : fetchSkills(),
    ])

    skills.value = data.skills || []
    targets.value = (config.targets || [])
      .map(t => normalizeTarget(t))
      .filter(Boolean)

    if (targets.value.length) {
      if (!activeTarget.value || !targets.value.find(t => t.path === activeTarget.value)) {
        activeTarget.value = targets.value[0].path
      }
      // Only load status for the active target on mount (lazy load the rest)
      await loadStatusForTarget(activeTarget.value)
    } else {
      activeTarget.value = ''
    }
    syncToBridge()
  } catch (e) {
    error.value = '加载失败: ' + e.message
  } finally {
    loading.value = false
  }
}

/** Load status for a single target and merge into statusMap */
async function loadStatusForTarget(targetName) {
  try {
    const rows = await fetchSyncStatus(targetName)
    // Clear stale entries for this target before merging fresh data
    // (so uninstalled skills no longer appear as installed)
    for (const skillName of Object.keys(statusMap.value)) {
      if (statusMap.value[skillName]?.[targetName] !== undefined) {
        delete statusMap.value[skillName][targetName]
      }
      // Also clear 'custom' entries (raw paths with no agent dirs get reported as 'custom')
      if (statusMap.value[skillName]?.custom !== undefined) {
        delete statusMap.value[skillName].custom
      }
    }
    // Merge fresh status rows
    if (Array.isArray(rows)) {
      for (const row of rows) {
        statusMap.value[row.name] = statusMap.value[row.name] || {}
        // Remap 'custom' target key to the actual queried path so lookups work
        const targetKey = row.target === 'custom' ? targetName : row.target
        statusMap.value[row.name][targetKey] = row.status
      }
    }
    // Merge fresh status rows into shared bridge without wiping unrelated targets
    mergeTargetStatus(targetName, rows, targets.value)
  } catch {
    // silently ignore — status stays stale
  }
}

/** Lightweight status-only refresh — only for active target */
async function refreshStatus() {
  if (activeTarget.value) {
    await loadStatusForTarget(activeTarget.value)
  }
}

async function refreshTargets(targetNames) {
  const uniqueTargets = [...new Set((targetNames || []).filter(Boolean))]
  await Promise.all(uniqueTargets.map(t => loadStatusForTarget(t)))
  syncToBridge()
}

/** Switch active target, lazy-load status if not cached */
async function switchTarget(targetName) {
  activeTarget.value = targetName
  // Check if we already have status data for ANY skill in this target
  const hasStatus = Object.values(statusMap.value).some(m => m[targetName] !== undefined)
  if (!hasStatus) {
    await loadStatusForTarget(targetName)
  }
}

// ---- Status Helpers ----

function getCellStatus(skillName, targetName) {
  const s = statusMap.value[skillName]?.[targetName]
  if (s) return s
  return 'not-installed'
}

function isSkillInstalled(skillName, targetName) {
  const status = statusMap.value[skillName]?.[targetName]
  return status !== undefined && status !== 'missing'
}

// ---- Computed: All Targets (config + project) ----

const allTargets = computed(() => {
  return targets.value.map(t => ({ ...t, _label: t.label || t.name, _project: false }))
})

const activeTargetObj = computed(() => {
  return allTargets.value.find(t => t.path === activeTarget.value) || null
})

const activeTargetShort = computed(() => {
  const t = activeTargetObj.value
  return t ? (t._label || t.label || t.name) : activeTarget.value
})

const activeTargetLabel = computed(() => {
  const t = activeTargetObj.value
  return t ? `${t._label || t.label || t.name} · ${formatDisplayPath(t.path)}` : formatDisplayPath(activeTarget.value)
})

// ---- Computed: Active Target Skills ----

const installedSkills = computed(() => {
  if (!activeTarget.value) return []
  let list = skills.value
    .filter(s => isSkillInstalled(s.name, activeTarget.value))
    .map(s => ({
      key: s.path || s.skillFilePath || s.name,
      name: s.name,
      status: getCellStatus(s.name, activeTarget.value),
    }))
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(s => s.name.toLowerCase().includes(q))
  }
  if (statusFilter.value) {
    list = list.filter(s => s.status === statusFilter.value)
  }
  return list
})

const availableSkills = computed(() => {
  if (!activeTarget.value) return []
  let list = skills.value
    .filter(s => !isSkillInstalled(s.name, activeTarget.value))
    .map(s => ({ key: s.path || s.skillFilePath || s.name, name: s.name }))
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(s => s.name.toLowerCase().includes(q))
  }
  if (statusFilter.value === 'not-installed') return list
  if (statusFilter.value !== null) return []
  return list
})

// ---- Install / Uninstall ----

async function installSkill(skillName) {
  installingSkill.value = skillName
  error.value = null
  try {
    const result = await executeSync(activeTarget.value, { skills: [skillName] })
    if (!result.success) throw new Error(result.stderr || 'sync failed')
    await refreshStatus()
  } catch (e) {
    error.value = `安装 ${skillName}: ${e.message}`
  } finally {
    installingSkill.value = null
  }
}

async function uninstallSkill(skillName) {
  removingSkill.value = skillName
  error.value = null
  try {
    const result = await removeSkillApi(skillName, activeTarget.value)
    if (!result.success) throw new Error(result.error)
    await refreshStatus()
  } catch (e) {
    error.value = `卸载 ${skillName}: ${e.message}`
  } finally {
    removingSkill.value = null
  }
}

// ---- Sync All Confirmation ----

const syncAllConfirmOpen = ref(false)
const syncAllRunning = ref(false)
const syncAllError = ref('')
const syncAllDone = ref(0)
const syncAllTotal = ref(0)
const syncAllCurrent = ref('')
const syncAllProgress = computed(() => syncAllTotal.value ? Math.round(syncAllDone.value / syncAllTotal.value * 100) : 0)

/** Get installed skills and counts for a given target key.
 *  Returns { names, total, changed } — changed = needs sync (has local modifications). */
function getInstalledSkillsForTarget(targetKey) {
  const seen = new Map() // skillName → 'unchanged'|'changed'|'missing'
  // Direct lookup (for named targets and raw paths without agent dirs)
  for (const skillName of Object.keys(statusMap.value)) {
    const st = statusMap.value[skillName]?.[targetKey]
    if (st) seen.set(skillName, st)
  }
  // Also check agent dir paths (for project targets that have discovered agent dirs)
  const agents = discoveredProjectMap.value[targetKey]?.agent_dirs || []
  for (const d of agents) {
    for (const skillName of Object.keys(statusMap.value)) {
      const st = statusMap.value[skillName]?.[d.path]
      if (st) seen.set(skillName, st)
    }
  }
  const names = [...seen.keys()]
  const changed = names.filter(n => seen.get(n) === 'changed')
  return { names, total: names.length, changed: changed.length, changedNames: changed }
}

const syncAllNamedTargets = computed(() => {
  return targets.value.map(t => {
    const info = getInstalledSkillsForTarget(t.path)
    return { ...t, skillList: info.names, skillCount: info.total, changedCount: info.changed, changedNames: info.changedNames }
  })
})

const syncAllProjectTargets = computed(() => {
  // Group targets by project, compute union of installed skills per project
  const projectGroups = new Map()
  for (const p of projects.value) {
    const unionMap = new Map() // skillName → 'unchanged'|'changed'|'missing'
    const targets = []
    for (const t of (p.targets || [])) {
      const info = getInstalledSkillsForTarget(t)
      // Track each skill's worst status in the union (changed > missing > unchanged)
      for (let i = 0; i < info.names.length; i++) {
        const name = info.names[i]
        const st = info.changedNames.includes(name) ? 'changed' : 'unchanged'
        const existing = unionMap.get(name)
        if (!existing || (st === 'changed')) unionMap.set(name, st)
      }
      targets.push({ path: t, skillList: info.names, skillCount: info.total, changedCount: info.changed, changedNames: info.changedNames })
    }
    const unionSkills = [...unionMap.keys()]
    const unionChangedNames = [...unionMap.entries()].filter(([, s]) => s === 'changed').map(([n]) => n)
    projectGroups.set(p.id, {
      projectName: p.name,
      projectId: p.id,
      targets,
      unionSkills,
      unionCount: unionSkills.length,
      unionChanged: unionChangedNames.length,
      unionChangedNames,
    })
  }
  return projectGroups
})

const totalProjectTargetCount = computed(() => {
  let count = 0
  for (const [, group] of syncAllProjectTargets.value) {
    count += group.targets.length
  }
  return count
})

function isTargetStatusLoaded(targetKey) {
  // Check if any skill has status data for this target key
  for (const skillName of Object.keys(statusMap.value)) {
    if (statusMap.value[skillName]?.[targetKey] !== undefined) {
      return true
    }
  }
  return false
}

const syncAllPreloading = ref(false)

async function openSyncAllConfirm() {
  syncAllError.value = ''
  syncAllDone.value = 0
  syncAllTotal.value = 0
  syncAllCurrent.value = ''

  // Ensure projects are loaded before computing the sync plan
  if (!projects.value.length) {
    syncAllPreloading.value = true
    syncAllConfirmOpen.value = true
    await loadProjects()
  }

  if (!targets.value.length && !projects.value.length) {
    syncAllPreloading.value = false
    syncAllConfirmOpen.value = false
    toast.warn('没有可同步的目标目录')
    return
  }

  // Eagerly load status for any target that hasn't been fetched yet
  const toLoad = []
  for (const t of targets.value) {
    if (!isTargetStatusLoaded(t.path)) {
      toLoad.push(loadStatusForTarget(t.path))
    }
  }
  for (const p of projects.value) {
    for (const t of (p.targets || [])) {
      if (!isTargetStatusLoaded(t)) {
        toLoad.push(loadStatusForTarget(t))
      }
    }
  }

  syncAllPreloading.value = true
  syncAllConfirmOpen.value = true
  if (toLoad.length) {
    await Promise.all(toLoad)
  }
  syncAllPreloading.value = false
}

async function executeSyncAll() {
  syncAllRunning.value = true
  syncAllError.value = ''

  // Build sync plan: only sync skills with 'changed' status
  const plan = []
  // Named targets: sync changed skills only
  for (const t of syncAllNamedTargets.value) {
    if (t.changedCount > 0) {
      plan.push({ key: t.path, label: t.label || t.name, skills: t.changedNames })
    }
  }
  // Project targets: sync changed union skills for each target
  for (const [, group] of syncAllProjectTargets.value) {
    if (group.unionChanged > 0) {
      for (const t of group.targets) {
        plan.push({ key: t.path, label: `${group.projectName}/${getTargetLabel(t.path)}`, skills: group.unionChangedNames })
      }
    }
  }

  if (!plan.length) {
    syncAllRunning.value = false
    syncAllConfirmOpen.value = false
    toast.info('所有目标均已同步，无需更新')
    return
  }

  syncAllTotal.value = plan.length
  syncAllDone.value = 0

  let hasError = false
  for (const item of plan) {
    syncAllCurrent.value = item.label
    try {
      const result = await executeSync(item.key, item.skills.length ? { skills: item.skills } : {})
      if (!result.success) throw new Error(result.stderr || 'sync failed')
    } catch (e) {
      syncAllError.value = `${item.label}: ${e.message}`
      hasError = true
    }
    syncAllDone.value++
  }

  syncAllRunning.value = false
  syncAllCurrent.value = ''

  await refreshTargets(plan.map(item => item.key))

  syncAllConfirmOpen.value = false

  if (hasError) {
    toast.warn('部分目标同步失败')
  } else {
    const totalSkills = plan.reduce((sum, item) => sum + item.skills.length, 0)
    toast.success(`全部同步完成: ${plan.length} 个目标 · ${totalSkills} 个 skill`)
  }
}

function syncToBridge() {
  for (const [skillName, targetEntries] of Object.entries(statusMap.value)) {
    bridgeState.statusMap[skillName] = {
      ...(bridgeState.statusMap[skillName] || {}),
      ...targetEntries,
    }
  }
  bridgeState.targets = targets.value
    .map(t => normalizeTarget(t))
    .filter(Boolean)
    .map(t => ({ ...t, _project: false }))
}

// ---- Sync Actions ----

async function syncActiveTarget() {
  syncingInTarget.value = true
  error.value = null
  try {
    const result = await executeSync(activeTarget.value)
    if (!result.success) throw new Error(result.stderr || 'sync failed')
    await refreshStatus()
  } catch (e) {
    error.value = '同步失败: ' + e.message
  } finally {
    syncingInTarget.value = false
  }
}

async function syncOneSkill(skillName) {
  syncingSkill.value = skillName
  error.value = null
  try {
    const result = await executeSync(activeTarget.value, { skills: [skillName] })
    if (!result.success) throw new Error(result.stderr || 'sync failed')
    await refreshStatus()
  } catch (e) {
    error.value = `同步 ${skillName}: ${e.message}`
  } finally {
    syncingSkill.value = null
  }
}

// ---- Diff ----

function openDiff(skillName) {
  showDiff.value = true
  diffSkill.value = skillName
  diffTarget.value = activeTarget.value
  diffLoading.value = true
  diffError.value = null
  diffFiles.value = []
  diffSummary.value = {}
  selectedDiffFile.value = null
  previewSource.value = ''
  previewTarget.value = ''
  previewError.value = ''
  fetchSkillDiff(skillName, activeTarget.value)
    .then(data => {
      diffFiles.value = data.files || []
      diffSummary.value = data.summary || {}
    })
    .catch(e => {
      diffError.value = e.message
    })
    .finally(() => {
      diffLoading.value = false
    })
}

// ---- File Preview ----

async function openFilePreview(file) {
  selectedDiffFile.value = file.path
  previewLoading.value = true
  previewError.value = ''

  try {
    const skillName = diffSkill.value
    const targetName = diffTarget.value
    const filePath = file.path

    let repoPromise = Promise.resolve('')
    let targetPromise = Promise.resolve('')

    // removed: exists in source, not in target → fetch source only
    // added: exists in target, not in source → fetch target only
    // modified: both exist → fetch both

    if (file.status !== 'added') {
      repoPromise = fetchSkillFile(skillName, filePath)
        .then(data => data.exists === false ? '(文件不存在)' : (data.content || ''))
    }

    if (file.status !== 'removed') {
      targetPromise = fetchTargetFile(skillName, targetName, filePath)
        .then(data => data.exists === false ? '(文件不存在)' : (data.content || ''))
    }

    const [repo, target] = await Promise.all([repoPromise, targetPromise])
    previewSource.value = repo
    previewTarget.value = target
  } catch (e) {
    previewError.value = e.message
  } finally {
    previewLoading.value = false
  }
}

function closeFilePreview() {
  selectedDiffFile.value = null
  previewSource.value = ''
  previewTarget.value = ''
  previewError.value = ''
}

// ---- Add Target ----

async function addTarget() {
  if (!newTarget.value.name || !newTarget.value.path) {
    addTargetError.value = '名称和路径不能为空'
    return
  }
  addTargetSaving.value = true
  addTargetError.value = ''
  try {
    const extra = newTarget.value.agentKind ? { agentKind: newTarget.value.agentKind } : {}
    await addSyncTarget(newTarget.value.name, newTarget.value.path, extra)
    addTargetOpen.value = false
    newTarget.value = { name: '', path: '', agentKind: null }
    await loadAll(true)
    loadBuiltinCatalog()
  } catch (e) {
    addTargetError.value = e.message
  } finally {
    addTargetSaving.value = false
  }
}

// ---- Target Files Management ----

const targetFilesOpen = ref(false)
const targetFilesTarget = ref('')
const targetFilesData = ref(null)
const targetFilesLoading = ref(false)
const targetFilesError = ref('')
const removingSkill = ref(null)

const { show: showSkillDetail } = useSkillDetail()

const confirmRemoveOpen = ref(false)
const confirmRemoveSkill = ref('')
const confirmRemoveChecked = ref(false)
const confirmRemoveError = ref('')

// ── Target management state ──

const targetDropdownOpen = ref(null) // target path or null
const renameTargetOpen = ref(false)
const renameTargetLabel = ref('')
const renameTargetOldPath = ref('')
const renameTargetNewPath = ref('')
const renameTargetSaving = ref(false)
const renameTargetError = ref('')

const deleteTargetOpen = ref(false)
const deleteTargetLabel = ref('')
const deleteTargetPath = ref('')
const deleteTargetSaving = ref(false)
const deleteTargetError = ref('')

// ── Built-in agent catalog & discovery state ──

const managedCount = computed(() => {
  if (!targetFilesData.value?.skills) return 0
  return targetFilesData.value.skills.filter(s => s.managed).length
})

const unmanagedCount = computed(() => {
  if (!targetFilesData.value?.skills) return 0
  return targetFilesData.value.skills.filter(s => !s.managed).length
})

async function openTargetFiles() {
  targetFilesOpen.value = true
  targetFilesTarget.value = activeTarget.value
  targetFilesLoading.value = true
  targetFilesError.value = ''
  targetFilesData.value = null
  try {
    targetFilesData.value = await fetchTargetSkills(activeTarget.value)
  } catch (e) {
    targetFilesError.value = e.message
  } finally {
    targetFilesLoading.value = false
  }
}

async function removeSkillFromTarget(skillName) {
  removingSkill.value = skillName
  try {
    const result = await removeSkillApi(skillName, targetFilesTarget.value)
    if (!result.success) throw new Error(result.error)
    // Refresh the list and status
    targetFilesData.value = null
    await openTargetFiles()
    await refreshStatus()
  } catch (e) {
    targetFilesError.value = `删除 ${skillName}: ${e.message}`
  } finally {
    removingSkill.value = null
  }
}

function confirmRemoveUnmanaged(skillName) {
  confirmRemoveSkill.value = skillName
  confirmRemoveChecked.value = false
  confirmRemoveError.value = ''
  confirmRemoveOpen.value = true
}

async function doRemoveUnmanaged() {
  removingSkill.value = confirmRemoveSkill.value
  confirmRemoveError.value = ''
  try {
    const result = await removeSkillApi(confirmRemoveSkill.value, targetFilesTarget.value, true)
    if (!result.success) throw new Error(result.error)
    confirmRemoveOpen.value = false
    targetFilesData.value = null
    await openTargetFiles()
    await refreshStatus()
  } catch (e) {
    confirmRemoveError.value = e.message
  } finally {
    removingSkill.value = null
  }
}

// ── Target management ──

function toggleTargetDropdown(targetPath) {
  targetDropdownOpen.value = targetDropdownOpen.value === targetPath ? null : targetPath
}

function closeTargetDropdown() {
  targetDropdownOpen.value = null
}

function onDocumentClick(e) {
  if (!e.target.closest('.target-tab-wrapper')) {
    closeTargetDropdown()
  }
}

const renameInputRef = ref(null)

function openRenameTarget(t) {
  closeTargetDropdown()
  renameTargetOpen.value = true
  renameTargetLabel.value = t.label || t.name
  renameTargetOldPath.value = t.path
  renameTargetNewPath.value = t.path
  renameTargetError.value = ''
  renameTargetSaving.value = false
  nextTick(() => {
    renameInputRef.value?.focus()
    renameInputRef.value?.select()
  })
}

async function doRenameTarget() {
  const newPath = renameTargetNewPath.value.trim()
  if (!newPath || newPath === renameTargetOldPath.value) {
    renameTargetOpen.value = false
    return
  }
  renameTargetSaving.value = true
  renameTargetError.value = ''
  try {
    await renameSyncTarget(renameTargetOldPath.value, newPath)
    renameTargetOpen.value = false
    if (activeTarget.value === renameTargetOldPath.value) {
      activeTarget.value = newPath
    }
    await loadAll(true)
    toast.success(`已更新目标路径: ${renameTargetLabel.value}`)
  } catch (e) {
    if (e.status === 409) {
      renameTargetError.value = `路径 "${newPath}" 已存在`
    } else {
      renameTargetError.value = e.message
    }
  } finally {
    renameTargetSaving.value = false
  }
}

function openDeleteTarget(t) {
  closeTargetDropdown()
  deleteTargetOpen.value = true
  deleteTargetLabel.value = t.label || t.name
  deleteTargetPath.value = t.path
  deleteTargetError.value = ''
  deleteTargetSaving.value = false
}

async function doDeleteTarget() {
  deleteTargetSaving.value = true
  deleteTargetError.value = ''
  try {
    await removeSyncTarget(deleteTargetPath.value)
    deleteTargetOpen.value = false
    if (activeTarget.value === deleteTargetPath.value) {
      activeTarget.value = targets.value.find(t => t.path !== deleteTargetPath.value)?.path || ''
    }
    await loadAll(true)
    toast.success(`已删除目标: ${deleteTargetLabel.value}`)
  } catch (e) {
    deleteTargetError.value = e.message
  } finally {
    deleteTargetSaving.value = false
  }
}

// ── Built-in agent catalog & actions ──

async function promoteBuiltinTarget(t) {
  closeTargetDropdown()
  try {
    await addSyncTarget(t.label || t.name, t.path, t.agentKind ? { agentKind: t.agentKind } : {})
    await loadAll(true)
    loadBuiltinCatalog()
    toast.success(`已保存为自定义目标: ${t.label || t.name}`)
  } catch (e) {
    toast.error(`保存失败: ${e.message}`)
  }
}

async function hideBuiltinTarget(t) {
  closeTargetDropdown()
  if (!t.agentKind) return
  try {
    await setBuiltinAgentEnabled(t.agentKind, false)
    if (activeTarget.value === t.path) {
      activeTarget.value = targets.value.find(item => item.path !== t.path)?.path || ''
    }
    await loadAll(true)
    loadBuiltinCatalog()
    toast.success(`已移出目标清单: ${t.label || t.name}`)
  } catch (e) {
    toast.error(`移出失败: ${e.message}`)
  }
}
</script>

<style scoped>
.sync-manager {
  width: 100%;
}

.sync-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--sr-space-4);
  flex-wrap: wrap;
  gap: var(--sr-space-2);
}

.sync-header-left {
  display: flex;
  align-items: center;
  gap: var(--sr-space-3);
}

.sync-title {
  font-size: var(--sr-text-page-title);
  font-weight: var(--sr-weight-semibold);
  letter-spacing: -0.015em;
  line-height: 1.4;
  color: var(--sr-text-primary);
}

.sync-count {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
  background: var(--sr-content-bg);
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-secondary);
}

.sync-header-actions {
  display: flex;
  gap: var(--sr-space-2);
  align-items: center;
  flex-wrap: wrap;
}

.project-select {
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-control-bg);
  color: var(--sr-text-primary);
  font-size: var(--sr-text-compact);
  font-family: inherit;
  height: var(--sr-control-height-sm);
  cursor: pointer;
}

.project-select:focus {
  outline: none;
  box-shadow: var(--sr-control-focus-shadow);
}

.sync-error {
  color: var(--sr-role-rose-ink);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-medium);
  margin-bottom: var(--sr-space-3);
  padding: 10px 14px;
  background: var(--sr-role-rose-surface);
  border-radius: var(--sr-radius-md);
}

.sync-loading,
.sync-empty {
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-card-title);
  padding: var(--sr-space-5);
  text-align: center;
}

/* ---- Target Tabs (Borderless Workbench Segmented Bar) ---- */
.target-tabs-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sr-space-3);
  margin-bottom: var(--sr-space-4);
}

.target-tabs {
  display: flex;
  gap: 4px;
  background: var(--sr-content-bg);
  border-radius: var(--sr-radius-md);
  padding: 4px;
  border: none;
  flex-wrap: wrap;
}

.target-tab {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: var(--sr-text-secondary);
  font-size: var(--sr-text-compact);
  border-radius: var(--sr-radius-sm);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
  text-align: left;
  min-width: 100px;
}

.target-tab-wrapper .target-tab {
  border-radius: var(--sr-radius-sm);
  min-width: 80px;
}

.target-tab:not(.target-tab--active):hover {
  background: var(--sr-bg-hover);
  color: var(--sr-text-primary);
}

.target-tab--active,
.target-tab-wrapper .target-tab--active {
  background: var(--sr-bg-floating);
  color: var(--sr-text-primary);
  font-weight: var(--sr-weight-semibold);
  box-shadow: var(--sr-shadow-sm);
}

.target-tab-header {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.target-tab-name {
  font-size: var(--sr-text-card-title);
  font-weight: var(--sr-weight-semibold);
  color: inherit;
}

.target-tab-badge {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 6px;
  border-radius: var(--sr-radius-badge);
  background: var(--sr-control-bg);
  color: var(--sr-text-secondary);
  font-size: var(--sr-text-micro);
  line-height: 1;
  font-weight: var(--sr-weight-semibold);
}

.target-tab-badge--shared {
  background: var(--sr-role-blue-surface);
  color: var(--sr-role-blue-ink);
}

.sync-empty-targets {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--sr-space-2);
  padding: var(--sr-space-6) var(--sr-space-5);
  border: none;
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  text-align: center;
}

.sync-empty-targets-title {
  margin: 0;
  font-size: var(--sr-text-body);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
}

.sync-empty-targets-desc {
  margin: 0;
  max-width: 400px;
  font-size: var(--sr-text-card-title);
  color: var(--sr-text-secondary);
}

.sync-empty-targets-actions {
  display: flex;
  gap: var(--sr-space-2);
  margin-top: var(--sr-space-2);
}

.preset-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.preset-label {
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-bold);
  color: var(--sr-text-secondary);
}

.preset-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preset-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  padding: 0 10px;
  border: none;
  border-radius: var(--sr-radius-pill);
  background: var(--sr-control-bg);
  color: var(--sr-text-primary);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-medium);
  font-family: inherit;
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
}

.preset-chip:hover {
  background: var(--sr-control-bg-hover);
}

.preset-chip--active {
  background: var(--sr-action-bg-selected);
  color: var(--sr-accent);
  font-weight: var(--sr-weight-semibold);
}

.preset-chip-path {
  font-size: var(--sr-text-meta);
  color: var(--sr-text-tertiary);
  font-family: var(--sr-font-mono);
}

.target-tab-path {
  font-size: var(--sr-text-meta);
  font-family: var(--sr-font-mono);
  color: var(--sr-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 170px;
}

.target-tab-actions {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  flex-shrink: 0;
  padding-top: var(--sr-space-1);
}

/* ---- Config Panel ---- */
.config-card {
  margin-bottom: var(--sr-space-5);
}

.config-body {
  display: flex;
  flex-direction: column;
  gap: var(--sr-space-2);
}

.config-skill-row {
  display: flex;
  align-items: center;
  gap: var(--sr-space-3);
  padding: 8px 10px;
  border-radius: var(--sr-radius-sm);
  flex-wrap: wrap;
}

.config-skill-row:nth-child(even) {
  background: var(--sr-table-stripe);
}

.config-skill-name {
  min-width: 180px;
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
}

.config-checkbox {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--sr-text-compact);
  color: var(--sr-text-secondary);
  cursor: pointer;
}

.config-actions {
  display: flex;
  gap: var(--sr-space-2);
  justify-content: flex-end;
  padding-top: var(--sr-space-3);
}

/* ---- Search & Filter ---- */
.search-bar {
  display: flex;
  gap: var(--sr-space-3);
  align-items: center;
  margin-bottom: var(--sr-space-4);
  flex-wrap: wrap;
}

.search-input {
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-control-bg);
  color: var(--sr-text-primary);
  font-size: var(--sr-text-compact);
  font-family: inherit;
  width: 200px;
  height: var(--sr-control-height-sm);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              box-shadow 140ms var(--sr-ease-standard);
}

.search-input:focus {
  outline: none;
  background: var(--sr-control-bg-active);
  box-shadow: var(--sr-control-focus-shadow);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              box-shadow 180ms var(--sr-ease-standard);
}

.filter-btns {
  display: flex;
  gap: 4px;
}

.filter-btn {
  height: 28px;
  padding: 0 10px;
  border: none;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-control-bg);
  color: var(--sr-text-secondary);
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-medium);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
}

.filter-btn:not(.filter-btn--active):hover {
  background: var(--sr-control-bg-hover);
  color: var(--sr-text-primary);
}

.filter-btn--active {
  background: var(--sr-action-bg-selected);
  color: var(--sr-accent);
  font-weight: var(--sr-weight-semibold);
}

/* ---- Skill List Card ---- */
.skill-list-card {
  margin-bottom: var(--sr-space-5);
}

.card-target-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: var(--sr-text-compact);
  font-family: var(--sr-font-mono);
  color: var(--sr-text-tertiary);
  font-weight: var(--sr-weight-regular);
}

.card-target-icon {
  color: var(--sr-text-primary);
}

.skill-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: var(--sr-space-4);
}

.skill-list:last-child {
  margin-bottom: 0;
}

.section-header {
  margin-bottom: var(--qqx-space-md);
}

.section-header h3 {
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-bold);
  color: var(--sr-text-tertiary);
  letter-spacing: 0.02em;
}

/* Borderless rounded tonal rows — zero borders or inset border rings */
.skill-list-row {
  display: flex;
  align-items: center;
  gap: var(--sr-space-3);
  padding: 10px 14px;
  border-radius: var(--qqx-radius-md);
  background: var(--sr-bg-floating);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.skill-list-row:hover,
.skill-list-row:focus-within {
  background: color-mix(in srgb, var(--sr-accent) 8%, var(--sr-bg-floating));
}

.skill-list-name {
  flex: 1;
  font-size: var(--sr-text-body);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
  cursor: pointer;
  transition: color var(--sr-duration-fast) var(--sr-ease-standard);
}

.skill-list-name:hover {
  color: var(--sr-accent);
}

.skill-list-status {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
  flex-shrink: 0;
}

.skill-list-status.unchanged,
.skill-list-status.synced {
  color: var(--sr-role-sage-ink);
  background: var(--sr-role-sage-surface);
}

.skill-list-status.changed,
.skill-list-status.modified {
  color: var(--sr-role-amber-ink);
  background: var(--sr-role-amber-surface);
}

.skill-list-status.missing {
  color: var(--sr-role-rose-ink);
  background: var(--sr-role-rose-surface);
}

.skill-list-status.not-installed {
  color: var(--sr-text-secondary);
  background: var(--sr-control-bg);
}

.skill-list-actions {
  display: flex;
  gap: var(--sr-space-2);
  flex-shrink: 0;
}

/* ---- Diff Summary ---- */
.diff-summary {
  display: flex;
  gap: var(--sr-space-2);
  flex-wrap: wrap;
  margin-bottom: var(--sr-space-3);
}

.diff-stat {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
}

.diff-stat.unchanged {
  background: var(--qqx-diff-unchanged-tag-bg);
  color: var(--qqx-diff-unchanged-tag-text);
}

.diff-stat.added {
  background: var(--qqx-diff-added-tag-bg);
  color: var(--qqx-diff-added-tag-text);
}

.diff-stat.modified {
  background: var(--qqx-diff-modified-tag-bg);
  color: var(--qqx-diff-modified-tag-text);
}

.diff-stat.removed {
  background: var(--qqx-diff-removed-tag-bg);
  color: var(--qqx-diff-removed-tag-text);
}

.diff-file-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.diff-file-row {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  padding: 8px 12px;
  border-radius: var(--sr-radius-sm);
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.diff-file-row:hover {
  background: var(--sr-bg-hover);
}

.diff-file-row.added { background: var(--qqx-diff-added-row-bg); }
.diff-file-row.modified { background: var(--qqx-diff-modified-row-bg); }
.diff-file-row.removed { background: var(--qqx-diff-removed-row-bg); }

.diff-file-status {
  font-size: var(--sr-text-meta);
  min-width: 64px;
  font-weight: var(--sr-weight-semibold);
}

.diff-file-nav {
  display: flex;
  align-items: center;
  gap: var(--sr-space-3);
  margin-bottom: var(--sr-space-3);
}

.diff-file-nav-path {
  font-family: var(--sr-font-mono);
  font-size: var(--sr-text-compact);
  color: var(--sr-text-secondary);
}

.diff-file-path {
  word-break: break-all;
}

.diff-all-unchanged {
  text-align: center;
  padding: var(--sr-space-5);
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  color: var(--sr-text-tertiary);
  font-size: var(--sr-text-card-title);
}

/* ---- Add Target Form ---- */
.add-target-form {
  display: flex;
  flex-direction: column;
  gap: var(--sr-space-3);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-bold);
  color: var(--sr-text-secondary);
}

.form-input {
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-control-bg);
  color: var(--sr-text-primary);
  font-size: var(--sr-text-body);
  font-family: inherit;
  height: var(--sr-control-height-md);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              box-shadow 140ms var(--sr-ease-standard);
}

.form-input:hover:not(:focus) {
  background: var(--sr-control-bg-hover);
}

.form-input:focus {
  outline: none;
  background: var(--sr-control-bg-active);
  box-shadow: var(--sr-control-focus-shadow);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              box-shadow 180ms var(--sr-ease-standard);
}

.form-input-row {
  display: flex;
  gap: var(--sr-space-2);
  align-items: center;
}

.form-input-flex {
  flex: 1;
  min-width: 0;
}

/* ---- Target Files Management ---- */
.target-files-info {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-secondary);
  margin-bottom: var(--sr-space-3);
}

.target-files-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 50vh;
  overflow-y: auto;
}

.target-file-row {
  display: flex;
  align-items: center;
  gap: var(--sr-space-3);
  padding: 8px 12px;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-content-bg);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.target-file-row:hover {
  background: var(--sr-content-bg-hover);
}

.target-file-row.is-unmanaged {
  background: var(--sr-role-amber-surface);
}

.target-file-name {
  flex: 1;
  font-size: var(--sr-text-body);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
}

.target-file-badge {
  display: inline-flex;
  align-items: center;
  height: 24px;
  box-sizing: border-box;
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  line-height: 1;
  padding: 0 8px;
  border-radius: var(--sr-radius-badge);
  flex-shrink: 0;
}

.target-file-badge.managed {
  color: var(--sr-role-sage-ink);
  background: var(--sr-role-sage-surface);
}

.target-file-badge.unmanaged {
  color: var(--sr-role-amber-ink);
  background: var(--sr-bg-panel);
}

.target-file-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 56px;
  flex-shrink: 0;
}

.target-file-actions :deep(.qqx-btn) {
  min-width: 56px;
  min-height: 24px;
  height: 24px;
  box-sizing: border-box;
}

/* Confirm Remove Unmanaged */
.confirm-remove-body {
  display: flex;
  flex-direction: column;
  gap: var(--sr-space-3);
  align-items: center;
  text-align: center;
}

.confirm-warn-icon {
  color: var(--sr-role-amber-ink);
}

.confirm-warn-text {
  font-size: var(--sr-text-body);
  color: var(--sr-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.confirm-warn-text strong {
  color: var(--sr-text-primary);
}

/* ---- Responsive ---- */
@media (max-width: 760px) {
  .target-tabs-row {
    flex-direction: column;
  }

  .target-tab-actions {
    padding-top: 0;
  }

  .target-tabs {
    width: 100%;
    overflow-x: auto;
    flex-wrap: nowrap;
  }

  .config-skill-name {
    min-width: auto;
    width: 100%;
  }

  .skill-list-row {
    flex-wrap: wrap;
    gap: var(--sr-space-2);
  }
}

/* ── View tabs (Workbench segmented control) ── */
.sync-view-tabs {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  border: none;
  border-radius: var(--sr-radius-md);
  background: var(--sr-control-bg);
}

.sync-view-tab {
  min-height: 26px;
  padding: 0 12px;
  border: none;
  border-radius: var(--sr-radius-sm);
  background: transparent;
  color: var(--sr-text-secondary);
  font-size: var(--sr-text-compact);
  font-weight: var(--sr-weight-medium);
  cursor: pointer;
  font-family: inherit;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
}

.sync-view-tab:not(.sync-view-tab--active):hover {
  color: var(--sr-text-primary);
}

.sync-view-tab--active {
  background: var(--sr-action-bg-selected);
  color: var(--sr-text-primary);
  font-weight: var(--sr-weight-semibold);
  cursor: default;
}

/* ── Project view (Borderless cards & matrix table) ── */
.sync-projects {
  display: flex;
  flex-direction: column;
  gap: var(--sr-space-3);
}

.sp-card {
  border: none;
  border-radius: var(--sr-radius-lg);
  background: var(--sr-content-bg);
  overflow: hidden;
}

.sp-card-header {
  display: flex;
  align-items: center;
  gap: var(--sr-space-2);
  padding: var(--sr-space-3) var(--sr-space-4);
  cursor: pointer;
  user-select: none;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.sp-card-header:hover {
  background: var(--sr-bg-hover);
}

.sp-chevron {
  display: flex;
  color: var(--sr-text-tertiary);
  transition: transform var(--sr-duration-normal) var(--sr-ease-standard);
  flex-shrink: 0;
}

.sp-chevron--open {
  transform: rotate(90deg);
}

.sp-name {
  font-size: var(--sr-text-body);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
}

.sp-count {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
}

.sp-syncing {
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-accent);
  margin-left: auto;
}

.sp-card-body {
  padding: 0 var(--sr-space-3) var(--sr-space-3);
  background: transparent;
}

/* ── Borderless Matrix table (Header tint + striped rows, zero vertical grid lines) ── */
.sp-matrix {
  overflow-x: auto;
  border-radius: var(--sr-radius-md);
  background: var(--sr-bg-panel);
  padding: var(--sr-space-2);
}

.sp-matrix-header {
  display: flex;
  background: var(--sr-sticky-bg);
  backdrop-filter: var(--sr-sticky-filter);
  border-radius: var(--sr-radius-sm);
  padding: 0 var(--sr-space-3);
  margin-bottom: 4px;
  position: sticky;
  top: 0;
  z-index: 1;
}

.sp-matrix-header-skill {
  width: 180px;
  flex-shrink: 0;
  padding: 10px 0;
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-secondary);
}

.sp-matrix-header-target {
  flex: 1;
  min-width: 120px;
  padding: 10px var(--sr-space-2);
  text-align: center;
}

.sp-matrix-col-label {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-primary);
  font-weight: var(--sr-weight-semibold);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sp-matrix-col-agents {
  display: flex;
  justify-content: center;
  gap: 4px;
  margin-top: 3px;
  flex-wrap: wrap;
}

.sp-agent-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--sr-text-micro);
  font-weight: var(--sr-weight-semibold);
  background: var(--sr-role-blue-surface);
  color: var(--sr-role-blue-ink);
  padding: 1px 6px;
  border-radius: var(--sr-radius-badge);
  line-height: 16px;
}

.sp-agent-tag--warn {
  background: var(--sr-role-amber-surface);
  color: var(--sr-role-amber-ink);
}

.sp-matrix-col-actions {
  display: flex;
  justify-content: center;
  gap: 4px;
  margin-top: 4px;
}

.sp-matrix-row {
  display: flex;
  border-radius: var(--sr-radius-sm);
  padding: 0 var(--sr-space-3);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.sp-matrix-row:nth-child(even) {
  background: var(--sr-table-stripe);
}

.sp-matrix-row:hover {
  background: var(--sr-bg-hover);
}

.sp-matrix-skill {
  width: 180px;
  flex-shrink: 0;
  padding: 10px 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sp-matrix-skill-name {
  font-size: var(--sr-text-card-title);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sp-matrix-skill-name:hover {
  color: var(--sr-accent);
}

.sp-matrix-skill-status {
  font-size: var(--sr-text-meta);
  color: var(--sr-text-tertiary);
}

.sp-matrix-cell {
  flex: 1;
  min-width: 120px;
  padding: 10px var(--sr-space-2);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border-radius: var(--sr-radius-sm);
  cursor: pointer;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.sp-matrix-cell:hover {
  background: var(--sr-action-bg-hover);
}

.sp-cell-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--sr-radius-pill);
  flex-shrink: 0;
}

.sp-cell--unchanged .sp-cell-dot { background: var(--sr-role-sage-solid); }
.sp-cell--changed .sp-cell-dot { background: var(--sr-role-amber-solid); }
.sp-cell--missing .sp-cell-dot { background: var(--sr-role-rose-solid); }
.sp-cell--none .sp-cell-dot { background: var(--sr-border-strong); }

.sp-cell-label {
  font-size: var(--sr-text-meta);
  color: var(--sr-text-secondary);
}

.sp-cell-install {
  flex-shrink: 0;
  margin-left: auto;
  padding: 2px 8px;
  border: none;
  border-radius: var(--sr-radius-xs);
  background: var(--sr-role-blue-surface);
  color: var(--sr-role-blue-ink);
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-semibold);
  cursor: pointer;
  font-family: inherit;
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard), opacity var(--sr-duration-fast);
  opacity: 0;
}

.sp-matrix-cell:hover .sp-cell-install,
.sp-cell-install:focus-visible { opacity: 1; }
.sp-cell-install:hover:not(:disabled) { background: var(--sr-accent); color: var(--sr-text-inverse); }
.sp-cell-install:disabled { opacity: 0.4; cursor: not-allowed; }

.sp-card-footer {
  display: flex;
  gap: var(--sr-space-2);
  padding: var(--sr-space-3) var(--sr-space-1) 0;
}

/* ── Sync All Confirmation Modal ── */
.sync-all-confirm-body {
  display: flex;
  flex-direction: column;
  gap: var(--sr-space-3);
}

.sync-all-confirm-desc {
  margin: 0;
  font-size: var(--sr-text-body);
  color: var(--sr-text-secondary);
}

.sync-all-loading {
  text-align: center;
  padding: var(--sr-space-5);
  font-size: var(--sr-text-card-title);
  color: var(--sr-text-tertiary);
}

.sync-all-section {
  border: none;
  border-radius: var(--sr-radius-md);
  background: var(--sr-content-bg);
  padding: var(--sr-space-2);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sync-all-section-title {
  font-size: var(--sr-text-meta);
  font-weight: var(--sr-weight-bold);
  color: var(--sr-text-tertiary);
  padding: 4px 8px;
}

.sync-all-target-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: var(--sr-radius-sm);
  background: var(--sr-bg-panel);
}

.sync-all-target-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
  margin-right: var(--sr-space-3);
}

.sync-all-target-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--sr-text-card-title);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
}

.sync-all-target-path {
  font-size: var(--sr-text-meta);
  color: var(--sr-text-tertiary);
  font-family: var(--sr-font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sync-all-target-skill-count {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-secondary);
  white-space: nowrap;
}

.sync-all-changed {
  font-style: normal;
  color: var(--sr-role-amber-ink);
  font-weight: var(--sr-weight-semibold);
}

.sync-all-ok {
  font-style: normal;
  color: var(--sr-role-sage-ink);
}

.sync-all-empty {
  padding: var(--sr-space-3);
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
  text-align: center;
}

.sync-all-summary {
  font-size: var(--sr-text-card-title);
  color: var(--sr-text-primary);
  text-align: center;
  padding: var(--sr-space-1);
}

/* Progress bar */
.sync-all-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sync-all-progress-bar {
  width: 100%;
  height: 6px;
  background: var(--sr-control-bg);
  border-radius: var(--sr-radius-pill);
  overflow: hidden;
}

.sync-all-progress-fill {
  height: 100%;
  background: var(--sr-accent);
  border-radius: var(--sr-radius-pill);
  transition: width 260ms var(--sr-ease-standard);
}

.sync-all-progress-text {
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
  text-align: center;
}

.sync-all-current {
  font-size: var(--sr-text-meta);
  color: var(--sr-text-secondary);
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Target tab wrapper & Glass dropdown ── */
.target-tab-wrapper {
  position: relative;
  display: flex;
  align-items: stretch;
  gap: 2px;
}

.target-tab-more {
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--sr-text-tertiary);
  cursor: pointer;
  padding: 0 6px;
  border-radius: var(--sr-radius-sm);
  transition: color var(--sr-duration-fast) var(--sr-ease-standard),
              background-color var(--sr-duration-fast) var(--sr-ease-standard);
}

.target-tab-more:hover,
.target-tab-more--open {
  color: var(--sr-text-primary);
  background: var(--sr-action-bg-hover);
}

.target-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 6px;
  background: var(--sr-glass-bg);
  backdrop-filter: var(--sr-glass-filter);
  -webkit-backdrop-filter: var(--sr-glass-filter);
  border: none;
  border-radius: var(--sr-radius-md);
  box-shadow: var(--sr-shadow-md);
  min-width: 168px;
  z-index: var(--sr-z-popover);
  overflow: hidden;
  padding: 5px;
}

.target-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 32px;
  padding: 5px 8px;
  border: none;
  background: transparent;
  color: var(--sr-text-primary);
  font-size: var(--sr-text-compact);
  font-family: inherit;
  cursor: pointer;
  border-radius: var(--sr-radius-menu-item);
  transition: background-color var(--sr-duration-fast) var(--sr-ease-standard),
              color var(--sr-duration-fast) var(--sr-ease-standard);
  text-align: left;
}

.target-dropdown-item:hover {
  background: var(--sr-bg-hover);
}

.target-dropdown-item--danger {
  color: var(--sr-role-rose-ink);
}

.target-dropdown-item--danger:hover {
  background: var(--sr-role-rose-surface);
}

/* ── Rename target form ── */
.rename-target-form {
  display: flex;
  flex-direction: column;
  gap: var(--sr-space-3);
}

.form-static-value {
  padding: 0 12px;
  background: var(--sr-content-bg);
  border-radius: var(--sr-radius-sm);
  font-size: var(--sr-text-body);
  font-weight: var(--sr-weight-semibold);
  color: var(--sr-text-primary);
  height: var(--sr-control-height-md);
  display: flex;
  align-items: center;
}

.form-static-subvalue {
  font-family: var(--sr-font-mono);
  font-size: var(--sr-text-compact);
  color: var(--sr-text-tertiary);
  word-break: break-all;
}

</style>
