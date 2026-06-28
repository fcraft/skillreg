<template>
  <div class="playground">
    <!-- Page Header -->
    <div class="playground__header">
      <h1 class="playground__title">组件实验室</h1>
      <p class="playground__desc">Component Playground — 浏览所有基础 UI 组件的状态与交互效果</p>
    </div>

    <!-- ============================================================ -->
    <!-- 1. Buttons                                                    -->
    <!-- ============================================================ -->
    <section class="playground__section">
      <h2 class="playground__section-title">按钮 QButton</h2>
      <div class="playground__grid">
        <QCard title="默认变体">
          <div class="demo-row">
            <QButton type="primary">Primary</QButton>
            <QButton type="secondary">Secondary</QButton>
            <QButton type="ghost">Ghost</QButton>
            <QButton type="text">Text</QButton>
            <QButton type="danger">Danger</QButton>
          </div>
        </QCard>

        <QCard title="Tint 变体">
          <div class="demo-row">
            <QButton type="secondary" tint="brand">Brand</QButton>
            <QButton type="secondary" tint="danger">Danger</QButton>
            <QButton type="ghost" tint="brand">Brand</QButton>
            <QButton type="ghost" tint="danger">Danger</QButton>
          </div>
        </QCard>

        <QCard title="尺寸">
          <div class="demo-row">
            <QButton type="primary" size="small">Small</QButton>
            <QButton type="primary" size="medium">Medium</QButton>
            <QButton type="primary" size="large">Large</QButton>
            <QButton type="secondary" size="small">Small</QButton>
            <QButton type="secondary" size="medium">Medium</QButton>
            <QButton type="secondary" size="large">Large</QButton>
          </div>
        </QCard>

        <QCard title="禁用状态">
          <div class="demo-row">
            <QButton type="primary" disabled>Primary</QButton>
            <QButton type="secondary" disabled>Secondary</QButton>
            <QButton type="ghost" disabled>Ghost</QButton>
            <QButton type="text" disabled>Text</QButton>
            <QButton type="danger" disabled>Danger</QButton>
          </div>
        </QCard>

        <QCard title="Pill 按钮">
          <div class="demo-row">
            <QButton type="primary" pill>Primary</QButton>
            <QButton type="secondary" pill>Secondary</QButton>
            <QButton type="ghost" pill>Ghost</QButton>
            <QButton type="text" pill>Text</QButton>
            <QButton type="danger" pill>Danger</QButton>
          </div>
        </QCard>
      </div>
    </section>

    <!-- ============================================================ -->
    <!-- 2. Form Controls                                              -->
    <!-- ============================================================ -->
    <section class="playground__section">
      <h2 class="playground__section-title">表单控件</h2>
      <div class="playground__grid">
        <QCard title="QCheckbox 单个">
          <div class="demo-row demo-row--vertical">
            <div class="demo-cell">
              <span class="demo-cell__label">默认 (md)</span>
              <QCheckbox v-model="checkboxValue" label="选中我" />
              <code class="demo-cell__code">checked: {{ checkboxValue }}</code>
            </div>
            <div class="demo-cell">
              <span class="demo-cell__label">禁用 (md)</span>
              <QCheckbox v-model="checkboxDisabledValue" label="禁用" disabled />
            </div>
          </div>
          <div class="demo-row">
            <div class="demo-cell">
              <span class="demo-cell__label">小尺寸 (sm)</span>
              <QCheckbox v-model="checkboxSmValue" label="小尺寸" size="sm" />
            </div>
            <div class="demo-cell">
              <span class="demo-cell__label">大尺寸 (md)</span>
              <QCheckbox v-model="checkboxValue" label="标准尺寸" size="md" />
            </div>
          </div>
        </QCard>

        <QCard title="QRadio 单个">
          <div class="demo-row demo-row--vertical">
            <div class="demo-cell">
              <span class="demo-cell__label">选中状态</span>
              <QRadio v-model="radioValue" value="a" label="选项 A" />
            </div>
            <div class="demo-cell">
              <span class="demo-cell__label">未选中状态</span>
              <QRadio v-model="radioValue" value="b" label="选项 B" />
            </div>
            <div class="demo-cell">
              <span class="demo-cell__label">禁用</span>
              <QRadio v-model="radioValue" value="c" label="禁用项" disabled />
            </div>
          </div>
          <div class="demo-row">
            <div class="demo-cell">
              <span class="demo-cell__label">尺寸 sm</span>
              <QRadio v-model="radioSize" value="x" label="小" size="sm" />
            </div>
            <div class="demo-cell">
              <span class="demo-cell__label">尺寸 md</span>
              <QRadio v-model="radioSize" value="y" label="标准" size="md" />
            </div>
          </div>
          <code class="demo-cell__code">selected: {{ radioValue }}</code>
        </QCard>

        <QCard title="QCheckboxGroup 多选">
          <div class="demo-row demo-row--vertical">
            <QCheckboxGroup
              v-model="checkboxGroupValue"
              :options="checkboxGroupOptions"
            />
            <code class="demo-cell__code">selected: {{ JSON.stringify(checkboxGroupValue) }}</code>
          </div>
        </QCard>

        <QCard title="QRadioGroup 单选">
          <div class="demo-row demo-row--vertical">
            <QRadioGroup
              v-model="radioGroupValue"
              :options="radioGroupOptions"
            />
            <code class="demo-cell__code">selected: {{ radioGroupValue }}</code>
          </div>
        </QCard>
      </div>
    </section>

    <!-- ============================================================ -->
    <!-- 3. Tabs                                                       -->
    <!-- ============================================================ -->
    <section class="playground__section">
      <h2 class="playground__section-title">标签页 QTabs</h2>
      <QCard title="标签切换">
        <QTabs :tabs="tabs" v-model="activeTab">
          <div v-if="activeTab === 'preview'" class="tab-panel">
            <p class="tab-panel__text">这是预览面板。您可以在这里查看内容的预览效果。</p>
          </div>
          <div v-if="activeTab === 'code'" class="tab-panel">
            <p class="tab-panel__text">这是代码面板。显示组件的源代码。</p>
          </div>
          <div v-if="activeTab === 'settings'" class="tab-panel">
            <p class="tab-panel__text">设置面板。调整组件参数与行为配置。</p>
          </div>
        </QTabs>
      </QCard>
    </section>

    <!-- ============================================================ -->
    <!-- 4. Feedback                                                   -->
    <!-- ============================================================ -->
    <section class="playground__section">
      <h2 class="playground__section-title">反馈组件</h2>
      <div class="playground__grid">
        <QCard title="QToast 消息提示">
          <div class="demo-row">
            <QButton type="secondary" tint="brand" @click="triggerToast('success')">成功提示</QButton>
            <QButton type="secondary" tint="danger" @click="triggerToast('error')">错误提示</QButton>
            <QButton type="secondary" tint="brand" @click="triggerToast('warn')">警告提示</QButton>
            <QButton type="secondary" @click="triggerToast('info')">信息提示</QButton>
          </div>
          <div class="demo-row" style="margin-top: 12px;">
            <span class="demo-hint">点击按钮触发全局 Toast 提示</span>
          </div>
        </QCard>

        <QCard title="QModal 模态框">
          <div class="demo-row">
            <QButton type="primary" @click="modalVisible = true">打开模态框</QButton>
          </div>
          <QModal v-model="modalVisible" title="示例模态框" width="480px">
            <div class="modal-demo-content">
              <p>这是一个模态框示例。模态框支持自定义标题、内容和底部操作栏。</p>
              <p>点击遮罩层或右上角关闭按钮可关闭模态框。</p>
            </div>
            <template #footer>
              <QButton type="ghost" @click="modalVisible = false">取消</QButton>
              <QButton type="primary" @click="modalVisible = false">确认</QButton>
            </template>
          </QModal>
        </QCard>
      </div>
    </section>

    <!-- ============================================================ -->
    <!-- 5. Data Display                                               -->
    <!-- ============================================================ -->
    <section class="playground__section">
      <h2 class="playground__section-title">数据展示</h2>
      <div class="playground__grid">
        <QCard title="QCard 卡片">
          <div class="demo-row demo-row--vertical">
            <QCard title="带标题的卡片" style="width: 100%;">
              <p>这是卡片主体的内容区域，支持自由排版。</p>
              <p style="margin-top: 8px; color: var(--qqx-text-secondary); font-size: var(--qqx-font-size-small);">
                卡片包含 header、body、footer 三个插槽。
              </p>
            </QCard>
            <QCard title="悬停效果" hoverable style="width: 100%;">
              <p>将鼠标悬停在此卡片上，边框将变为品牌色。</p>
            </QCard>
            <QCard empty style="width: 100%;">
              <div class="demo-empty-state">
                <p>空状态卡片 — 使用 <code>empty</code> 属性</p>
              </div>
            </QCard>
          </div>
        </QCard>

        <QCard title="StatusBadge 状态徽标">
          <div class="demo-row demo-row--vertical">
            <div class="demo-cell">
              <span class="demo-cell__label">活跃</span>
              <StatusBadge status="active" />
            </div>
            <div class="demo-cell">
              <span class="demo-cell__label">久未更新</span>
              <StatusBadge status="stale" />
            </div>
            <div class="demo-cell">
              <span class="demo-cell__label">未知</span>
              <StatusBadge status="unknown" />
            </div>
          </div>
        </QCard>
      </div>
    </section>

    <!-- ============================================================ -->
    <!-- 6. Diff Viewer                                                -->
    <!-- ============================================================ -->
    <section class="playground__section">
      <h2 class="playground__section-title">差异查看器 QDiffViewer</h2>
      <QCard title="文件差异对比">
        <QDiffViewer
          repo-content="function greet(name) {\n  console.log(`Hello, ${name}!`)\n  return `Hi ${name}`\n}\n\nexport default greet"
          target-content="function greet(name) {\n  console.log(`Hello, ${name}`)\n  return `Hi ${name}`\n}\n\nexport default greet"
          file-path="src/utils/greet.js"
        />
        <div style="margin-top: 12px;">
          <span class="demo-hint">绿色行表示新增，红色行表示删除。无色行表示未变更。</span>
        </div>
      </QCard>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import QButton from './QButton.vue'
