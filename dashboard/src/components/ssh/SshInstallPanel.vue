<template>
  <section class="ssh-install-panel" aria-label="从 workspace 安装">
    <div class="ssh-list-toolbar">
      <input v-model="search" class="ssh-input" type="search" aria-label="搜索 Skill" placeholder="搜索名称或描述" />
      <span class="ssh-muted">{{ filteredSkills.length }} 个</span>
      <QButton type="text" size="small" @click="selectVisible">选择筛选结果</QButton>
      <QButton type="text" size="small" :disabled="!selectedSkills.length" @click="$emit('update:selectedSkills', [])">清空</QButton>
    </div>
    <div class="ssh-install-destination">
      <span :title="destination">安装到：{{ destination || '尚未选择目标' }}</span>
      <QButton type="text" size="small" @click="$emit('targets')">更改目标</QButton>
    </div>
    <div class="ssh-skill-list" tabindex="0" aria-label="可安装的 Skills">
      <QCheckbox v-for="skill in filteredSkills" :key="skill.name" :model-value="selectedSkills.includes(skill.name)" @update:model-value="toggle(skill.name, $event)">
        <span class="ssh-skill-name" :title="skill.name">{{ skill.name }}</span><small :title="skill.description">{{ skill.description || '暂无说明' }}</small>
      </QCheckbox>
      <p v-if="!filteredSkills.length" class="ssh-muted">没有匹配的 Skill</p>
    </div>
    <footer class="ssh-submit"><span>已选 {{ selectedSkills.length }} 个 Skill · {{ selectedTargets.length }} 个目标</span><QButton type="primary" :disabled="busy || !selectedTargets.length || !selectedSkills.length" @click="$emit('preview')">{{ busy ? '检查中…' : '检查状态并预览' }}</QButton></footer>
  </section>
</template>
<script setup>
import { computed, ref } from 'vue'
import QButton from '../QButton.vue'
import QCheckbox from '../QCheckbox.vue'
const props = defineProps({ skills: Array, selectedSkills: Array, selectedTargets: Array, targets: Array, busy: Boolean })
const emit = defineEmits(['update:selectedSkills', 'targets', 'preview'])
const search = ref('')
const filteredSkills = computed(() => props.skills.filter(skill => `${skill.name} ${skill.description || ''}`.toLowerCase().includes(search.value.toLowerCase())))
const destination = computed(() => props.targets.filter(target => props.selectedTargets.includes(target.id)).map(target => `${target.name} (${target.path})`).join('、'))
function toggle(name, selected) { emit('update:selectedSkills', selected ? [...props.selectedSkills, name] : props.selectedSkills.filter(item => item !== name)) }
function selectVisible() { emit('update:selectedSkills', [...new Set([...props.selectedSkills, ...filteredSkills.value.map(skill => skill.name)])]) }
</script>
