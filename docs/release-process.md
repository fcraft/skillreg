# 发版流程

`pyproject.toml` 是人工维护的版本号源头。每次发版都必须确保运行时版本和
Git tag 与它同步。

## 准备发版 PR

1. 确认下一个版本号，例如 `0.2.0`。
2. 同步修改：
   - `pyproject.toml` -> `[project].version`
   - `src/skillreg/__init__.py` -> `__version__`
3. 本地执行检查：

   ```bash
   python scripts/check_version.py
   python -m pytest -q
   ```

4. 等 CI 通过后合入发版 PR。

## 在 GitHub 发布

创建并推送一个与 `pyproject.toml` 完全匹配的 tag，格式是
`v<pyproject version>`：

```bash
git tag v0.2.0
git push origin v0.2.0
```

`Release` GitHub Action 会自动执行：

- 校验 `pyproject.toml`、`skillreg.__version__` 和 tag 一致
- 运行测试
- 构建 wheel 和 sdist
- 校验 wheel metadata 中的版本号
- 上传构建产物
- 创建 GitHub Release，并自动生成 release notes
- 发布到 PyPI

如果 tag 不匹配，例如 tag 是 `v0.2.1`，但 `pyproject.toml` 写的是
`0.2.0`，release job 会在发布产物前失败。

## PyPI 发布

`uv tool install skillreg` 默认会从 PyPI 安装 `skillreg` 包。当前 PyPI
项目已注册，发布通过 trusted publishing 完成。

PyPI trusted publisher 配置：

- PyPI project name: `skillreg`
- Owner: `fcraft`
- Repository: `skillreg`
- Workflow name: `release.yml`
- Environment name: 留空

发布成功后，用户可以直接安装：

```bash
uv tool install skillreg
```
