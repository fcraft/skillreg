<template>
  <QModal
    v-model="localVisible"
    :title="modalTitle"
    :width="modalWidth"
    @update:model-value="handleClose"
  >
    <!-- Step: source -->
    <div v-if="step === 'source'" class="import-step">
      <QTabs :tabs="sourceTabs" v-model="sourceType" />

      <!-- Folder tab -->
      <div v-show="sourceType === 'folder'" class="source-panel">
        <div class="form-group">
          <label class="form-label">本地文件夹路径</label>
          <div class="input-row input-row--folder">
            <input
              v-model="folderPath"
              class="qqx-input"
              placeholder="例如: ~/.claude/skills/my-skill 或 /Users/xxx/.claude/skills/my-skill"
              @input="clearUploadedFolder"
              @keyup.enter="validateSource"
            />
            <QButton
              type="secondary"
              size="small"
              :disabled="uploading"
              @click="openFolderPicker"
            >
              <FolderOpenIcon :size="15" />
              {{ uploading ? '读取中...' : '选择文件夹' }}
            </QButton>
            <QButton
              type="primary"
              size="small"
              :disabled="!folderPath.trim() || validationLoading || uploading"
              @click="validateSource"
            >
              {{ validationLoading ? '验证中...' : '验证' }}
            </QButton>
            <input
              ref="folderInput"
              class="native-folder-input"
              type="file"
              webkitdirectory
              directory
              multiple
              @change="handleFolderSelection"
            />
          </div>
          <p class="form-hint">可选择文件夹直接导入，也可手动输入本机路径</p>
          <div v-if="validationError" class="state-card state-card--error folder-error">
            <div class="state-card__inner"><XCircleIcon :size="20" /><span>{{ validationError }}</span></div>
          </div>
        </div>
      </div>

      <!-- Zip tab -->
      <div v-show="sourceType === 'zip'" class="source-panel">
        <div
          class="drop-zone"
          :class="{ 'drop-zone--active': dragOver, 'drop-zone--has-file': selectedFile }"
          @dragover.prevent="dragOver = true"
          @dragleave.prevent="dragOver = false"
          @drop.prevent="handleDrop"
          @click="openFilePicker"
        >
          <UploadIcon :size="32" class="drop-zone__icon" />
          <p class="drop-zone__text">
            {{ selectedFile ? selectedFile.name : '拖放 ZIP 文件到此处，或点击选择文件' }}
          </p>
          <p v-if="uploading" class="drop-zone__hint">上传中...</p>
          <p v-else class="drop-zone__hint">仅支持 .zip 格式</p>
          <input
            ref="fileInput"
            type="file"
            accept=".zip"
            style="display: none"
            @change="handleFileChange"
          />
        </div>
        <div v-if="selectedFile && !uploading" class="zip-actions">
          <QButton type="primary" size="small" @click="uploadAndValidate">
            验证 ZIP 文件
          </QButton>
        </div>
      </div>

      <!-- Git tab -->
      <div v-show="sourceType === 'git'" class="source-panel">
        <div class="form-group">
          <label class="form-label">Git 仓库 URL</label>
          <div class="input-row">
            <input v-model="gitUrl" class="qqx-input" placeholder="例如: https://github.com/user/my-skill.git" @keyup.enter="validateGitUrl" />
          </div>
        </div>
        <div class="form-group" style="margin-top: var(--qqx-space-sm);">
          <label class="form-label">分支（可选）</label>
          <div class="input-row">
            <input v-model="gitBranch" class="qqx-input" placeholder="默认: main" />
            <QButton type="primary" size="small" :disabled="!gitUrl.trim() || gitLoading" @click="validateGitUrl">
              {{ gitLoading ? '克隆中...' : '验证' }}
            </QButton>
          </div>
        </div>
        <div v-if="gitError" class="state-card state-card--error" style="margin-top: var(--qqx-space-md);">
          <div class="state-card__inner"><XCircleIcon :size="20" /><span>{{ gitError }}</span></div>
        </div>
        <div v-if="gitSkills.length > 0" class="git-skills-section">
          <div class="git-section-label">发现 {{ gitSkills.length }} 个技能</div>
          <div v-for="sk in gitSkills" :key="sk.name" class="git-skill-row" :class="{ 'git-skill-row--selected': gitSelected.includes(sk.name) }" @click="toggleGitSkill(sk.name)">
            <div class="git-skill-check"><div class="check-box" :class="{ 'check-box--checked': gitSelected.includes(sk.name) }"><CheckIcon v-if="gitSelected.includes(sk.name)" :size="12" /></div></div>
            <div class="git-skill-info">
              <div class="git-skill-name">{{ sk.name }}</div>
              <div class="git-skill-desc">{{ sk.description || '无描述' }}</div>
              <div class="git-skill-path">{{ sk.relPath }}</div>
            </div>
          </div>
          <div class="git-section-label" style="margin-top: var(--qqx-space-lg);">导入方式</div>
          <div class="git-mode-group">
            <QRadio v-model="gitMode" value="skill" label="导入为 Skill" />
            <QRadio v-model="gitMode" value="submodule" label="注册为 Submodule" />
          </div>
          <div v-if="gitMode === 'skill'" class="form-group" style="margin-top: var(--qqx-space-sm);">
            <label class="form-label">目标子目录（相对于 skills/）</label>
            <div class="input-row"><input v-model="gitTargetDir" class="qqx-input" placeholder="third（默认）" /></div>
            <p class="form-hint">导入到 skills/{{ gitTargetDir || 'third' }}/&lt;skill-name&gt;</p>
          </div>
          <div v-if="gitMode === 'submodule'" class="form-group" style="margin-top: var(--qqx-space-sm);">
            <label class="form-label">Submodule 路径</label>
            <div class="input-row"><input v-model="gitSubmodulePath" class="qqx-input" :placeholder="`repos/third/${gitSubmoduleDefaultName}`" /></div>
            <p class="form-hint">路径相对于仓库根目录</p>
          </div>
          <div style="margin-top: var(--qqx-space-lg); display: flex; justify-content: flex-end;">
            <QButton type="primary" :disabled="gitSelected.length === 0 || gitImporting" @click="executeGitImport">
              {{ gitImporting ? '导入中...' : '导入' }}
            </QButton>
          </div>
        </div>
      </div>

      <div v-show="sourceType === 'npm'" class="source-panel">
        <div class="form-group">
          <label class="form-label">NPM 包名</label>
          <input v-model="npmPackage" class="qqx-input" placeholder="例如: @scope/design-skills" @keyup.enter="previewNpm" />
        </div>
        <div class="npm-source-grid">
          <div class="form-group">
            <label class="form-label">Registry</label>
            <input v-model="npmRegistry" class="qqx-input" placeholder="https://registry.npmjs.org/" />
          </div>
          <div class="form-group">
            <label class="form-label">版本</label>
            <input v-model="npmVersionSpec" class="qqx-input" placeholder="latest" @keyup.enter="previewNpm" />
          </div>
        </div>
        <div class="npm-preview-action">
          <QButton type="primary" size="small" :disabled="!npmPackage.trim() || npmLoading" @click="previewNpm">
            {{ npmLoading ? '验证中...' : '验证并预览' }}
          </QButton>
        </div>
        <div v-if="npmError" class="state-card state-card--error"><div class="state-card__inner"><XCircleIcon :size="20" /><span>{{ npmError }}</span></div></div>

        <div v-if="npmPreview" class="npm-preview">
          <div class="npm-resolution">
            <strong>{{ npmPreview.package }}@{{ npmPreview.resolvedVersion }}</strong>
            <code>{{ npmPreview.integrity }}</code>
          </div>
          <div class="git-section-label">发现 {{ npmPreview.skills.length }} 个 Skill</div>
          <div v-for="skill in npmPreview.skills" :key="skill.name" class="git-skill-row" :class="{ 'git-skill-row--selected': npmSelected.includes(skill.name) }" @click="toggleNpmSkill(skill.name)">
            <div class="git-skill-check"><div class="check-box" :class="{ 'check-box--checked': npmSelected.includes(skill.name) }"><CheckIcon v-if="npmSelected.includes(skill.name)" :size="12" /></div></div>
            <div class="git-skill-info">
              <div class="git-skill-name">{{ skill.name }} <span v-if="skill.conflict" class="npm-conflict">目标已存在</span></div>
              <div class="git-skill-desc">{{ skill.description || '无描述' }}</div>
              <div class="git-skill-path">{{ skill.sourceDirectory }} → {{ skill.defaultTargetDirectory }}</div>
            </div>
          </div>
          <div class="git-section-label">管理方式</div>
          <div class="git-mode-group">
            <QRadio v-model="npmMode" value="skill" label="导入为 Skill" />
            <QRadio v-model="npmMode" value="repo" label="管理为 Repo" />
          </div>
          <div class="form-group">
            <label class="form-label">目标路径（可选）</label>
            <input v-model="npmTargetPath" class="qqx-input" :placeholder="npmMode === 'repo' ? `repos/${npmDefaultRepoName}` : 'skills'" />
          </div>
          <div v-if="npmMode === 'repo'" class="npm-source-grid">
            <div class="form-group">
              <label class="form-label">Git remote（可选）</label>
              <input v-model="npmRemote" class="qqx-input" placeholder="留空时创建本地独立仓库" />
            </div>
            <div class="form-group">
              <label class="form-label">分支（可选）</label>
              <input v-model="npmBranch" class="qqx-input" placeholder="使用远端默认分支" />
            </div>
          </div>
          <label v-if="npmSelectedHasConflict && npmMode === 'skill'" class="npm-force-confirm">
            <input v-model="npmForce" type="checkbox" />
            我已确认覆盖所选的同名 Skill
          </label>
          <div class="npm-preview-action">
            <QButton type="primary" :disabled="npmSelected.length === 0 || npmImporting || (npmSelectedHasConflict && npmMode === 'skill' && !npmForce)" @click="executeNpmImport">
              {{ npmImporting ? '导入中...' : `导入 ${npmSelected.length} 个 Skill` }}
            </QButton>
          </div>
        </div>
      </div>
    </div>

    <!-- Step: validate -->
    <div v-if="step === 'validate'" class="import-step">
      <div v-if="validationLoading" class="loading-state">
        <LoaderIcon :size="24" class="spin" />
        <p>验证中...</p>
      </div>
      <div v-else-if="validationError" class="state-card state-card--error">
        <div class="state-card__inner">
          <XCircleIcon :size="20" />
          <span>{{ validationError }}</span>
        </div>
      </div>
      <div v-else-if="validationResult">
        <div class="result-card">
          <div class="result-card__icon">
            <CheckCircleIcon :size="22" class="icon-success" />
          </div>
          <div class="result-card__body">
            <p class="result-name">{{ validationResult.skillName }}</p>
            <p class="result-desc">{{ validationResult.description || '无描述' }}</p>
            <p class="result-meta">{{ validationResult.fileCount }} 个文件</p>
          </div>
        </div>

        <!-- Conflict warning for new import -->
        <div v-if="validationResult.conflict?.exists && !existingSkillName" class="conflict-warning">
          <AlertTriangleIcon :size="18" />
          <div class="conflict-content">
            <p class="conflict-text">同名技能已存在: {{ validationResult.conflict.existingPath }}</p>
            <div class="conflict-actions">
              <div class="conflict-radio-group">
                <QRadio v-model="conflictAction" value="rename" label="重命名" />
                <QRadio v-model="conflictAction" value="overwrite" label="覆盖" />
              </div>
              <div v-if="conflictAction === 'rename'" class="rename-input-group">
                <label class="rename-label">新名称:</label>
                <input
                  v-model="renameTo"
                  class="qqx-input rename-input"
                  :placeholder="validationResult.skillName"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step: diff (update mode only) -->
    <div v-if="step === 'diff'" class="import-step">
      <div v-if="diffLoading" class="loading-state">
        <LoaderIcon :size="24" class="spin" />
        <p>加载差异对比...</p>
      </div>
      <div v-else-if="diffError" class="state-card state-card--error">
        <div class="state-card__inner">
          <XCircleIcon :size="20" />
          <span>{{ diffError }}</span>
        </div>
      </div>
      <div v-else-if="diffResult">
        <!-- Summary stats -->
        <div class="diff-summary">
          <div class="diff-stat diff-stat--unchanged">
            <FileTextIcon :size="15" />
            <span>{{ diffResult.summary.unchanged }} 未改变</span>
          </div>
          <div class="diff-stat diff-stat--added">
            <span>+{{ diffResult.summary.added }} 新增</span>
          </div>
          <div class="diff-stat diff-stat--modified">
            <span>~{{ diffResult.summary.modified }} 修改</span>
          </div>
          <div class="diff-stat diff-stat--removed">
            <span>-{{ diffResult.summary.removed }} 删除</span>
          </div>
        </div>

        <!-- File list -->
        <div class="diff-files">
          <div
            v-for="file in diffResult.files"
            :key="file.path"
            class="diff-file-row"
            :class="{ 'diff-file-row--expanded': expandedFile === file.path }"
            @click="toggleFile(file)"
          >
            <span class="file-status" :class="'file-status--' + file.status">
              {{ statusLabel(file.status) }}
            </span>
            <span class="file-path">{{ file.path }}</span>
            <ChevronRightIcon :size="14" class="expand-arrow" :class="{ rotated: expandedFile === file.path }" />
          </div>
          <div v-if="expandedFile && expandedFileContent !== null" class="diff-file-expanded">
            <QDiffViewer
              :repo-content="expandedFileContent.repoContent || ''"
              :target-content="expandedFileContent.targetContent || ''"
              :file-path="expandedFile"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Step: result -->
    <div v-if="step === 'result'" class="import-step">
      <div v-if="importError" class="state-card state-card--error">
        <div class="state-card__inner">
          <XCircleIcon :size="24" />
          <span>{{ importError }}</span>
        </div>
      </div>
      <div v-else-if="importResult" class="success-state">
        <CheckCircleIcon :size="36" class="icon-success" />
        <p class="success-title">导入成功</p>
        <div class="success-details">
          <div class="detail-row">
            <span class="detail-label">名称</span>
            <span class="detail-value">{{ importResult.name }}</span>
          </div>
          <div v-if="importResult.skillPath" class="detail-row">
            <span class="detail-label">路径</span>
            <span class="detail-value detail-value--mono">{{ importResult.skillPath }}</span>
          </div>
          <div v-if="importResult.commit" class="detail-row">
            <span class="detail-label">提交</span>
            <span class="detail-value detail-value--mono">{{ importResult.commit }}</span>
          </div>
          <div v-if="importResult.filesCopied" class="detail-row">
            <span class="detail-label">文件</span>
            <span class="detail-value">已复制 {{ importResult.filesCopied }} 个文件</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer actions -->
    <template #footer>
      <template v-if="step === 'source'">
        <QButton type="ghost" @click="closeModal">取消</QButton>
      </template>

      <template v-if="step === 'validate' && !validationLoading">
        <QButton type="ghost" @click="goBackToSource">
          <ChevronLeftIcon :size="16" />
          返回
        </QButton>
        <QButton
          v-if="validationResult"
          type="primary"
          :disabled="executing"
          @click="proceedFromValidate"
        >
          {{ executing ? (existingSkillName ? '加载差异中...' : '导入中...') : (existingSkillName ? '预览差异' : '确认导入') }}
        </QButton>
      </template>

      <template v-if="step === 'diff' && !diffLoading && diffResult">
        <QButton type="ghost" @click="goBackToValidate">
          <ChevronLeftIcon :size="16" />
          返回
        </QButton>
        <QButton
          type="primary"
          :disabled="executing"
          @click="executeUpdate"
        >
          {{ executing ? '执行更新中...' : '执行更新' }}
        </QButton>
      </template>

      <template v-if="step === 'result'">
        <QButton type="primary" @click="closeModal">完成</QButton>
      </template>
    </template>
  </QModal>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import {
  Upload as UploadIcon,
  AlertTriangle as AlertTriangleIcon,
  CheckCircle as CheckCircleIcon,
  XCircle as XCircleIcon,
  Loader as LoaderIcon,
  FileText as FileTextIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Check as CheckIcon,
  FolderOpen as FolderOpenIcon,
} from 'lucide-vue-next'
import { useToast } from '../composables/useToast.js'
import {
  importUploadZip,
  importUploadDirectory,
  importValidate,
  importExecute,
  importPreviewUpdate,
  importExecuteUpdate,
  importCleanup,
  importGitClone,
  importGitExecute,
  previewNpmSource,
  importNpmSource,
} from '../api/index.js'
import QDiffViewer from './QDiffViewer.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  existingSkillName: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'imported'])

