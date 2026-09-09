<template>
  <QModal :model-value="modelValue" :title="connection ? '编辑连接' : '添加 SSH 连接'" @update:model-value="$emit('update:modelValue', $event)">
    <form class="ssh-form" @submit.prevent="save">
      <label>连接名称<input v-model="form.name" class="ssh-input" required placeholder="开发机" /></label>
      <label>SSH Host<input v-model="form.host" class="ssh-input" required placeholder="dev1 或主机地址" /></label>
      <p class="ssh-muted">使用本机 SSH 配置和密钥，无需在远端安装 skillreg</p>
      <QDisclosure id="ssh-advanced-connection" title="高级连接设置"><div class="ssh-form ssh-advanced">
        <label>用户<input v-model="form.user" class="ssh-input" placeholder="使用 SSH 配置" /></label>
        <label>端口<input v-model="form.port" class="ssh-input" type="number" min="1" max="65535" placeholder="使用 SSH 配置" /></label>
        <label>私钥路径<input v-model="form.identityFile" class="ssh-input" placeholder="~/.ssh/id_ed25519" /></label>
      </div></QDisclosure>
      <p v-if="error" class="ssh-error" role="alert">{{ error }}</p>
    </form>
    <template #footer>
      <QButton type="secondary" @click="$emit('update:modelValue', false)">取消</QButton>
      <QButton type="primary" :disabled="saving || !form.name || !form.host" @click="save">{{ saving ? '保存中…' : '保存并检查' }}</QButton>
    </template>
  </QModal>
</template>
<script setup>
import { reactive, ref, watch } from 'vue'
import QModal from '../QModal.vue'
import QButton from '../QButton.vue'
import QDisclosure from '../QDisclosure.vue'
import { saveConnection, checkConnection } from '../../api/remoteSync.js'
const props = defineProps({ modelValue: Boolean, connection: Object })
const emit = defineEmits(['update:modelValue', 'saved'])
const form = reactive({ name: '', host: '', user: '', port: '', identityFile: '' })
const error = ref(''), saving = ref(false)
watch(() => props.modelValue, open => {
  if (!open) return
  Object.assign(form, { name: '', host: '', user: '', port: '', identityFile: '' }, props.connection || {})
  error.value = ''
})
async function save() {
  if (saving.value || !form.name || !form.host) return
  saving.value = true; error.value = ''
  try {
    const result = await saveConnection({ name: form.name, host: form.host, user: form.user || null, port: form.port ? Number(form.port) : null, identityFile: form.identityFile || null }, props.connection?.id)
    emit('saved', await checkConnection(result.id))
    emit('update:modelValue', false)
  } catch (err) { error.value = err.message }
  finally { saving.value = false }
}
</script>
