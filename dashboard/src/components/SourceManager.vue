<template>
  <section class="sources-page">
    <header class="page-header">
      <div>
        <h2>NPM 来源</h2>
        <p>以包为单位管理版本、完整性与 Skill 映射</p>
      </div>
      <QButton type="secondary" size="small" :disabled="loading" @click="load">刷新</QButton>
    </header>

    <div v-if="errorMessage" class="notice notice--error">{{ errorMessage }}</div>
    <div v-if="loading" class="empty-state">加载来源中...</div>
    <div v-else-if="sources.length === 0" class="empty-state">尚未添加受管来源</div>
    <div v-else class="source-list">
      <article
        v-for="source in sources"
        :key="source.id"
        :data-source-id="source.id"
        class="source-card"
        :class="{ 'source-card--selected': route.query.source === source.id }"
      >
        <div class="source-card__top">
          <div>
            <div class="source-title">{{ source.package }}</div>
            <div class="source-meta">
              <span>{{ source.resolvedVersion }} · {{ source.mode === 'repo' ? 'Repo' : 'Skill' }}</span>
              <template v-if="source.repository">
                <button
                  class="entity-link"
                  :disabled="!source.repository.exists"
                  @click="openRepository(source.repository.path)"
                >
                  {{ source.repository.name }} →
                </button>
                <span v-if="!source.repository.exists" class="mapping-missing">仓库缺失</span>
              </template>
              <code v-else>{{ source.targetPath }}</code>
            </div>
          </div>
          <span class="status-pill" :data-status="checks[source.id]?.status">{{ sourceStatusLabel(checks[source.id]?.status) }}</span>
        </div>
        <div class="mapping-list">
          <div v-for="skill in source.skills" :key="skill.path" class="mapping-row">
            <code>{{ skill.sourceDirectory }} →</code>
            <button
              class="skill-link"
              :disabled="!skill.available"
              :title="skill.available ? '查看 Skill' : '映射存在，但当前未发现对应 Skill'"
              @click="openSkill(skill)"
            >
              {{ skill.name }}
            </button>
            <span v-if="!skill.available" class="mapping-missing">Skill 缺失</span>
          </div>
        </div>
        <div class="source-meta">
          <span>更新时间 {{ formatTime(source.updatedAt) }}</span>
          <span v-if="source.mode === 'repo'">{{ source.remoteConfigured ? '已配置远端' : '尚未配置远端' }}</span>
        </div>
        <div class="actions">
          <QButton type="ghost" size="small" :disabled="busy === source.id" @click="runCheck(source)">检查更新</QButton>
          <QButton type="secondary" size="small" :disabled="busy === source.id" @click="runPreview(source)">查看差异</QButton>
        </div>

        <div v-if="previews[source.id]" class="preview-panel">
          <div class="preview-summary">
            <strong>{{ previews[source.id].currentVersion }} → {{ previews[source.id].resolvedVersion }}</strong>
            <span>新增 {{ previews[source.id].summary.added }}</span>
            <span>修改 {{ previews[source.id].summary.modified }}</span>
            <span>删除 {{ previews[source.id].summary.deleted }}</span>
          </div>
          <div v-if="previews[source.id].repoDirty" class="notice notice--error">Repo 工作树有未提交修改，dry-run 可继续但不能更新</div>
          <div v-if="previews[source.id].localModified" class="notice notice--warning">
            受管路径存在本地修改
            <label><input v-model="forceConfirmed[source.id]" type="checkbox" /> 我已查看差异并允许覆盖</label>
          </div>
          <div v-if="destructiveCount(previews[source.id])" class="notice notice--warning">本次更新会删除 {{ destructiveCount(previews[source.id]) }} 个文件</div>
          <div class="diff-list">
            <code v-for="file in previews[source.id].files" :key="file.path"><span :data-change="file.status">{{ file.status }}</span> {{ file.path }}</code>
            <span v-if="previews[source.id].files.length === 0">Skill 内容没有变化</span>
          </div>
          <div class="actions">
            <QButton type="ghost" size="small" @click="runDryRun(source)">Dry run</QButton>
            <QButton type="primary" size="small" :disabled="!canApplyUpdate(previews[source.id], forceConfirmed[source.id]) || busy === source.id" @click="runUpdate(source)">一键更新</QButton>
          </div>
        </div>
      </article>
    </div>

    <QModal
      v-model="identityDialog.open"
      title="设置 Git 身份"
      width="440px"
      :close-on-overlay="false"
    >
      <div class="identity-form">
        <p>提交前需要为这个仓库设置身份</p>
        <code>{{ identityDialog.repository }}</code>
        <QInput
          v-model="identityDialog.name"
          label="用户名"
          placeholder="例如 kexjhhuang"
        />
        <QInput
          v-model="identityDialog.email"
          label="邮箱"
          placeholder="例如 name@example.com"
          type="email"
        />
        <div v-if="identityDialog.error" class="notice notice--error">
          {{ identityDialog.error }}
        </div>
      </div>
      <template #footer>
        <QButton type="ghost" :disabled="identityDialog.saving" @click="closeIdentityDialog">
          取消
        </QButton>
        <QButton type="primary" :disabled="identityDialog.saving" @click="saveGitIdentity">
          {{ identityDialog.saving ? '保存中...' : '保存并重试' }}
        </QButton>
      </template>
    </QModal>
  </section>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import QButton from './QButton.vue'
