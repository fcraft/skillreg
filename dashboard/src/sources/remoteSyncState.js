export const isActiveRun = run => run && ['queued', 'running'].includes(run.state)
export const statusLabel = status => ({ synced: '已同步', modified: '有差异', missing: '未安装', queued: '等待执行', running: '同步中', succeeded: '已完成', 'partially-succeeded': '部分完成', failed: '失败', cancelled: '已取消', online: '连接正常', offline: '连接失败', unknown: '未检查', 'auth-failed': '认证失败', 'host-key-changed': '主机指纹已变化', 'host-key-untrusted': '主机尚未信任', 'unsupported-platform': '远端环境不支持' })[status] || status
export const changeLabel = change => ({ added: '新增', deleted: '删除', modified: '修改', unchanged: '一致' })[change] || change
export const observedSummary = observation => {
  if (!observation) return '尚未检查'
  if (observation.error) return '检查失败 · ' + observation.error.message
  const rows = observation.skills || []
  return ['synced', 'modified', 'missing'].map(status => {
    const count = rows.filter(s => s.status === status).length
    return count ? `${count} ${statusLabel(status)}` : null
  }).filter(Boolean).join(' · ') || '没有选择 Skill'
}
