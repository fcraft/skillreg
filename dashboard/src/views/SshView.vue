<template>
  <div class="ssh-view">
    <!-- Toolbar -->
    <div class="ssh-toolbar">
      <div class="ssh-toolbar-left">
        <h2 class="ssh-title">SSH 远程主机</h2>
        <span v-if="!loading" class="ssh-count">{{ hosts.length }} 台</span>
      </div>
      <div class="ssh-toolbar-actions">
        <QButton type="ghost" size="small" @click="refreshAll">
          <RefreshCw :size="14" :class="{ 'icon-spin': loading }" /> 刷新
        </QButton>
        <QButton type="primary" size="small" @click="openAddForm">
          <Plus :size="14" /> 添加主机
        </QButton>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="ssh-error">{{ error }}</div>

    <!-- Empty state -->
    <div v-if="!loading && !hosts.length" class="ssh-empty">
      <QCard empty>
        <div class="ssh-empty-content">
          <Server :size="32" class="ssh-empty-icon" />
          <p>暂无远程主机</p>
          <p class="ssh-empty-hint">添加远程主机后，可管理远程 Skill 同步状态</p>
          <QButton type="primary" size="medium" @click="openAddForm">
            <Plus :size="14" /> 添加主机
          </QButton>
        </div>
      </QCard>
    </div>

    <!-- Host grid -->
    <div v-if="hosts.length" class="ssh-host-grid">
      <SshHostCard
        v-for="host in hosts"
        :key="host.id"
        :host="host"
        :check-result="checks[host.id]"
        :status-text="statusSummary(host.id)"
        @select="enterHost(host.id)"
        @edit="openEditForm(host)"
        @delete="confirmDelete(host)"
        @check="checkHost(host.id)"
      />
    </div>

    <!-- Add/Edit Modal -->
    <SshHostFormModal
      v-model="formOpen"
      :host="editingHost"
      @submit="handleFormSubmit"
    />

    <!-- Delete Confirm Modal -->
    <QModal
      v-model="deleteConfirmOpen"
      title="删除主机"
      width="400px"
    >
      <p class="delete-confirm-text">
        确定要删除主机 <strong>{{ deletingHost?.id }}</strong> 吗？此操作不可撤销。
      </p>
      <template #footer>
        <QButton type="secondary" size="medium" @click="deleteConfirmOpen = false">取消</QButton>
        <QButton type="danger" size="medium" :disabled="deleting" @click="handleDelete">
          {{ deleting ? '删除中...' : '删除' }}
        </QButton>
      </template>
    </QModal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Server, Plus, RefreshCw } from 'lucide-vue-next'
import QCard from '../components/QCard.vue'
import QButton from '../components/QButton.vue'
import QModal from '../components/QModal.vue'
import SshHostCard from '../components/ssh/SshHostCard.vue'
import SshHostFormModal from '../components/ssh/SshHostFormModal.vue'
import { useSshHosts } from '../composables/useSshHosts.js'
import { useSshMode } from '../composables/useSshMode.js'

const router = useRouter()
const { enterRemoteMode } = useSshMode()
const {
  hosts, loading, error,
  selectedHostId, checks,
  loadHosts, addHost, updateHost, removeHost,
  checkHost,
} = useSshHosts()

// ── Enter remote management mode ─────────────────

function enterHost(hostId) {
  enterRemoteMode(hostId)
  router.push('/skills')
}

// ── Status summary for cards ─────────────────────

function statusSummary(hostId) {
  const check = checks[hostId]
  if (!check) return ''
  if (!check.ok) return ''
  return '在线'
}

// ── Host form ────────────────────────────────────

const formOpen = ref(false)
const editingHost = ref(null)

function openAddForm() {
  editingHost.value = null
  formOpen.value = true
}

function openEditForm(host) {
  editingHost.value = host
  formOpen.value = true
}

async function handleFormSubmit(payload) {
  try {
    if (editingHost.value) {
      await updateHost(editingHost.value.id, payload)
    } else {
      await addHost(payload)
    }
    formOpen.value = false
    await checkHost(payload.id)
  } catch (err) {
    throw err
  }
}

// ── Delete ───────────────────────────────────────

const deleteConfirmOpen = ref(false)
const deletingHost = ref(null)
const deleting = ref(false)

function confirmDelete(host) {
  deletingHost.value = host
  deleteConfirmOpen.value = true
}

async function handleDelete() {
  if (!deletingHost.value || deleting.value) return
  deleting.value = true
  try {
    await removeHost(deletingHost.value.id)
    deleteConfirmOpen.value = false
    deletingHost.value = null
  } finally {
    deleting.value = false
  }
}

// ── Refresh all ──────────────────────────────────

async function refreshAll() {
  await loadHosts()
  await Promise.allSettled(hosts.value.map(h => checkHost(h.id)))
}

onMounted(() => {
  loadHosts().then(() => {
    hosts.value.forEach(h => checkHost(h.id))
  })
})
</script>

<style scoped>
.ssh-view {
  max-width: 1200px;
  margin: 0 auto;
}

.ssh-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.ssh-toolbar-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.ssh-title {
  font-size: var(--qqx-font-size-title);
  font-weight: var(--qqx-font-semibold);
  color: var(--qqx-text-primary);
  margin: 0;
}

.ssh-count {
  font-size: var(--qqx-font-size-small);
  color: var(--qqx-text-secondary);
}

.ssh-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ssh-error {
  color: var(--qqx-error, #e53e3e);
  font-size: var(--qqx-font-size-label);
  padding: var(--qqx-space-md) var(--qqx-space-lg);
  background: var(--qqx-error-light, #fef2f2);
  border: 1px solid var(--qqx-border-color);
  border-radius: var(--qqx-radius-xs);
  margin-bottom: var(--qqx-space-lg);
}

.ssh-empty { margin-top: 40px; }

.ssh-empty-content {
  text-align: center;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.ssh-empty-icon { color: var(--qqx-text-tertiary); }
.ssh-empty-content p { font-size: var(--qqx-font-size-body); color: var(--qqx-text-primary); margin: 0; font-weight: var(--qqx-font-medium); }
.ssh-empty-hint { font-size: var(--qqx-font-size-small); color: var(--qqx-text-secondary); font-weight: var(--qqx-font-regular); max-width: 360px; }

.ssh-host-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

@media (max-width: 1023px) { .ssh-host-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 767px) { .ssh-host-grid { grid-template-columns: 1fr; } }

.delete-confirm-text { font-size: 14px; color: var(--qqx-text-primary); line-height: 1.6; }

.icon-spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
