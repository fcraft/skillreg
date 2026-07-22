# npm 发布初始化

日常发布由 `v<version>` tag 触发，不需要保存长期 npm token。首次占用
`skillreg` 包名时，需要维护者本人完成一次交互式发布，然后为 GitHub Actions
启用 Trusted Publishing。

## 首次发布

确认当前版本已经存在于 PyPI，并检查 npm 包名仍未被占用：

```bash
version="$(uv run python scripts/versioning.py current)"
python -m pip index versions skillreg
npm view "skillreg@$version" --registry=https://registry.npmjs.org/
```

首次查询 npm 预期返回 `E404`。发布前先在 npmjs.com 的 Account →
Two-Factor Authentication 中启用 2FA，并妥善保存恢复码。推荐选择
Authorization and writes；也可以在 CLI 中执行：

```bash
npm profile enable-2fa auth-and-writes --registry=https://registry.npmjs.org/
```

启用后，在仓库中执行：

```bash
cd npm
npm ci
npm test
npm pack --dry-run
npm login --registry=https://registry.npmjs.org/
npm whoami --registry=https://registry.npmjs.org/
npm publish --access public
```

登录、密码和一次性验证码只在 npm CLI 或 npmjs.com 中输入，不要写入仓库，
也不需要提供给其他维护者或 agent。

如果安全密钥页面显示 `Something went wrong`，终止当前 `npm publish` 后重新
执行，并改用 Edge InPrivate 等无扩展、无旧会话的隐私窗口打开新的认证链接。
不要重复使用已经失败的 `/auth/cli/` 链接。

## Trusted Publishing

首次发布成功后，打开 npmjs.com 上 `skillreg` 包的 Settings → Trusted
Publisher，选择 GitHub Actions，并填写：

- Organization or user：`fcraft`
- Repository：`skillreg`
- Workflow filename：`release.yml`
- Environment：留空
- Allowed actions：`npm publish`

保存后，在 Publishing access 中启用“Require two-factor authentication and
disallow tokens”。GitHub Actions 会使用 OIDC 短期凭证发布，并自动生成
provenance，不需要配置 `NPM_TOKEN`。

后续发布只运行：

```bash
scripts/release.sh
```

如果 `skillreg` 包名在首次发布前被占用，应停止发布并改用受控 scope，不要向
未知包所有者索要权限。
