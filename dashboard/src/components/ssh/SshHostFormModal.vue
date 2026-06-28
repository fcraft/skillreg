<template>
  <QModal
    :model-value="modelValue"
    :title="isEdit ? '编辑远程主机' : '添加远程主机'"
    width="480px"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="host-form">
      <div class="form-row">
        <QInput v-model="form.id" label="ID *" placeholder="dev-server" :disabled="isEdit" />
      </div>
      <div class="form-row">
        <QInput v-model="form.label" label="Label" placeholder="开发服务器" />
      </div>
      <div class="form-row">
        <QInput v-model="form.hostname" label="Hostname *" placeholder="10.0.0.100" />
      </div>
      <div class="form-row form-row--half">
        <QInput v-model="form.port" label="Port" placeholder="22" />
        <QInput v-model="form.user" label="User" placeholder="deploy" />
      </div>
      <div class="form-row">
        <QInput v-model="form.identityFile" label="Identity File" placeholder="~/.ssh/id_rsa" />
      </div>
      <div class="form-row">
        <QInput v-model="form.agentHubPath" label="agent-hub 路径 *" placeholder="~/agent-hub" />
      </div>

      <div v-if="error" class="form-error">{{ error }}</div>
    </div>

    <template #footer>
      <QButton type="secondary" size="medium" @click="close">取消</QButton>
      <QButton type="primary" size="medium" :disabled="!valid || saving" @click="handleSubmit">
        {{ saving ? '保存中...' : (isEdit ? '保存' : '保存并检查') }}
      </QButton>
    </template>
  </QModal>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import QModal from '../QModal.vue'
import QInput from '../QInput.vue'
import QButton from '../QButton.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  host: { type: Object, default: null },  // non-null when editing
})

const emit = defineEmits(['update:modelValue', 'submit'])

const isEdit = computed(() => !!props.host)
const saving = ref(false)
const error = ref(null)

const form = reactive({
  id: '',
  label: '',
  hostname: '',
  port: '',
  user: '',
  identityFile: '',
  agentHubPath: '',
})

// Reset form when modal opens or host changes
watch(() => props.modelValue, (val) => {
  if (val) {
    error.value = null
    saving.value = false
    if (props.host) {
      Object.assign(form, {
        id: props.host.id || '',
        label: props.host.label || '',
        hostname: props.host.hostname || '',
        port: props.host.port ? String(props.host.port) : '',
        user: props.host.user || '',
        identityFile: props.host.identityFile || '',
        agentHubPath: props.host.agentHubPath || '',
      })
    } else {
      Object.assign(form, {
        id: '', label: '', hostname: '', port: '',
        user: '', identityFile: '', agentHubPath: '~/agent-hub',
      })
    }
  }
})

const valid = computed(() => {
  return form.id.trim() && /^[a-zA-Z0-9_-]+$/.test(form.id.trim()) &&
         form.hostname.trim() &&
         form.agentHubPath.trim()
})

function close() {
  emit('update:modelValue', false)
}

async function handleSubmit() {
  if (!valid.value || saving.value) return
  saving.value = true
  error.value = null

  const payload = {
    id: form.id.trim(),
    label: form.label.trim() || null,
    hostname: form.hostname.trim(),
    port: parseInt(form.port) || 22,
    user: form.user.trim() || null,
    identityFile: form.identityFile.trim() || null,
    agentHubPath: form.agentHubPath.trim() || '~/agent-hub',
  }

  emit('submit', payload)
  // Parent closes modal on success; keep open on error to let user retry
}
</script>

<style scoped>
.host-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: flex;
  flex-direction: column;
}

.form-row--half {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-error {
  font-size: 12px;
  color: #e53e3e;
  padding: 8px 12px;
  background: #fef2f2;
  border-radius: 8px;
}
</style>