const { success, error } = useToast()

// --- Wizard state ---
const step = ref('source') // source | validate | diff | result
const sourceType = ref('folder')

// --- Data state ---
const folderPath = ref('')
const uploadedFolderRoot = ref('')
const selectedFile = ref(null)
const tempPath = ref('')
const extractedRoot = ref('')
const renameTo = ref('')
const conflictAction = ref('rename')

const validationResult = ref(null)
const diffResult = ref(null)
const importResult = ref(null)

// --- Loading / error state ---
const uploading = ref(false)
const validationLoading = ref(false)
const diffLoading = ref(false)
const executing = ref(false)
const validationError = ref('')
const diffError = ref('')
const importError = ref('')
const dragOver = ref(false)

// ── Git state ──
const gitUrl = ref('')
const gitBranch = ref('')
const gitLoading = ref(false)
const gitImporting = ref(false)
const gitError = ref('')
const gitSkills = ref([])
const gitSelected = ref([])
const gitMode = ref('skill')
const gitTargetDir = ref('third')
const gitSubmodulePath = ref('')
const gitTempPath = ref('')

const npmPackage = ref('')
const npmRegistry = ref('https://registry.npmjs.org/')
const npmVersionSpec = ref('latest')
const npmPreview = ref(null)
const npmSelected = ref([])
const npmMode = ref('skill')
const npmTargetPath = ref('')
const npmRemote = ref('')
const npmBranch = ref('')
const npmLoading = ref(false)
const npmImporting = ref(false)
const npmError = ref('')
const npmForce = ref(false)

