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
          <Search :size="14" /> 内置 Agent
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
        <p class="sync-empty-targets-title">未自动探测到常见 Agent 目录</p>
        <p class="sync-empty-targets-desc">可从内置 Agent 预设中选择目录，或手动新增自定义同步目标。</p>
        <div class="sync-empty-targets-actions">
          <QButton type="secondary" size="small" @click="openDiscoverHome"><Search :size="14" /> 查看内置 Agent</QButton>
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
                  <Trash2 :size="13" /> 隐藏此内置目录
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
          <QButton type="primary" size="small" pill :disabled="syncingInTarget" @click="syncActiveTarget">
            <RefreshCw :size="14" /> 同步 {{ activeTargetShort }}
          </QButton>
        </div>
      </div>

      <!-- Skill List for Active Target -->
      <QCard class="skill-list-card">
        <template #header>
          <span class="card-target-label">Target: {{ activeTargetLabel }}</span>
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
                    <span v-for="d in (discoveredProjectMap[t]?.agent_dirs || [])" :key="d.agent" class="sp-agent-tag">{{ d.agent }}</span>
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
              <span class="sync-all-target-name">{{ t.label || t.name }}</span>
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
                <span class="sync-all-target-name">{{ getTargetLabel(t.path) }}</span>
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

    <!-- Built-in Agent Catalog & Discovery Modal -->
    <QModal v-model="discoverOpen" title="内置 Agent 目录" width="640px">
      <div v-if="discoverLoading" class="sync-loading">正在探测常见 Agent 目录...</div>
      <div v-else-if="discoverError" class="sync-error">{{ discoverError }}</div>
      <div v-else class="discover-body">
        <div class="discover-toolbar">
          <input
            v-model="discoverQuery"
            type="text"
            class="form-input discover-search"
            placeholder="搜索 Agent 名称或路径，例如: claude、cursor、opencode..."
          />
          <QButton type="ghost" size="small" @click="switchToManualTarget">+ 手动自定义目录</QButton>
        </div>

        <div class="discover-sections">
          <div class="discover-section">
            <div class="discover-section-title">
              本机已自动识别 ({{ partitionedCatalog.detected.length }})
              <span class="discover-section-hint">免手动配置即可直接同步与安装</span>
            </div>
            <div v-if="!partitionedCatalog.detected.length" class="discover-empty">
              未匹配到本机已识别的 Agent 目录
            </div>
            <div v-else class="discover-list">
              <div
                v-for="agent in partitionedCatalog.detected"
                :key="agent.id"
                class="discover-row"
                :class="{ 'discover-row--muted': !agent.active }"
              >
                <div class="discover-info">
                  <div class="discover-name-line">
                    <span class="discover-agent">{{ agent.name }}</span>
                    <span v-if="agent.shared" class="discover-pill discover-pill--brand">共享</span>
                    <span class="discover-pill">{{ detectedByLabel(agent.detectedBy, agent.detectedBinary) }}</span>
                  </div>
                  <code class="discover-path" :title="agent.path">{{ formatDisplayPath(agent.path, agent.rel_path) }}</code>
                </div>
                <div class="discover-row-actions">
                  <span v-if="agent.configured" class="discover-status discover-status--custom">已自定义</span>
                  <template v-else-if="agent.enabled">
                    <span class="discover-status discover-status--active">已自动启用</span>
                    <QButton
                      type="ghost"
                      size="small"
                      :disabled="discoverBusyId === agent.id"
                      @click="toggleBuiltinAgent(agent, false)"
                    >隐藏</QButton>
                  </template>
                  <template v-else>
                    <span class="discover-status discover-status--hidden">已隐藏</span>
                    <QButton
                      type="secondary"
                      size="small"
                      :disabled="discoverBusyId === agent.id"
                      @click="toggleBuiltinAgent(agent, true)"
                    >启用</QButton>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <div class="discover-section">
            <div class="discover-section-title">
              其他常见 Agent 预设 ({{ partitionedCatalog.presets.length }})
              <span class="discover-section-hint">本机暂未检测到，可一键添加</span>
            </div>
            <div v-if="!partitionedCatalog.presets.length" class="discover-empty">
              无匹配的其他预设
            </div>
            <div v-else class="discover-list">
              <div
                v-for="agent in partitionedCatalog.presets"
                :key="agent.id"
                class="discover-row"
              >
                <div class="discover-info">
                  <div class="discover-name-line">
                    <span class="discover-agent">{{ agent.name }}</span>
                    <span v-if="agent.shared" class="discover-pill discover-pill--brand">共享</span>
                  </div>
                  <code class="discover-path" :title="agent.path">{{ formatDisplayPath(agent.path, agent.rel_path) }}</code>
                </div>
                <div class="discover-row-actions">
                  <span v-if="agent.configured" class="discover-status discover-status--custom">已添加</span>
                  <QButton
                    v-else
                    type="secondary"
                    tint="brand"
                    size="small"
                    :disabled="discoverBusyId === agent.id"
                    @click="addPresetTarget(agent)"
                  >{{ discoverBusyId === agent.id ? '添加中...' : '添加' }}</QButton>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
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
import { useSyncBridge } from '../composables/useSyncBridge.js'
import { useSkillDetail } from '../composables/useSkillDetail.js'
import { useToast } from '../composables/useToast.js'
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
  detectedByLabel,
  formatAgentDisplayPath,
  normalizeTarget,
  partitionAgentCatalog,
  pickQuickPresets,
  targetBadgeText,
} from '../sources/agentTargets.js'

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

