<template>
  <section class="onboarding-shell" aria-labelledby="onboarding-title">
    <div v-if="!result" class="onboarding-layout">
      <div class="onboarding-intro">
        <div class="onboarding-mark"><Sparkles :size="22" /></div>
        <div class="onboarding-kicker">首次设置</div>
        <h2 id="onboarding-title">准备你的 Skill Workspace</h2>
        <p>
          Workspace 是 Skill 的本地管理目录，skillreg 会在这里保存内容、记录 Git 历史并同步到不同 Agent
        </p>
        <div class="onboarding-steps" aria-label="设置流程">
          <div class="onboarding-step onboarding-step--active">
            <span>1</span>
            <div><strong>准备 Workspace</strong><small>新建或选择已有目录</small></div>
          </div>
          <div class="onboarding-step">
            <span>2</span>
            <div><strong>导入首个 Skill</strong><small>本地目录、ZIP、Git 或 NPM</small></div>
          </div>
          <div class="onboarding-step">
            <span>3</span>
            <div><strong>配置同步目标</strong><small>同步给 Codex、Claude 等 Agent</small></div>
          </div>
        </div>
      </div>

      <QCard class="onboarding-card">
        <QTabs v-model="mode" :tabs="tabs">
          <div class="onboarding-form">
            <template v-if="mode === 'create'">
              <div class="form-heading">
                <FolderPlus :size="20" />
                <div>
                  <h3>创建新的 Workspace</h3>
                  <p>自动创建目录、初始化 Git 并生成首个提交</p>
                </div>
              </div>
              <QInput
                v-model="path"
                label="保存位置"
                placeholder="例如: ~/my-skills"
                :disabled="saving"
              />
              <div class="git-note">
                <GitCommit :size="18" />
                <div>
                  <strong>本地 Git 历史会自动开启</strong>
                  <span>首个提交和后续 Skill 变更会自动记录，不会配置远端或自动 push</span>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="form-heading">
                <FolderOpen :size="20" />
                <div>
                  <h3>使用已有 Workspace</h3>
                  <p>目录需要包含 skills/，现有文件不会被改写</p>
                </div>
              </div>
              <QInput
                v-model="path"
                label="Workspace 路径"
                placeholder="例如: ~/my-skills"
                :disabled="saving"
              />
            </template>

            <div v-if="error" class="onboarding-error" role="alert">{{ error }}</div>

            <QButton type="primary" size="large" :disabled="saving || !path.trim()" @click="submit">
              {{ saving ? '正在准备...' : mode === 'create' ? '创建并继续' : '选择并继续' }}
              <ArrowRight v-if="!saving" :size="16" />
            </QButton>
          </div>
        </QTabs>
      </QCard>
    </div>

    <div v-else class="onboarding-success">
      <div class="success-icon"><Check :size="28" /></div>
      <div class="onboarding-kicker">准备完成</div>
      <h2 id="onboarding-title">Workspace 已就绪</h2>
      <p>{{ result.created ? '基础目录和本地版本记录都已准备好，现在可以加入你的第一个 Skill' : '已切换到现有目录，现在可以继续管理和同步 Skill' }}</p>

      <div class="success-summary">
        <div class="summary-row">
          <span>Workspace</span>
          <code>{{ result.workspace_path }}</code>
        </div>
        <div v-if="result.initial_commit" class="summary-row">
          <span>初始提交</span>
          <code>{{ result.initial_commit }}</code>
        </div>
        <div v-if="result.created" class="summary-row">
          <span>远端备份</span>
          <strong>尚未配置</strong>
        </div>
        <div v-else class="summary-row">
          <span>接入方式</span>
          <strong>使用已有目录</strong>
        </div>
      </div>

      <div class="next-actions">
        <button class="next-card next-card--primary" @click="$emit('continue', 'import')">
          <span class="next-index">推荐下一步</span>
          <strong>导入首个 Skill</strong>
          <small>从本地目录、ZIP、Git 或 NPM 开始</small>
          <ArrowRight :size="18" />
        </button>
        <button class="next-card" @click="$emit('continue', 'target')">
          <span class="next-index">随后设置</span>
          <strong>添加同步目标</strong>
          <small>把 Skill 安装到 Agent 的技能目录</small>
          <ArrowRight :size="18" />
        </button>
      </div>

      <QButton type="ghost" size="small" @click="$emit('continue', 'dashboard')">稍后设置，先进入 Dashboard</QButton>
    </div>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ArrowRight, Check, FolderOpen, FolderPlus, GitCommit, Sparkles } from 'lucide-vue-next'
import QButton from './QButton.vue'
import QCard from './QCard.vue'
import QInput from './QInput.vue'
import QTabs from './QTabs.vue'
import { createWorkspace, switchWorkspace } from '../api/index.js'

const emit = defineEmits(['configured', 'continue'])

const tabs = [
  { key: 'create', label: '创建新的' },
  { key: 'existing', label: '使用已有的' },
]

const mode = ref('create')
const path = ref('~/my-skills')
const saving = ref(false)
const error = ref('')
const result = ref(null)

watch(mode, (value) => {
  path.value = value === 'create' ? '~/my-skills' : ''
  error.value = ''
})

async function submit() {
  const workspacePath = path.value.trim()
  if (!workspacePath) return
  saving.value = true
  error.value = ''
  try {
    const data = mode.value === 'create'
      ? await createWorkspace(workspacePath)
      : await switchWorkspace(workspacePath)
    result.value = {
      workspace_path: data.workspace_path,
      initial_commit: data.initial_commit || null,
      created: mode.value === 'create',
    }
    emit('configured', result.value)
  } catch (err) {
    error.value = err.message || 'Workspace 设置失败'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.onboarding-shell {
  display: grid;
  place-items: center;
  min-height: calc(100vh - 140px);
  animation: onboarding-slide-up 0.3s ease-out;
}

.onboarding-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(360px, 1.1fr);
  gap: var(--qqx-space-3xl);
  align-items: center;
  width: min(940px, 100%);
}

.onboarding-intro,
.onboarding-success {
  color: var(--qqx-text-primary);
}

.onboarding-mark,
.success-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  margin-bottom: var(--qqx-space-lg);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
}