const npmDefaultRepoName = computed(() => npmPackage.value.trim().replace(/^@/, '').replace(/\//g, '-').toLowerCase() || 'npm-skills')
const npmSelectedHasConflict = computed(() => Boolean(npmPreview.value?.skills.some(skill => npmSelected.value.includes(skill.name) && skill.conflict)))

const gitSubmoduleDefaultName = computed(() => {
  const url = gitUrl.value.trim()
  if (!url) return 'repo'
  const match = url.match(/\/([^/]+?)(?:\.git)?$/)
  return match ? match[1] : 'repo'
})

// Expanded file in diff list
const expandedFile = ref(null)
const expandedFileContent = ref(null)

// File input ref
const fileInput = ref(null)
const folderInput = ref(null)

// --- Computed ---
const localVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const modalWidth = computed(() => {
  if (step.value === 'diff') return '720px'
  return '560px'
})

const modalTitle = computed(() => {
  if (props.existingSkillName) {
    const titles = {
      source: '选择更新来源',
      validate: '验证来源',
      diff: '差异预览',
      result: '更新结果',
    }
    return titles[step.value] || '更新技能'
  }
  const titles = {
    source: '导入新技能',
    validate: '验证来源',
    diff: '差异预览',
    result: '导入结果',
  }
  return titles[step.value] || '导入技能'
})

const sourceTabs = computed(() => [
  { key: 'folder', label: '本地文件夹' },
  { key: 'zip', label: 'ZIP 文件' },
  { key: 'git', label: 'Git URL' },
  { key: 'npm', label: 'NPM 包' },
])

const sourcePath = computed(() => {
  if (sourceType.value === 'folder') return uploadedFolderRoot.value || folderPath.value.trim()
  if (sourceType.value === 'zip') return extractedRoot.value
  if (sourceType.value === 'git') return gitTempPath.value
  return ''
})

const isUpdateMode = computed(() => Boolean(props.existingSkillName))

// --- Methods ---

function handleClose(val) {
  if (!val) {
    closeModal()
  }
}

function closeModal() {
  cleanupTemporarySources()
  resetState()
  emit('update:modelValue', false)
}

function cleanupTemporarySources() {
  const paths = new Set([tempPath.value, gitTempPath.value].filter(Boolean))
  paths.forEach(path => importCleanup(path).catch(() => {}))
}

function resetState() {
  step.value = 'source'
  folderPath.value = ''
  uploadedFolderRoot.value = ''
  selectedFile.value = null
  tempPath.value = ''
  extractedRoot.value = ''
  renameTo.value = ''
  conflictAction.value = 'rename'
  validationResult.value = null
  diffResult.value = null
  importResult.value = null
  validationError.value = ''
  diffError.value = ''
  importError.value = ''
  uploading.value = false
  validationLoading.value = false
  diffLoading.value = false
  executing.value = false
  expandedFile.value = null
  expandedFileContent.value = null
  // Git state
  gitUrl.value = ''
  gitBranch.value = ''
  gitLoading.value = false
  gitImporting.value = false
  gitError.value = ''
  gitSkills.value = []
  gitSelected.value = []
  gitMode.value = 'skill'
  gitTargetDir.value = 'third'
  gitSubmodulePath.value = ''
  gitTempPath.value = ''
  npmPackage.value = ''
  npmRegistry.value = 'https://registry.npmjs.org/'
  npmVersionSpec.value = 'latest'
  npmPreview.value = null
  npmSelected.value = []
  npmMode.value = 'skill'
  npmTargetPath.value = ''
  npmRemote.value = ''
  npmBranch.value = ''
  npmLoading.value = false
  npmImporting.value = false
  npmError.value = ''
  npmForce.value = false
}

function goBackToSource() {
  step.value = 'source'
  validationResult.value = null
  validationError.value = ''
}

function goBackToValidate() {
  step.value = 'validate'
  diffResult.value = null
  diffError.value = ''
  expandedFile.value = null
  expandedFileContent.value = null
}

function openFilePicker() {
  fileInput.value?.click()
}

function openFolderPicker() {
  folderInput.value?.click()
}

function clearUploadedFolder() {
  if (!uploadedFolderRoot.value && !tempPath.value) return
  const managedTempPath = tempPath.value
  uploadedFolderRoot.value = ''
  extractedRoot.value = ''
  tempPath.value = ''
  if (managedTempPath) importCleanup(managedTempPath).catch(() => {})
}

async function handleFolderSelection(event) {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  if (files.length === 0) {
    validationError.value = '所选文件夹为空'
    return
  }

  uploading.value = true
  validationError.value = ''
  validationResult.value = null
  clearUploadedFolder()

  try {
    const uploadResult = await importUploadDirectory(files)
    tempPath.value = uploadResult.tempPath
    uploadedFolderRoot.value = uploadResult.extractedRoot
    const result = await importValidate({ sourceType: 'folder', sourcePath: uploadedFolderRoot.value })
    showValidationResult(result)
  } catch (err) {
    validationError.value = err.message || '文件夹读取或验证失败'
  } finally {
    uploading.value = false
  }
}

function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (file) {
    selectedFile.value = file
  }
}

function handleDrop(e) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.name.endsWith('.zip')) {
    selectedFile.value = file
  } else if (file) {
    error('请选择 .zip 格式的文件')
  }
}