const activeTargetShort = computed(() => {
  const t = allTargets.value.find(t => t.path === activeTarget.value)
  return t ? (t._label || t.label || t.name) : activeTarget.value
})

const activeTargetLabel = computed(() => {
  const t = allTargets.value.find(t => t.path === activeTarget.value)
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

const discoverOpen = ref(false)
const discoverLoading = ref(false)
const discoverError = ref('')
const discoverQuery = ref('')
const discoverBusyId = ref(null)

const partitionedCatalog = computed(() =>
  partitionAgentCatalog(builtinCatalog.value, discoverQuery.value),
)

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

async function openDiscoverHome() {
  discoverOpen.value = true
  discoverLoading.value = true
  discoverError.value = ''
  discoverQuery.value = ''
  try {
    const data = await fetchBuiltinAgents(true)
    builtinCatalog.value = data.agents || []
  } catch (e) {
    discoverError.value = e.message
  } finally {
    discoverLoading.value = false
  }
}

function switchToManualTarget() {
  discoverOpen.value = false
  openAddTargetModal()
}

async function toggleBuiltinAgent(agent, enabled) {
  discoverBusyId.value = agent.id
  discoverError.value = ''
  try {
    await setBuiltinAgentEnabled(agent.id, enabled)
    const data = await fetchBuiltinAgents(true)
    builtinCatalog.value = data.agents || []
    await loadAll(true)
    toast.success(enabled ? `已启用内置目录: ${agent.name}` : `已隐藏内置目录: ${agent.name}`)
  } catch (e) {
    discoverError.value = e.message || '操作失败'
  } finally {
    discoverBusyId.value = null
  }
}

async function addPresetTarget(agent) {
  discoverBusyId.value = agent.id
  discoverError.value = ''
  try {
    await addSyncTarget(agent.name, agent.path, { agentKind: agent.id })
    const data = await fetchBuiltinAgents(true)
    builtinCatalog.value = data.agents || []
    await loadAll(true)
    toast.success(`已添加目标: ${agent.name}`)
  } catch (e) {
    discoverError.value = e.message || '添加失败'
  } finally {
    discoverBusyId.value = null
  }
}

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
    toast.success(`已隐藏内置目录: ${t.label || t.name}`)
  } catch (e) {
    toast.error(`隐藏失败: ${e.message}`)
  }
}
</script>

<style scoped>
.sync-manager {
  /* Root container */
}

.sync-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--qqx-space-xl);
  flex-wrap: wrap;
  gap: var(--qqx-space-sm);
}

.sync-header-left {
  display: flex;
  align-items: baseline;
  gap: var(--qqx-space-md);
}

.sync-title {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
}

.sync-count {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
}

.sync-header-actions {
  display: flex;
  gap: var(--qqx-space-sm);
  align-items: center;
}