import QCard from './QCard.vue'
import QCheckbox from './QCheckbox.vue'
import QCheckboxGroup from './QCheckboxGroup.vue'
import QRadio from './QRadio.vue'
import QRadioGroup from './QRadioGroup.vue'
import QTabs from './QTabs.vue'
import QModal from './QModal.vue'
import QDiffViewer from './QDiffViewer.vue'
import StatusBadge from './StatusBadge.vue'
import { useToast } from '../composables/useToast.js'

// ── Checkbox state ──
const checkboxValue = ref(true)
const checkboxDisabledValue = ref(false)
const checkboxSmValue = ref(false)

// ── Radio state ──
const radioValue = ref('a')
const radioSize = ref('x')

// ── CheckboxGroup state ──
const checkboxGroupValue = ref(['vue'])
const checkboxGroupOptions = [
  { label: 'Vue.js', value: 'vue' },
  { label: 'React', value: 'react' },
  { label: 'Svelte', value: 'svelte' },
]

// ── RadioGroup state ──
const radioGroupValue = ref('option1')
const radioGroupOptions = [
  { label: '选项 1', value: 'option1' },
  { label: '选项 2', value: 'option2' },
  { label: '选项 3', value: 'option3' },
]

// ── Tabs state ──
const activeTab = ref('preview')
const tabs = [
  { key: 'preview', label: '预览' },
  { key: 'code', label: '代码' },
  { key: 'settings', label: '设置' },
]

