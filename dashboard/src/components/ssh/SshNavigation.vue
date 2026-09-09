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
      <label>机器<select class="ssh-input" aria-label="机器" :value="selectedConnection" @change="$emit('connection', $event.target.value)"><option v-for="connection in connections" :key="connection.id" :value="connection.id">{{ connection.name }}</option></select></label>
      <label>目录<select class="ssh-input" aria-label="目录" :value="activeTargetId || ''" @change="chooseTarget($event.target.value)"><option value="" disabled>选择目录</option><option v-for="target in connectionTargets(selectedConnection)" :key="target.id" :value="target.id">{{ target.name }}</option></select></label>
    </div>
  </nav>
</template>
<script setup>
import { ChevronDown, Folder, Plus, Server } from 'lucide-vue-next'
import QButton from '../QButton.vue'
const props = defineProps({ connections: Array, targets: Array, selectedConnection: String, activeTargetId: String })
const emit = defineEmits(['connection', 'target', 'add'])
const connectionTargets = id => props.targets.filter(target => target.connectionId === id)
function chooseTarget(id) { const target = props.targets.find(item => item.id === id); if (target) emit('target', target) }
</script>