.project-select {
  padding: 4px 8px;
  border: 1px solid var(--qqx-input-border);
  border-radius: var(--qqx-radius-xs);
  background: var(--qqx-input-bg);
  color: var(--qqx-text-primary);
  font-size: 12px;
  font-family: inherit;
  height: 30px;
  cursor: pointer;
}

.project-select:focus {
  outline: none;
  border-color: var(--qqx-brand);
}

.sync-error {
  color: #ef4444;
  font-size: var(--qqx-font-size-small);
  margin-bottom: var(--qqx-space-md);
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  background: rgba(239, 68, 68, 0.08);
  border-radius: var(--qqx-radius-sm);
}

.sync-loading, .sync-empty {
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
  padding: var(--qqx-space-xl);
  text-align: center;
}

/* ---- Target Tabs ---- */

.target-tabs-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--qqx-space-md);
  margin-bottom: var(--qqx-space-xl);
}

.target-tabs {
  display: flex;
  gap: 2px;
  background: var(--qqx-bg-elevated);
  border-radius: var(--qqx-radius-md);
  padding: 3px;
  border: 1px solid var(--qqx-border-color);
  flex-wrap: wrap;
}

.target-tab {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  border: none;
  background: transparent;
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  border-radius: var(--qqx-radius-sm);
  transition: all var(--qqx-transition);
  text-align: left;
  min-width: 100px;
}

.target-tab-wrapper .target-tab {
  border-radius: var(--qqx-radius-sm) 0 0 var(--qqx-radius-sm);
  min-width: 80px;
}

.target-tab-wrapper .target-tab--active {
  background: var(--qqx-bg-card);
}

.target-tab:not(.target-tab--active):hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-primary);
}

.target-tab--active {
  background: var(--qqx-bg-card);
  color: var(--qqx-text-primary);
  font-weight: var(--qqx-font-medium);
}

.target-tab--project {
  border-left: 2px solid var(--qqx-brand);
}

.target-tab-header {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.target-tab-name {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: inherit;
}

.target-tab-badge {
  display: inline-flex;
  align-items: center;
  padding: 0 5px;
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-tertiary);
  font-size: 10px;
  line-height: 1.5;
  font-weight: var(--qqx-font-regular);
}

.target-tab-badge--shared {
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
}

.sync-empty-targets {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--qqx-space-sm);
  padding: 48px 24px;
  border: 1px dashed var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-card);
  text-align: center;
}

.sync-empty-targets-title {
  margin: 0;
  font-size: var(--qqx-font-size-body);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
}

.sync-empty-targets-desc {
  margin: 0;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
}

.sync-empty-targets-actions {
  display: flex;
  gap: var(--qqx-space-sm);
  margin-top: var(--qqx-space-sm);
}

.preset-section {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-xs);
}

.preset-label {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
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
  padding: 4px 10px;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-elevated);
  color: var(--qqx-text-primary);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: border-color var(--qqx-transition), background var(--qqx-transition);
}

.preset-chip:hover,
.preset-chip--active {
  border-color: var(--qqx-brand);
  background: var(--qqx-brand-light);
}

.preset-chip-path {
  font-size: 11px;
  color: var(--qqx-text-tertiary);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.target-tab-path {
  font-size: 10px;
  color: var(--qqx-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 160px;
}

.target-tab-actions {
  display: flex;
  gap: var(--qqx-space-sm);
  flex-shrink: 0;
  padding-top: var(--qqx-space-xs);
}

/* ---- Config Panel ---- */

.config-card {
  margin-bottom: var(--qqx-space-xl);
}

.config-body {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-sm);
}

.config-skill-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-sm) 0;
  border-bottom: 1px solid var(--qqx-border-color);
  flex-wrap: wrap;
}

.config-skill-row:last-child {
  border-bottom: none;
}

.config-skill-name {
  min-width: 180px;
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.config-checkbox {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--qqx-text-secondary);
  cursor: pointer;
}

.config-actions {
  display: flex;
  gap: var(--qqx-space-sm);
  justify-content: flex-end;
  padding-top: var(--qqx-space-md);
}

/* ---- Search & Filter ---- */

.search-bar {
  display: flex;
  gap: var(--qqx-space-md);
  align-items: center;
  margin-bottom: var(--qqx-space-lg);
  flex-wrap: wrap;
}