async function validateSource() {
  if (sourceType.value === 'folder' && !folderPath.value.trim()) return
  if (sourceType.value === 'zip') {
    await uploadAndValidate()
    return
  }
  if (sourceType.value === 'git') {
    await validateGitUrl()
    return
  }

  validationLoading.value = true
  validationError.value = ''
  validationResult.value = null

  try {
    const result = await importValidate({ sourceType: sourceType.value, sourcePath: sourcePath.value })
    showValidationResult(result)
  } catch (err) {
    validationError.value = err.message || '验证失败'
  } finally {
    validationLoading.value = false
  }
}

async function uploadAndValidate() {
  if (!selectedFile.value) return

  uploading.value = true
  validationError.value = ''
  validationResult.value = null
  if (tempPath.value) {
    importCleanup(tempPath.value).catch(() => {})
    tempPath.value = ''
  }

  try {
    const uploadResult = await importUploadZip(selectedFile.value)
    tempPath.value = uploadResult.tempPath
    extractedRoot.value = uploadResult.extractedRoot

    const result = await importValidate({ sourceType: 'zip', sourcePath: extractedRoot.value })
    showValidationResult(result)
  } catch (err) {
    validationError.value = err.message || '上传或验证失败'
  } finally {
    uploading.value = false
  }
}