import QInput from './QInput.vue'
import QModal from './QModal.vue'
import {
  checkSource,
  configureGitIdentity,
  fetchSources,
  previewSourceUpdate,
  updateSource,
} from '../api/index.js'
import {
  gitIdentityRequestFromError,
  validateGitIdentity,
} from '../sources/gitIdentity.js'
import { canApplyUpdate, destructiveCount, sourceStatusLabel } from '../sources/sourceState.js'
import { useSkillDetail } from '../composables/useSkillDetail.js'

const sources = ref([])
const route = useRoute()
const router = useRouter()
const { show: showSkill } = useSkillDetail()
const loading = ref(false)
const busy = ref('')
const errorMessage = ref('')
const checks = reactive({})
const previews = reactive({})
const forceConfirmed = reactive({})
const identityDialog = reactive({
  open: false,
  repository: '.',
  name: '',
  email: '',
  source: null,
  saving: false,
  error: '',
})

function formatTime(value) {
  if (!value) return '未知'
  return new Date(value).toLocaleString()
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    sources.value = await fetchSources()
    await nextTick()
    scrollToSelectedSource()
  } catch (error) {
    errorMessage.value = error.message || '来源加载失败'
  } finally {
    loading.value = false
  }
}

function openRepository(path) {
  router.push({ name: 'repos', query: { repo: path } })
}

function openSkill(skill) {
  if (skill.available && skill.skillId) showSkill(skill.skillId)
}

function scrollToSelectedSource() {
  const sourceId = route.query.source
  if (!sourceId) return
  const card = document.querySelector(`[data-source-id="${CSS.escape(sourceId)}"]`)
  card?.scrollIntoView({ block: 'center' })
}

async function runCheck(source) {
  busy.value = source.id
  errorMessage.value = ''
  try {
    checks[source.id] = await checkSource(source.id)
  } catch (error) {
    errorMessage.value = error.message || '检查更新失败'
  } finally {
    busy.value = ''
  }
}

async function runPreview(source) {
  busy.value = source.id
  errorMessage.value = ''
  try {
    previews[source.id] = await previewSourceUpdate(source.id)
    checks[source.id] = previews[source.id]
    forceConfirmed[source.id] = false
  } catch (error) {
    errorMessage.value = error.message || '差异预览失败'
  } finally {
    busy.value = ''
  }
}

async function runDryRun(source) {
  const preview = previews[source.id]
  if (!preview) return
  busy.value = source.id
  try {
    checks[source.id] = await updateSource(source.id, preview.token, { dryRun: true })
    await runPreview(source)
  } catch (error) {
    errorMessage.value = error.message || 'Dry run 失败'
  } finally {
    busy.value = ''
  }
}

async function runUpdate(source) {
  const preview = previews[source.id]
  if (!canApplyUpdate(preview, forceConfirmed[source.id])) return
  if (destructiveCount(preview) && !window.confirm(`确认删除 ${destructiveCount(preview)} 个受管文件`)) return
  busy.value = source.id
  try {
    checks[source.id] = await updateSource(source.id, preview.token, { force: Boolean(forceConfirmed[source.id]) })
    delete previews[source.id]
    await load()
  } catch (error) {
    const request = gitIdentityRequestFromError(error)
    if (request) {
      identityDialog.repository = request.repository
      identityDialog.source = source
      identityDialog.error = ''
      identityDialog.open = true
    } else {
      errorMessage.value = error.message || '更新失败'
    }
  } finally {
    busy.value = ''
  }
}