.search-input {
  padding: var(--qqx-space-xs) var(--qqx-space-md);
  border: 1px solid var(--qqx-input-border);
  border-radius: var(--qqx-radius-xs);
  background: var(--qqx-input-bg);
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-small);
  font-family: inherit;
  width: 200px;
  height: 32px;
  transition: border-color var(--qqx-transition);
}

.search-input:focus {
  outline: none;
  border-color: var(--qqx-brand);
  box-shadow: var(--qqx-shadow-focus);
}

.filter-btns {
  display: flex;
  gap: 4px;
}

.filter-btn {
  padding: 2px 10px;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-card);
  color: var(--qqx-text-secondary);
  font-size: 11px;
  transition: all var(--qqx-transition);
}

.filter-btn:not(.filter-btn--active):hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-primary);
}

.filter-btn--active {
  background: var(--qqx-brand-light);
  border-color: var(--qqx-brand);
  color: var(--qqx-brand);
  font-weight: var(--qqx-font-medium);
}

/* ---- Skill List Card ---- */

.skill-list-card {
  margin-bottom: var(--qqx-space-xl);
}

.card-target-label {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  font-weight: var(--qqx-font-regular);
}

.skill-list {
  display: flex;
  flex-direction: column;
}

.section-header {
  margin-bottom: var(--qqx-space-md);
}

.skill-list-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  border-radius: var(--qqx-radius-md);
  transition: background-color var(--qqx-transition), box-shadow var(--qqx-transition);
}

.skill-list-row:hover,
.skill-list-row:focus-within {
  background: var(--qqx-bg-hover);
  box-shadow: inset 0 0 0 1px var(--qqx-border-color);
}

.skill-list-row + .skill-list-row {
  border-top: 1px solid var(--qqx-border-color);
}

.skill-list-name {
  flex: 1;
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
  cursor: pointer;
  transition: color var(--qqx-transition);
}
.skill-list-name:hover {
  color: var(--qqx-brand);
}

.skill-list-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
  flex-shrink: 0;
}

.skill-list-status.unchanged,
.skill-list-status.synced {
  color: var(--qqx-success);
  background: var(--qqx-success-light);
}

.skill-list-status.changed,
.skill-list-status.modified {
  color: var(--qqx-warning);
  background: var(--qqx-warning-light);
}

.skill-list-status.missing {
  color: var(--qqx-text-tertiary);
  background: var(--qqx-bg-elevated);
}

.skill-list-status.not-installed {
  color: var(--qqx-text-tertiary);
  border: 1px dashed var(--qqx-border-dashed);
  background: transparent;
}

.skill-list-actions {
  display: flex;
  gap: var(--qqx-space-xs);
  flex-shrink: 0;
}

/* ---- Diff Summary ---- */

.diff-summary {
  display: flex;
  gap: var(--qqx-space-sm);
  flex-wrap: wrap;
  margin-bottom: var(--qqx-space-md);
  padding-bottom: var(--qqx-space-md);
  border-bottom: 1px solid var(--qqx-border-color);
}

.diff-stat {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
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
  gap: 2px;
}

.diff-file-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  padding: 4px 8px;
  border-radius: var(--qqx-radius-xs);
  cursor: pointer;
  transition: filter 0.15s ease;
}

.diff-file-row:hover {
  filter: brightness(0.92);
}

.diff-file-row.added { background: var(--qqx-diff-added-row-bg); }
.diff-file-row.modified { background: var(--qqx-diff-modified-row-bg); }
.diff-file-row.removed { background: var(--qqx-diff-removed-row-bg); }

.diff-file-status {
  font-size: 11px;
  min-width: 64px;
  font-weight: var(--qqx-font-medium);
}

/* Diff file preview nav */
.diff-file-nav {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  margin-bottom: var(--qqx-space-md);
  padding-bottom: var(--qqx-space-md);
  border-bottom: 1px solid var(--qqx-border-color);
}

.diff-file-nav-path {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
}

.diff-file-path {
  word-break: break-all;
}

.diff-all-unchanged {
  text-align: center;
  padding: var(--qqx-space-xl);
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
}