.onboarding-kicker {
  margin-bottom: var(--qqx-space-sm);
  color: var(--qqx-brand);
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-semibold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h2 {
  margin: 0;
  font-size: var(--qqx-font-size-hero);
  line-height: 1.2;
  letter-spacing: -0.9px;
}

.onboarding-intro > p,
.onboarding-success > p {
  margin: var(--qqx-space-lg) 0 0;
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-body);
  line-height: 1.7;
}

.onboarding-steps {
  display: grid;
  gap: var(--qqx-space-md);
  margin-top: var(--qqx-space-2xl);
}

.onboarding-step {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-md);
  color: var(--qqx-text-tertiary);
}

.onboarding-step > span {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-full);
  font-size: var(--qqx-font-size-small);
}

.onboarding-step--active {
  color: var(--qqx-text-primary);
}

.onboarding-step--active > span {
  border-color: var(--qqx-brand);
  background: var(--qqx-brand-light);
  color: var(--qqx-brand);
}

.onboarding-step div {
  display: grid;
  gap: 2px;
}

.onboarding-step strong {
  font-size: var(--qqx-font-size-label);
  font-weight: var(--qqx-font-medium);
}

.onboarding-step small {
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
}

.onboarding-card {
  width: 100%;
}

.onboarding-form {
  display: grid;
  gap: var(--qqx-space-xl);
}

.form-heading {
  display: flex;
  align-items: flex-start;
  gap: var(--qqx-space-md);
  color: var(--qqx-brand);
}

.form-heading h3 {
  margin: 0 0 var(--qqx-space-xs);
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-title);
}

.form-heading p {
  margin: 0;
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-caption);
  line-height: 1.5;
}

.git-note {
  display: flex;
  gap: var(--qqx-space-md);
  padding: var(--qqx-space-lg);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-md);
  background: var(--qqx-bg-surface);
  color: var(--qqx-brand);
}

.git-note div {
  display: grid;
  gap: var(--qqx-space-xs);
}

.git-note strong {
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-label);
}

.git-note span {
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-small);
  line-height: 1.5;
}

.onboarding-error {
  padding: var(--qqx-space-md);
  border: 1px solid color-mix(in srgb, var(--qqx-error) 30%, transparent);
  border-radius: var(--qqx-radius-xs);
  background: var(--qqx-error-light);
  color: var(--qqx-error);
  font-size: var(--qqx-font-size-caption);
}

.onboarding-form :deep(.qqx-btn) {
  width: 100%;
}

.onboarding-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: min(760px, 100%);
  text-align: center;
}

.success-icon {
  border-radius: var(--qqx-radius-full);
  background: var(--qqx-success-light);
  color: var(--qqx-success);
}

.success-summary {
  width: 100%;
  margin: var(--qqx-space-2xl) 0;
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-lg);
  background: var(--qqx-bg-card);
  overflow: hidden;
  text-align: left;
}

.summary-row {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: var(--qqx-space-lg);
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  border-bottom: 1px solid var(--qqx-border-color);
}

.summary-row:last-child {
  border-bottom: 0;
}

.summary-row > span {
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-caption);
}

.summary-row code,
.summary-row strong {
  overflow-wrap: anywhere;
  color: var(--qqx-text-primary);
  font-size: var(--qqx-font-size-caption);
  font-weight: var(--qqx-font-medium);
}

.next-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--qqx-space-lg);
  width: 100%;
  margin-bottom: var(--qqx-space-lg);
}

.next-card {
  position: relative;
  display: grid;
  gap: var(--qqx-space-sm);
  min-height: 150px;
  padding: var(--qqx-space-xl);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-lg);
  background: var(--qqx-bg-card);
  color: var(--qqx-text-primary);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--qqx-transition), background-color var(--qqx-transition), transform 150ms ease-out;
}

.next-card:not(.next-card--primary):hover,
.next-card--primary {
  border-color: var(--qqx-brand);
}

.next-card--primary {
  background: var(--qqx-brand-light);
}

.next-card:active {
  transform: scale(0.97);
  transition-duration: 100ms;
}

.next-card svg {
  position: absolute;
  right: var(--qqx-space-lg);
  bottom: var(--qqx-space-lg);
  color: var(--qqx-brand);
}

.next-index {
  color: var(--qqx-brand);
  font-size: var(--qqx-font-size-small);
  font-weight: var(--qqx-font-medium);
}

.next-card strong {
  font-size: var(--qqx-font-size-title);
}

.next-card small {
  padding-right: var(--qqx-space-xl);
  color: var(--qqx-text-secondary);
  font-size: var(--qqx-font-size-caption);
  line-height: 1.5;
}

@keyframes onboarding-slide-up {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 900px) {
  .onboarding-layout {
    grid-template-columns: 1fr;
    gap: var(--qqx-space-2xl);
  }

  .onboarding-steps {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .onboarding-step {
    align-items: flex-start;
  }
}

@media (max-width: 767px) {
  .onboarding-shell {
    min-height: auto;
    padding: var(--qqx-space-lg) 0;
  }

  h2 {
    font-size: 24px;
    letter-spacing: -0.5px;
  }

  .onboarding-steps,
  .next-actions {
    grid-template-columns: 1fr;
  }

  .summary-row {
    grid-template-columns: 1fr;
    gap: var(--qqx-space-xs);
  }
}
</style>
