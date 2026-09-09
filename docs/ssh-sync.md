# SSH 同步

将当前本地 workspace 中的 Skill 推送到远端安装目录，无需在远端安装 skillreg

## 前置条件

- 本机可使用 OpenSSH 和已配置的 Host 别名、密钥或 ssh-agent
- 主机指纹已由用户确认并写入 known_hosts；skillreg 不自动接受或替换指纹
- 远端为 Linux 或 macOS，安装 Python 3.6+，目标文件系统支持原子目录交换
- 目标目录可写，路径和 Skill 内容不包含符号链接；单个 Skill 不超过 32 MiB、10000 个文件

不保存密码、私钥内容或私钥口令，不支持 Windows SSH 目标，也不执行 Skill 内的脚本

## Dashboard

打开「SSH 同步」，添加连接并检查。选择“全局 Agent”或输入项目根目录，发现已有的
Agent 配置目录后确认添加目标，也可手工指定 Skill 安装目录。发现操作不会自动创建或同步目录

添加目标后会自动探测该目录中直接包含 `SKILL.md` 的 Skill；批量添加时依次探测新增目标，
不会扫描其他已保存的目标。左侧按机器和目录导航，选择已保存目录后按需探测，可搜索、
刷新目录；「查看说明」在只读弹窗中单独读取该 Skill 的文档。探测失败保留配置和上次结果，允许刷新重试

右侧「远端 Skills」与「从 workspace 安装」一次只展示一个列表，占用工作区剩余高度。
切换视图保留搜索和安装选择；「更改目标」可选择当前机器的多个目录，取消不会改变原选择。
连接和目录配置位于「设置」，历史和运行中的任务位于「执行记录」

列表区分 workspace 中有同名来源和仅远端存在的 Skill，这不表示内容已同步。
有同名来源时可「对比并同步」，仅预览该目标的单个 Skill；仅远端存在的 Skill 当前支持
查看说明，不自动导入、覆盖或删除。移除目标仅移除本地配置，不删除远端内容

目录探测只读取直接子目录与 `SKILL.md` 文件信息，不递归计算所有 Skill 的内容摘要。
每次最多检查 10000 个目录项，返回 1000 个 Skill 或跳过条目；文档按需读取前 256 KiB。
符号链接和非普通文件会跳过并说明，目录不存在时不创建目录；结果不是实时监控

在「从 workspace 安装」选择 Skill 后，使用底部「检查状态并预览」。展开 Skill 可看到文件新增、修改、删除清单
目标存在差异时必须勾选覆盖确认。同步以 Skill 为单位原子替换，不删除同级其他 Skill

执行记录展示进度、目标结果和错误。关闭弹窗不会取消同步；“停止后续同步”会等待当前
Skill 操作结束，再跳过后续安装。失败重试先重新预览，不会直接沿用旧预览覆盖目标

也可从 Skill 详情的「安装 → SSH」直接安装当前 Skill。进入标签只加载本地保存的
连接和目标配置，展开连接不查询远端；点击某个目标的「检查并安装」才检查该目标，
其他目标不会被一并扫描。每个目标独立显示检查中、错误或上次检查结果，随后复用
差异预览、覆盖确认和执行记录。离开详情不会停止后端已启动的同步，后续可在 SSH
同步页查看执行历史

## CLI 最短闭环

```bash
skillreg connection add --name 开发机 --host dev1
skillreg connection check 开发机
skillreg target discover --connection 开发机
skillreg target add '~/.codex/skills' --connection 开发机 --name 开发机-Codex --json
skillreg target list --json
skillreg target inventory <目标ID>
skillreg target read-skill <目标ID> <Skill名称>
skillreg sync preview --target-id <目标ID> --skill <Skill名称>
skillreg sync execute --preview-id <预览ID>
skillreg sync run <执行ID>
skillreg sync history
```

远端 `~/` 路径要加引号，避免本机 shell 提前展开。项目发现使用
`target discover --connection 开发机 --root /path/to/project`

确认预览中的差异后，可用 `sync execute --preview-id <预览ID> --force` 覆盖
`sync retry <执行ID>` 为原执行中的失败目标和原选定 Skill 生成新预览
`sync status --target-id <目标ID>` 主动刷新；多个目标可重复传入 `sync preview --target-id`

原有 `--target <本机路径>` 入口保持兼容；需要明确覆盖确认和执行记录时使用 `--target-id`

## 状态和持久化

- 连接检查反映网络、认证、主机信任或远端环境，不等于安装成功
- 安装状态仅为 `synced`、`modified`、`missing`，附带上次检查时间；不是实时监控
- 执行状态为 `queued`、`running`、`succeeded`、`partially-succeeded`、`failed`、`cancelled`
- 预览有效期 15 分钟且只能消费一次；源码或目标变化后需重新预览，即使 `--force` 也不跳过目标变化检查
- 连接保存在配置目录的 `connections.json`；目标在 `config.json` 中使用稳定 ID；预览、执行记录和观察结果保存在 `state.db`
- 默认配置目录为 `~/.skillreg`，可通过 `SKILLREG_CONFIG_DIR` 隔离配置和同步记录
- Dashboard 进程承担正在运行的同步；进程退出后不自动续跑，需刷新目标后重试

多目标执行可能部分成功，不提供跨主机事务。没有后台定时漂移检查或自动同步

## 维护者验证

```bash
uv run pytest -q tests/test_remote_sync.py tests/test_sync_inventory.py
SKILLREG_TEST_SSH_HOST=dev1 uv run pytest -q -s tests/test_remote_sync.py -k live_ssh
(cd dashboard && npm run build && SKILLREG_TEST_SSH_HOST=dev1 npx playwright test tests/e2e/ssh-live.spec.js --workers=1)
```

真实 SSH 用例仅在显式设置测试 Host 时运行：创建专用远端临时目录，覆盖发现、首次安装、
目录探测、按需读取说明、幂等、漂移拦截、覆盖确认和重试，并在结束时清理。
不会写入现有 Agent 安装目录

浏览器真实 SSH 用例使用隔离的测试 workspace，覆盖添加目录后的自动探测、安装预览、
执行、刷新目录与只读文档弹窗；结束后删除专用临时目录和测试连接配置