/* ---- Add Target Form ---- */

.add-target-form {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-xs);
}

.form-label {
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-secondary);
}

.form-input {
  padding: var(--qqx-space-xs) var(--qqx-space-md);
  border: 1px solid var(--qqx-input-border);
  border-radius: var(--qqx-radius-xs);
  background: var(--qqx-input-bg);
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-label);
  font-family: inherit;
  height: 40px;
  transition: border-color var(--qqx-transition);
}

.form-input:focus {
  outline: none;
  border-color: var(--qqx-brand);
  box-shadow: var(--qqx-shadow-focus);
}

.form-input-row {
  display: flex;
  gap: var(--qqx-space-sm);
  align-items: center;
}

.form-input-flex {
  flex: 1;
}

/* ---- Target Files Management ---- */

.target-files-info {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  margin-bottom: var(--qqx-space-md);
  padding-bottom: var(--qqx-space-md);
  border-bottom: 1px solid var(--qqx-border-color);
}

.target-files-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 50vh;
  overflow-y: auto;
}

.target-file-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  border-radius: var(--qqx-radius-xs);
  transition: background var(--qqx-transition);
}

.target-file-row:hover {
  background: var(--qqx-bg-hover);
}

.target-file-row.is-unmanaged {
  background: rgba(245, 158, 11, 0.06);
}

.target-file-row.is-unmanaged:hover {
  background: rgba(245, 158, 11, 0.12);
}

.target-file-name {
  flex: 1;
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.target-file-badge {
  display: inline-flex;
  align-items: center;
  height: 24px;
  box-sizing: border-box;
  font-size: 11px;
  line-height: 1;
  padding: 0 8px;
  border-radius: var(--qqx-radius-full);
  flex-shrink: 0;
}

.target-file-badge.managed {
  color: #10b981;
  background: rgba(16, 185, 129, 0.08);
}

.target-file-badge.unmanaged {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
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
  height: 24px;
  box-sizing: border-box;
}

/* Confirm Remove Unmanaged */

.confirm-remove-body {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-lg);
  align-items: center;
  text-align: center;
}

.confirm-warn-icon {
  color: #f59e0b;
}

.confirm-warn-text {
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.confirm-warn-text strong {
  color: var(--qqx-text-primary);
}

/* ---- Responsive ---- */

@media (max-width: 767px) {
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
    gap: var(--qqx-space-sm);
  }
}

/* ── View tabs ── */

.sync-view-tabs {
  display: flex;
  gap: 0;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  overflow: hidden;
}

.sync-view-tab {
  padding: 4px 14px;
  border: none;
  background: transparent;
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  cursor: pointer;
  font-family: inherit;
  transition: background var(--qqx-transition), color var(--qqx-transition);
}

.sync-view-tab:not(.sync-view-tab--active):hover { background: var(--qqx-bg-hover); }

.sync-view-tab--active {
  background: var(--qqx-brand-fill-bg);
  color: #fff;
  cursor: default;
}

/* ── Project view ── */

.sync-projects {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

.sp-card {
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-card);
  overflow: hidden;
}

.sp-card-header {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-xs);
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  cursor: pointer;
  user-select: none;
  transition: background var(--qqx-transition);
}

.sp-card-header:hover { background: var(--qqx-bg-hover); }

.sp-chevron {
  display: flex;
  color: var(--qqx-text-tertiary);
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.sp-chevron--open { transform: rotate(90deg); }

.sp-name {
  font-size: var(--qqx-font-size-body);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
}

.sp-count {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
}

.sp-syncing {
  font-size: var(--qqx-font-size-tiny);
  color: var(--qqx-brand);
  margin-left: auto;
}

.sp-card-body {
  border-top: 1px solid var(--qqx-border-color);
  padding: 0;
  background: var(--qqx-bg-surface);
}

[data-theme="light"] .sp-card-body,
:root .sp-card-body {
  background: #fafbfc;
}

[data-theme="dark"] .sp-card-body {
  background: var(--qqx-bg-elevated);
}

/* ── Matrix table ── */

.sp-matrix {
  overflow-x: auto;
}

.sp-matrix-header {
  display: flex;
  border-bottom: 1px solid var(--qqx-border-color);
  background: var(--qqx-bg-subtle);
  padding: 0 var(--qqx-space-md);
  position: sticky;
  top: 0;
}

.sp-matrix-header-skill {
  width: 180px;
  flex-shrink: 0;
  padding: 8px 0;
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-secondary);
}

