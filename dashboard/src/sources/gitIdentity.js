export function gitIdentityRequestFromError(error) {
  if (error?.code !== 'git_identity_required') return null
  return {
    repository: error.details?.repository || '.',
  }
}

export function validateGitIdentity(name, email) {
  if (!name.trim()) return '请输入 Git 用户名'
  if (!email.trim() || !email.includes('@')) return '请输入有效的 Git 邮箱'
  return ''
}