function showValidationResult(result) {
  step.value = 'validate'
  if (!result.valid) {
    validationResult.value = null
    validationError.value = result.error || '未找到有效的 SKILL.md'
    return
  }
  validationError.value = ''
  validationResult.value = result
}

async function proceedFromValidate() {
  if (isUpdateMode.value) {
    // Go to diff preview for update
    await loadDiffPreview()
  } else {
    await executeImport()
  }
}

async function loadDiffPreview() {
  if (!validationResult.value) return

  diffLoading.value = true
  diffError.value = ''
  diffResult.value = null

  try {
    const result = await importPreviewUpdate({
      sourcePath: sourcePath.value,
      skillName: props.existingSkillName,
    })
    diffResult.value = result
    step.value = 'diff'
  } catch (err) {
    diffError.value = err.message || '加载差异失败'
  } finally {
    diffLoading.value = false
  }
}

async function executeImport() {
  if (!validationResult.value) return

  executing.value = true
  importError.value = ''
  importResult.value = null

  try {
    const body = {
      sourceType: sourceType.value,
      sourcePath: sourcePath.value,
    }
    if (tempPath.value) body.tempPath = tempPath.value
    if (conflictAction.value === 'rename' && renameTo.value.trim()) {
      body.renameTo = renameTo.value.trim()
    }
    if (conflictAction.value === 'overwrite') {
      body.force = true
    }

    const result = await importExecute(body)
    importResult.value = result
    step.value = 'result'
    success(`技能 "${result.name}" 导入成功`)
    emit('imported')
  } catch (err) {
    importError.value = err.message || '导入失败'
    step.value = 'result'
  } finally {
    executing.value = false
  }
}