.sp-matrix-header-target {
  flex: 1;
  min-width: 120px;
  padding: 8px var(--qqx-space-sm);
  text-align: center;
  border-left: 1px solid var(--qqx-border-color);
}

.sp-matrix-col-label {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  font-weight: var(--qqx-font-medium);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sp-matrix-col-agents {
  display: flex;
  justify-content: center;
  gap: 3px;
  margin-top: 2px;
  flex-wrap: wrap;
}

.sp-agent-tag {
  font-size: 10px;
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
  padding: 0px 5px;
  border-radius: var(--qqx-radius-full);
  line-height: 16px;
}

.sp-agent-tag--warn {
  background: rgba(180, 83, 9, 0.08);
  color: #b45309;
}

.sp-matrix-col-actions {
  display: flex;
  justify-content: center;
  gap: 2px;
  margin-top: 3px;
}

.sp-matrix-row {
  display: flex;
  border-bottom: 1px solid var(--qqx-border-color);
  padding: 0 var(--qqx-space-md);
  transition: background var(--qqx-transition);
}

.sp-matrix-row:hover { background: var(--qqx-bg-hover); }

.sp-matrix-skill {
  width: 180px;
  flex-shrink: 0;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sp-matrix-skill-name {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sp-matrix-skill-name:hover { color: var(--qqx-brand); }

.sp-matrix-skill-status {
  font-size: var(--qqx-font-size-tiny);
  color: var(--qqx-text-tertiary);
}

.sp-matrix-cell {
  flex: 1;
  min-width: 120px;
  padding: 8px var(--qqx-space-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  border-left: 1px solid var(--qqx-border-color);
  cursor: pointer;
  transition: background var(--qqx-transition);
}

.sp-matrix-cell:hover { background: var(--qqx-bg-overlay); }

.sp-cell-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sp-cell--unchanged .sp-cell-dot { background: #6ee7b7; }
.sp-cell--changed .sp-cell-dot { background: #fcd34d; }
.sp-cell--missing .sp-cell-dot { background: var(--qqx-text-quaternary); }
.sp-cell--none .sp-cell-dot { background: transparent; border: 1px solid var(--qqx-border-dashed); }

.sp-cell-label {
  font-size: var(--qqx-font-size-tiny);
  color: var(--qqx-text-tertiary);
}

.sp-cell-install {
  flex-shrink: 0;
  margin-left: auto;
  padding: 1px 8px;
  border: none;
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
  font-size: 11px;
  font-weight: var(--qqx-font-medium);
  cursor: pointer;
  font-family: inherit;
  transition: background var(--qqx-transition), opacity 0.15s;
  opacity: 0;
}

.sp-matrix-cell:hover .sp-cell-install { opacity: 1; }
.sp-cell-install:hover:not(:disabled) { background: var(--qqx-brand-fill-bg); color: #fff; }
.sp-cell-install:disabled { opacity: 0.4; cursor: not-allowed; }

.sp-card-footer {
  display: flex;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  border-top: 1px solid var(--qqx-border-color);
}

/* ── Sync All Confirmation Modal ── */

.sync-all-confirm-body {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

.sync-all-confirm-desc {
  margin: 0;
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-secondary);
}

.sync-all-loading {
  text-align: center;
  padding: 24px;
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-tertiary);
}

.sync-all-section {
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  overflow: hidden;
}

.sync-all-section-title {
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-tertiary);
  padding: 6px var(--qqx-space-md);
  background: var(--qqx-bg-elevated);
  border-bottom: 1px solid var(--qqx-border-color);
}

.sync-all-target-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px var(--qqx-space-md);
}

.sync-all-target-row + .sync-all-target-row {
  border-top: 1px solid var(--qqx-border-color);
}

.sync-all-target-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
  margin-right: var(--qqx-space-md);
}

.sync-all-target-name {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.sync-all-target-path {
  font-size: var(--qqx-font-size-tiny);
  color: var(--qqx-text-tertiary);
  font-family: 'SF Mono', 'Fira Code', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sync-all-target-skill-count {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  white-space: nowrap;
}

.sync-all-changed {
  font-style: normal;
  color: #d4b96a;
  font-weight: var(--qqx-font-medium);
}

.sync-all-ok {
  font-style: normal;
  color: #6ee7b7;
}

.sync-all-empty {
  padding: 12px var(--qqx-space-md);
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  text-align: center;
}

.sync-all-summary {
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-primary);
  text-align: center;
  padding: var(--qqx-space-xs);
}

/* Progress bar */
.sync-all-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sync-all-progress-bar {
  width: 100%;
  height: 4px;
  background: var(--qqx-bg-elevated);
  border-radius: 2px;
  overflow: hidden;
}

.sync-all-progress-fill {
  height: 100%;
  background: var(--qqx-brand-fill-bg);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.sync-all-progress-text {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  text-align: center;
}

.sync-all-current {
  font-size: var(--qqx-font-size-tiny);
  color: var(--qqx-text-secondary);
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Target tab wrapper & dropdown ── */

.target-tab-wrapper {
  position: relative;
  display: flex;
  align-items: stretch;
}

.target-tab-more {
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--qqx-text-quaternary);
  cursor: pointer;
  padding: 0 4px;
  border-radius: var(--qqx-radius-sm);
  margin-left: 2px;
  transition: color var(--qqx-transition), background var(--qqx-transition);
}

.target-tab-more:hover,
.target-tab-more--open {
  color: var(--qqx-text-secondary);
  background: var(--qqx-bg-hover);
}

.target-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--qqx-bg-card);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  min-width: 140px;
  z-index: var(--z-dropdown);
  overflow: hidden;
  padding: 4px;
}

.target-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  font-family: inherit;
  cursor: pointer;
  border-radius: var(--qqx-radius-xs);
  transition: background var(--qqx-transition), color var(--qqx-transition);
  text-align: left;
}

.target-dropdown-item:hover {
  background: var(--qqx-bg-hover);
  color: var(--qqx-text-primary);
}

.target-dropdown-item--danger:hover {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
}

/* ── Rename target form ── */

.rename-target-form {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

.form-static-value {
  padding: var(--qqx-space-xs) var(--qqx-space-md);
  background: var(--qqx-bg-elevated);
  border-radius: var(--qqx-radius-xs);
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-tertiary);
  height: 40px;
  display: flex;
  align-items: center;
}

/* ── Built-in agent catalog modal ── */

.discover-body {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

.discover-toolbar {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
}

.discover-search {
  flex: 1;
  min-width: 0;
}

.discover-sections {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-lg);
  max-height: 55vh;
  overflow-y: auto;
  padding-right: 2px;
}

.discover-section {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-xs);
}

.discover-section-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--qqx-space-sm);
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-secondary);
}

