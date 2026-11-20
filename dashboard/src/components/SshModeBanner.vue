<template>
  <Transition name="ssh-banner">
    <div v-if="isRemoteMode && activeHost" class="ssh-mode-banner">
      <div class="ssh-mode-banner-left">
        <Server :size="16" />
        <span class="ssh-mode-banner-label">管理模式:</span>
        <span class="ssh-mode-banner-host">{{ activeHost.id }}</span>
        <span class="ssh-mode-banner-addr">({{ activeHost.user ? activeHost.user + '@' : '' }}{{ activeHost.hostname }})</span>
        <span class="ssh-mode-banner-path">{{ activeHost.agentHubPath }}</span>
      </div>
      <div class="ssh-mode-banner-right">
        <QButton type="ghost" size="small" @click="exitRemoteMode">
          退出远程管理
        </QButton>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { Server } from 'lucide-vue-next'
import QButton from './QButton.vue'
import { useSshMode } from '../composables/useSshMode.js'

const { isRemoteMode, activeHost, exitRemoteMode } = useSshMode()
</script>

<style scoped>
.ssh-mode-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sr-space-2) var(--sr-space-5);
  background: var(--sr-role-blue-surface);
  border-bottom: none;
}

.ssh-mode-banner-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--sr-text-primary);
  font-size: 13px;
}

.ssh-mode-banner-label {
  font-weight: 500;
}

.ssh-mode-banner-host {
  font-weight: 600;
  color: var(--sr-role-blue-ink);
}

.ssh-mode-banner-addr {
  color: var(--qqx-text-secondary);
  font-size: 12px;
}

.ssh-mode-banner-path {
  color: var(--qqx-text-secondary);
  font-size: 11px;
  font-family: monospace;
}

/* Transition */
.ssh-banner-enter-active,
.ssh-banner-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.ssh-banner-enter-from,
.ssh-banner-leave-to {
  opacity: 0;
  transform: translateY(-100%);
}
</style>