async function executeUpdate() {
  if (!diffResult.value || !validationResult.value) return

  executing.value = true
  importError.value = ''
  importResult.value = null

  try {
    const body = {
      sourcePath: sourcePath.value,
      skillName: props.existingSkillName,
    }
    if (tempPath.value) body.tempPath = tempPath.value

    const result = await importExecuteUpdate(body)
    importResult.value = result
    step.value = 'result'
    success(`技能 "${result.name}" 更新成功`)
    emit('imported')
  } catch (err) {
    importError.value = err.message || '更新失败'
    step.value = 'result'
  } finally {
    executing.value = false
  }
}

// ── Git import flow ──

async function validateGitUrl() {
  if (!gitUrl.value.trim()) return
  gitLoading.value = true
  gitError.value = ''
  gitSkills.value = []
  gitSelected.value = []
  try {
    const result = await importGitClone(gitUrl.value.trim(), gitBranch.value.trim() || undefined)
    gitSkills.value = result.skills
    gitSelected.value = result.skills.map(s => s.name)
    gitTempPath.value = result.tempPath
  } catch (err) {
    gitError.value = err.message || '克隆失败'
  } finally {
    gitLoading.value = false
  }
}

function toggleGitSkill(name) {
  const idx = gitSelected.value.indexOf(name)
  if (idx >= 0) gitSelected.value.splice(idx, 1)
  else gitSelected.value.push(name)
}

async function executeGitImport() {
  if (gitSelected.value.length === 0) return
  gitImporting.value = true
  gitError.value = ''
  importError.value = ''
  try {
    const body = {
      mode: gitMode.value,
      url: gitUrl.value.trim(),
      branch: gitBranch.value.trim() || undefined,
      selectedSkills: gitSelected.value,
      tempPath: gitTempPath.value,
    }
    if (gitMode.value === 'submodule') {
      body.targetPath = gitSubmodulePath.value.trim() || `repos/third/${gitSubmoduleDefaultName.value}`
    } else {
      body.targetDir = gitTargetDir.value.trim() || 'third'
    }
    const result = await importGitExecute(body)
    importResult.value = {
      name: gitMode.value === 'submodule' ? `submodule: ${result.submodulePath}` : `${result.imported.length} 个技能`,
      skillPath: gitMode.value === 'submodule' ? result.submodulePath : result.targetPath,
      commit: result.commit || result.imported?.[0]?.commit,
      filesCopied: result.imported?.reduce((s, r) => s + (r.filesCopied || 0), 0),
    }
    step.value = 'result'
    const label = gitMode.value === 'submodule' ? `已添加 submodule: ${result.submodulePath}` : `已导入 ${result.imported.length} 个技能`
    success(label)
    emit('imported')
    if (gitTempPath.value) { importCleanup(gitTempPath.value).catch(() => {}) }
  } catch (err) {
    importError.value = err.message || '导入失败'
    step.value = 'result'
  } finally {
    gitImporting.value = false
  }
}

async function previewNpm() {
  if (!npmPackage.value.trim()) return
  npmLoading.value = true
  npmError.value = ''
  npmPreview.value = null
  try {
    npmPreview.value = await previewNpmSource({
      package: npmPackage.value.trim(),
      registry: npmRegistry.value.trim(),
      versionSpec: npmVersionSpec.value.trim() || 'latest',
    })
    npmSelected.value = npmPreview.value.skills.map(skill => skill.name)
    npmForce.value = false
  } catch (err) {
    npmError.value = err.message || 'NPM 来源验证失败'
  } finally {
    npmLoading.value = false
  }
}

function toggleNpmSkill(name) {
  const index = npmSelected.value.indexOf(name)
  if (index >= 0) npmSelected.value.splice(index, 1)
  else npmSelected.value.push(name)
}

async function executeNpmImport() {
  if (!npmPreview.value || npmSelected.value.length === 0) return
  npmImporting.value = true
  npmError.value = ''
  try {
    const body = {
      token: npmPreview.value.token,
      mode: npmMode.value,
      selectedSkills: npmSelected.value,
      force: npmForce.value,
    }
    if (npmTargetPath.value.trim()) body.targetPath = npmTargetPath.value.trim()
    if (npmMode.value === 'repo' && npmRemote.value.trim()) body.remote = npmRemote.value.trim()
    if (npmMode.value === 'repo' && npmBranch.value.trim()) body.branch = npmBranch.value.trim()
    const result = await importNpmSource(body)
    importResult.value = {
      name: `${result.imported.length} 个 Skill`,
      skillPath: result.source.targetPath,
      filesCopied: result.imported.reduce((total, item) => total + Object.keys(item.fileHashes || {}).length, 0),
    }
    step.value = 'result'
    success(`已导入 ${result.imported.length} 个 Skill`)
    emit('imported')
  } catch (err) {
    npmError.value = err.message || 'NPM 来源导入失败'
  } finally {
    npmImporting.value = false
  }
}