.discover-section-hint {
  font-size: 11px;
  font-weight: var(--qqx-font-regular);
  color: var(--qqx-text-tertiary);
}

.discover-empty {
  padding: var(--qqx-space-md);
  text-align: center;
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  background: var(--qqx-bg-elevated);
  border-radius: var(--qqx-radius-xs);
}

.discover-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.discover-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  background: var(--qqx-bg-card);
  transition: background var(--qqx-transition), border-color var(--qqx-transition);
}

.discover-row:hover {
  background: var(--qqx-bg-hover);
}

.discover-row--muted {
  opacity: 0.7;
}

.discover-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  flex: 1;
  min-width: 0;
}

.discover-name-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.discover-agent {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.discover-pill {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-bg-elevated);
  color: var(--qqx-text-secondary);
  font-size: 11px;
}

.discover-pill--brand {
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
}

.discover-path {
  font-size: var(--qqx-font-size-tiny);
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--qqx-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.discover-row-actions {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  flex-shrink: 0;
}

.discover-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--qqx-radius-full);
}

.discover-status--active {
  background: var(--qqx-success-light);
  color: var(--qqx-success);
}

.discover-status--custom {
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
}

.discover-status--hidden {
  background: var(--qqx-bg-elevated);
  color: var(--qqx-text-tertiary);
}
</style>