function closeIdentityDialog() {
  if (identityDialog.saving) return
  identityDialog.open = false
  identityDialog.source = null
  identityDialog.error = ''
}

async function saveGitIdentity() {
  const validationError = validateGitIdentity(identityDialog.name, identityDialog.email)
  if (validationError) {
    identityDialog.error = validationError
    return
  }
  const source = identityDialog.source
  identityDialog.saving = true
  identityDialog.error = ''
  try {
    await configureGitIdentity(
      identityDialog.repository,
      identityDialog.name.trim(),
      identityDialog.email.trim(),
    )
    identityDialog.open = false
    identityDialog.source = null
    if (source) {
      await runPreview(source)
      await runUpdate(source)
    }
  } catch (error) {
    identityDialog.error = error.message || 'Git 身份保存失败'
  } finally {
    identityDialog.saving = false
  }
}

onMounted(load)
watch(() => route.query.source, () => nextTick(scrollToSelectedSource))
</script>

<style scoped>
.sources-page { display: flex; flex-direction: column; gap: var(--qqx-space-lg); }
.page-header, .source-card__top, .actions, .source-meta, .preview-summary { display: flex; align-items: center; justify-content: space-between; gap: var(--qqx-space-md); }
.page-header h2 { margin: 0; color: var(--qqx-text-primary); }
.page-header p { margin: 4px 0 0; color: var(--qqx-text-secondary); }
.source-list { display: grid; gap: var(--qqx-space-md); }
.source-card { padding: var(--qqx-space-lg); border: 1px solid var(--qqx-border-color); border-radius: var(--qqx-radius-lg); background: var(--qqx-bg-card); }
.source-card--selected { border-color: var(--qqx-brand-color); box-shadow: 0 0 0 2px color-mix(in srgb, var(--qqx-brand-color) 16%, transparent); }
.source-title { font-weight: var(--qqx-font-semibold); color: var(--qqx-text-primary); }
.source-meta { margin-top: var(--qqx-space-sm); justify-content: flex-start; color: var(--qqx-text-secondary); font-size: var(--qqx-font-size-small); }
.status-pill { padding: 4px 10px; border-radius: var(--qqx-radius-full); background: var(--qqx-bg-subtle); font-size: var(--qqx-font-size-small); }
.status-pill[data-status="update-available"] { color: var(--qqx-warning); }
.status-pill[data-status="up-to-date"] { color: var(--qqx-success); }
.mapping-list, .diff-list { display: flex; flex-direction: column; gap: 6px; margin: var(--qqx-space-md) 0; color: var(--qqx-text-secondary); }
.mapping-row { display: flex; align-items: center; gap: var(--qqx-space-sm); min-width: 0; }
.entity-link, .skill-link { border: 0; padding: 0; background: transparent; color: var(--qqx-brand-color); cursor: pointer; font: inherit; }
.entity-link:disabled, .skill-link:disabled { color: var(--qqx-text-tertiary); cursor: default; }
.mapping-missing { color: var(--qqx-warning); font-size: var(--qqx-font-size-small); }
.actions { justify-content: flex-end; }
.preview-panel { margin-top: var(--qqx-space-md); padding-top: var(--qqx-space-md); border-top: 1px solid var(--qqx-border-color); }
.preview-summary { justify-content: flex-start; flex-wrap: wrap; }
.notice, .empty-state { padding: var(--qqx-space-md); border-radius: var(--qqx-radius-md); background: var(--qqx-bg-subtle); color: var(--qqx-text-secondary); }
.notice--error { color: var(--qqx-error); }
.notice--warning { color: var(--qqx-warning); }
.identity-form { display: flex; flex-direction: column; gap: var(--qqx-space-md); }
.identity-form p { margin: 0; color: var(--qqx-text-secondary); }
.identity-form code { padding: var(--qqx-space-sm); border-radius: var(--qqx-radius-xs); background: var(--qqx-bg-subtle); color: var(--qqx-text-primary); }
</style>