function toggleFile(file) {
  if (expandedFile.value === file.path) {
    expandedFile.value = null
    expandedFileContent.value = null
    return
  }
  expandedFile.value = file.path
  // Content not available from preview API; set a placeholder
  expandedFileContent.value = {
    repoContent: null,
    targetContent: null,
  }
}

function statusLabel(status) {
  const labels = {
    added: '新增',
    modified: '修改',
    removed: '删除',
    unchanged: '不变',
  }
  return labels[status] || status
}

// --- Cleanup on unmount ---
onUnmounted(() => {
  cleanupTemporarySources()
})

// Reset when modal opens
watch(() => props.modelValue, (val) => {
  if (!val) {
    cleanupTemporarySources()
    resetState()
  }
})
</script>

<style scoped>
.import-step {
  min-height: 200px;
}

/* ── Source panels ──────────────────────────────── */

.source-panel {
  margin-top: var(--qqx-space-md);
}

.npm-source-grid {
  display: grid;
  grid-template-columns: 1fr 180px;
  gap: var(--qqx-space-md);
  margin-top: var(--qqx-space-md);
}

.npm-preview-action {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--qqx-space-md);
}

.npm-preview {
  margin-top: var(--qqx-space-md);
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

.npm-resolution {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--qqx-space-md);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-subtle);
  overflow-wrap: anywhere;
}

.npm-conflict {
  color: var(--qqx-warning);
  font-size: var(--qqx-font-size-small);
}

.npm-force-confirm {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  color: var(--qqx-warning);
  font-size: var(--qqx-font-size-small);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-sm);
}

.form-label {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.input-row {
  display: flex;
  gap: var(--qqx-space-sm);
}

.input-row--folder .qqx-input {
  min-width: 0;
}

.native-folder-input {
  display: none;
}

.folder-error {
  margin-top: var(--qqx-space-md);
}

.qqx-input {
  flex: 1;
  height: 40px;
  padding: 8px 12px;
  border: 1px solid var(--qqx-input-border);
  border-radius: var(--qqx-radius-xs);
  background: var(--qqx-input-bg);
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-label);
  font-family: inherit;
  transition: border-color var(--qqx-transition), box-shadow var(--qqx-transition);
  outline: none;
}

.qqx-input:focus {
  border-color: var(--qqx-brand);
  box-shadow: var(--qqx-shadow-focus);
}

.qqx-input::placeholder {
  color: var(--qqx-text-tertiary);
}

/* ── Drop zone ──────────────────────────────────── */

.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-2xl) var(--qqx-space-xl);
  border: 2px dashed var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-subtle);
  cursor: pointer;
  transition: border-color var(--qqx-transition),
              background var(--qqx-transition);
  text-align: center;
}

.drop-zone:hover,
.drop-zone--active {
  border-color: var(--qqx-brand);
  background: var(--qqx-brand-light);
}

.drop-zone--has-file {
  border-style: solid;
  border-color: var(--qqx-brand);
  background: var(--qqx-brand-light);
}

.drop-zone__icon {
  color: var(--qqx-text-tertiary);
  transition: color var(--qqx-transition);
}

.drop-zone:hover .drop-zone__icon,
.drop-zone--active .drop-zone__icon {
  color: var(--qqx-brand);
}

.drop-zone__text {
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-primary);
  margin: 0;
  word-break: break-all;
}

.drop-zone__hint {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  margin: 0;
}

.zip-actions {
  display: flex;
  justify-content: center;
  margin-top: var(--qqx-space-md);
}

/* ── Info alert ─────────────────────────────────── */

.info-alert {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-md);
  background: var(--qqx-brand-light);
  border: 1px solid rgba(0, 153, 255, 0.2);
  border-radius: var(--qqx-radius-md);
  color: var(--qqx-brand);
  font-size: var(--qqx-font-size-label);
  margin-top: var(--qqx-space-md);
}

/* ── Result card (validate step) ────────────────── */

.result-card {
  display: flex;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-lg);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-surface);
}

.result-card__icon {
  display: flex;
  flex-shrink: 0;
}

.icon-success {
  color: #22c55e;
}

.result-card__body {
  flex: 1;
  min-width: 0;
}

.result-name {
  font-size: var(--qqx-font-size-body);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  margin: 0 0 4px;
}

.result-desc {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  margin: 0 0 4px;
  line-height: 1.4;
}

.result-meta {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  margin: 0;
}

/* ── Conflict warning ───────────────────────────── */

.conflict-warning {
  display: flex;
  gap: var(--qqx-space-sm);
  margin-top: var(--qqx-space-lg);
  padding: var(--qqx-space-md);
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: var(--qqx-radius-md);
  color: #d97706;
}

.conflict-content {
  flex: 1;
}

.conflict-text {
  margin: 0 0 var(--qqx-space-sm);
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-primary);
}

.conflict-actions {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-sm);
}

.conflict-radio-group {
  display: flex;
  gap: var(--qqx-space-lg);
}

.rename-input-group {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
}

.rename-label {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  white-space: nowrap;
}

.rename-input {
  max-width: 280px;
}

/* ── Loading / Error states ──────────────────────── */

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-2xl);
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-label);
}

.spin {
  animation: qqx-spin 1s linear infinite;
}

@keyframes qqx-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.state-card {
  padding: var(--qqx-space-lg);
  border-radius: var(--qqx-radius-md);
}

