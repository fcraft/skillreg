export function sourceStatusLabel(status) {
  return {
    'up-to-date': '已是最新',
    'update-available': '有可用更新',
    'check-failed': '检查失败',
    updated: '更新完成',
  }[status] || '尚未检查'
}

export function destructiveCount(preview) {
  return Number(preview?.summary?.deleted || 0)
}

export function requiresForce(preview) {
  return Boolean(preview?.localModified)
}

export function canApplyUpdate(preview, forceConfirmed = false) {
  if (!preview?.token || preview.repoDirty) return false
  return !requiresForce(preview) || forceConfirmed
}
