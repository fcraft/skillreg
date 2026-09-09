<template>
  <nav class="ssh-navigation" aria-label="机器与目录">
    <div class="ssh-nav-desktop">
      <div class="ssh-nav-heading"><span>机器与目录</span><QButton type="ghost" size="small" aria-label="添加连接" @click="$emit('add')"><Plus :size="16" /></QButton></div>
      <div class="ssh-nav-list">
        <section v-for="connection in connections" :key="connection.id">
          <button class="ssh-connection q-press" :class="{ selected: selectedConnection === connection.id }" :aria-expanded="selectedConnection === connection.id" @click="$emit('connection', connection.id)">
            <Server :size="16" /><span><strong>{{ connection.name }}</strong><small>{{ connection.host }}</small></span><ChevronDown :size="14" :class="{ 'ssh-nav-collapsed': selectedConnection !== connection.id }" />
          </button>
          <div v-if="selectedConnection === connection.id" class="ssh-nav-targets">
            <button v-for="target in connectionTargets(connection.id)" :key="target.id" class="ssh-directory q-press" :class="{ selected: activeTargetId === target.id }" :aria-current="activeTargetId === target.id ? 'location' : undefined" :title="target.path" @click="$emit('target', target)"><Folder :size="14" /><span>{{ target.name }}</span></button>
            <p v-if="!connectionTargets(connection.id).length" class="ssh-muted">尚未添加目录</p>
          </div>
        </section>
      </div>
    </div>
    <div class="ssh-nav-mobile">
      <QSelect label="机器" :model-value="selectedConnection" :options="connections.map(item => ({ value: item.id, label: item.name }))" @change="$emit('connection', $event)" />
      <QSelect label="目录" placeholder="选择目录" :model-value="activeTargetId || ''" :options="connectionTargets(selectedConnection).map(item => ({ value: item.id, label: item.name }))" @change="chooseTarget" />
    </div>
  </nav>
</template>
<script setup>
import { ChevronDown, Folder, Plus, Server } from 'lucide-vue-next'
import QButton from '../QButton.vue'
import QSelect from '../QSelect.vue'
const props = defineProps({ connections: Array, targets: Array, selectedConnection: String, activeTargetId: String })
const emit = defineEmits(['connection', 'target', 'add'])
const connectionTargets = id => props.targets.filter(target => target.connectionId === id)
function chooseTarget(id) { const target = props.targets.find(item => item.id === id); if (target) emit('target', target) }
</script>