.state-card--error {
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.state-card__inner {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  color: #dc2626;
  font-size: var(--qqx-font-size-label);
}

/* ── Success state ───────────────────────────────── */

.success-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-xl) 0;
  text-align: center;
}

.success-title {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  margin: 0;
}

.success-details {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-md);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-surface);
  text-align: left;
}

.detail-row {
  display: flex;
  gap: var(--qqx-space-sm);
  font-size: var(--qqx-font-size-label);
}

.detail-label {
  color: var(--qqx-text-tertiary);
  min-width: 48px;
  flex-shrink: 0;
}

.detail-value {
  color: var(--qqx-text-primary);
  word-break: break-all;
}

.detail-value--mono {
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: var(--qqx-font-size-small);
}

/* ── Diff summary ────────────────────────────────── */

.diff-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--qqx-space-sm);
  margin-bottom: var(--qqx-space-lg);
}

.diff-stat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--qqx-radius-full);
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
}

.diff-stat--unchanged {
  background: var(--qqx-diff-unchanged-tag-bg);
  color: var(--qqx-diff-unchanged-tag-text);
}

.diff-stat--added {
  background: var(--qqx-diff-added-tag-bg);
  color: var(--qqx-diff-added-tag-text);
}

.diff-stat--modified {
  background: var(--qqx-diff-modified-tag-bg);
  color: var(--qqx-diff-modified-tag-text);
}

.diff-stat--removed {
  background: var(--qqx-diff-removed-tag-bg);
  color: var(--qqx-diff-removed-tag-text);
}

/* ── Diff file list ──────────────────────────────── */

.diff-files {
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  overflow: hidden;
}

.diff-file-row {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  cursor: pointer;
  transition: background var(--qqx-transition);
  border-bottom: 1px solid var(--qqx-border-color);
}

.diff-file-row:last-child {
  border-bottom: none;
}

.diff-file-row:hover {
  background: var(--qqx-bg-hover);
}

.diff-file-row--expanded {
  background: var(--qqx-bg-subtle);
}

.file-status {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: var(--qqx-radius-full);
  font-weight: var(--qqx-font-medium);
  flex-shrink: 0;
  text-transform: uppercase;
}

.file-status--added {
  background: var(--qqx-diff-added-tag-bg);
  color: var(--qqx-diff-added-tag-text);
}

.file-status--modified {
  background: var(--qqx-diff-modified-tag-bg);
  color: var(--qqx-diff-modified-tag-text);
}

.file-status--removed {
  background: var(--qqx-diff-removed-tag-bg);
  color: var(--qqx-diff-removed-tag-text);
}

.file-status--unchanged {
  background: var(--qqx-diff-unchanged-tag-bg);
  color: var(--qqx-diff-unchanged-tag-text);
}

.file-path {
  flex: 1;
  font-size: var(--qqx-font-size-small);
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  color: var(--qqx-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.expand-arrow {
  flex-shrink: 0;
  color: var(--qqx-text-tertiary);
  transition: transform var(--qqx-transition);
}

.expand-arrow.rotated {
  transform: rotate(90deg);
}

.diff-file-expanded {
  border-top: 1px solid var(--qqx-border-color);
  padding: var(--qqx-space-sm) var(--qqx-space-md) var(--qqx-space-md);
  background: var(--qqx-bg-card);
}

/* ── Git import UI ─────────────────────────────────── */

.git-skills-section { margin-top: var(--qqx-space-lg); }

.git-section-label {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
  margin-bottom: var(--qqx-space-sm);
}

.git-skill-row {
  display: flex;
  align-items: flex-start;
  gap: var(--qqx-space-sm);
  padding: var(--qqx-space-sm) var(--qqx-space-md);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  cursor: pointer;
  transition: border-color var(--qqx-transition), background var(--qqx-transition);
  margin-bottom: var(--qqx-space-xs);
}

.git-skill-row:hover { border-color: var(--qqx-brand); }

.git-skill-row--selected {
  border-color: var(--qqx-brand);
  background: var(--qqx-brand-light);
}

.git-skill-check { flex-shrink: 0; padding-top: 2px; }

.check-box {
  width: 18px; height: 18px;
  border: 2px solid var(--qqx-border-color);
  border-radius: 3px;
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  transition: all var(--qqx-transition);
}

.check-box--checked {
  background: var(--qqx-brand);
  border-color: var(--qqx-brand);
}

.git-skill-info { flex: 1; min-width: 0; }

.git-skill-name {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
  color: var(--qqx-text-primary);
}

.git-skill-desc {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
  margin-top: 2px; line-height: 1.3;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.git-skill-path {
  font-size: var(--qqx-font-size-tiny);
  color: var(--qqx-text-tertiary);
  font-family: 'SF Mono', 'Fira Code', monospace;
  margin-top: 2px;
}

.git-mode-group { display: flex; gap: var(--qqx-space-lg); }

.form-hint {
  font-size: var(--qqx-font-size-tiny);
  color: var(--qqx-text-tertiary);
  margin: var(--qqx-space-xs) 0 0;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

@media (max-width: 600px) {
  .input-row--folder {
    flex-wrap: wrap;
  }

  .input-row--folder .qqx-input {
    flex-basis: 100%;
  }
}
</style>