// ── Modal state ──
const modalVisible = ref(false)

// ── Toast triggers ──
const toast = useToast()

function triggerToast(tint) {
  const messages = {
    success: '操作成功完成！',
    error: '操作失败，请稍后重试。',
    warn: '操作可能产生预期外的结果。',
    info: '这是一条信息提示。',
  }
  if (tint === 'success') toast.success(messages.success)
  else if (tint === 'error') toast.error(messages.error)
  else if (tint === 'warn') toast.warn(messages.warn)
  else toast.info(messages.info)
}
</script>

<style scoped>
.playground {
  max-width: 960px;
}

.playground__header {
  margin-bottom: var(--qqx-space-2xl);
}

.playground__title {
  font-size: var(--qqx-font-size-hero);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  margin: 0 0 var(--qqx-space-sm);
}

.playground__desc {
  font-size: var(--qqx-font-size-body);
  color: var(--qqx-text-secondary);
  margin: 0;
}

.playground__section {
  margin-bottom: var(--qqx-space-3xl);
}

.playground__section-title {
  font-size: var(--qqx-font-size-display);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  margin: 0 0 var(--qqx-space-lg);
}

.playground__grid {
  display: flex;
  flex-direction: column;
  gap: var(--qqx-space-md);
}

/* ── Demo row helpers ── */
.demo-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--qqx-space-md);
}

.demo-row--vertical {
  flex-direction: column;
  align-items: flex-start;
}

.demo-cell {
  display: flex;
  align-items: center;
  gap: var(--qqx-space-sm);
}

.demo-cell__label {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  min-width: 72px;
  flex-shrink: 0;
}

.demo-cell__code {
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 11px;
  color: var(--qqx-text-tertiary);
  background: var(--qqx-bg-subtle);
  padding: 2px 8px;
  border-radius: var(--qqx-radius-xs);
}

.demo-hint {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-tertiary);
  font-style: italic;
}

.demo-empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--qqx-space-lg);
  color: var(--qqx-text-tertiary);
  font-size: var(--qqx-font-size-small);
}

.demo-empty-state code {
  font-family: 'SF Mono', monospace;
  font-size: 11px;
  margin: 0 4px;
}

/* ── Tab panel ── */
.tab-panel {
  padding: var(--qqx-space-lg);
  background: var(--qqx-bg-subtle);
  border-radius: var(--qqx-radius-sm);
}

.tab-panel__text {
  margin: 0;
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-secondary);
  line-height: 1.6;
}

/* ── Modal demo content ── */
.modal-demo-content p {
  margin: 0 0 var(--qqx-space-md);
  font-size: var(--qqx-font-size-label);
  color: var(--qqx-text-secondary);
  line-height: 1.6;
}

.modal-demo-content p:last-child {
  margin-bottom: 0;
}
</style>
