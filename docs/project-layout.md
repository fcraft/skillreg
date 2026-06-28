# 项目结构说明

当前 `skillreg` 仓库里有几类目录：

## 核心目录

- `src/skillreg/`
  - Python 包本体，包含 CLI、FastAPI server、services
- `dashboard/`
  - 前端源码与构建产物
- `tests/`
  - 后端接口与迁移闭环测试

## 归档目录

- `docs/archive/`
  - 迁移过程中的矩阵、拆解 issue、实施记录
  - 保留作为历史留档，不再作为当前开发入口

当前版本的真实实现都已经在主仓中：

- CLI：`src/skillreg/cli.py`
- skillreg-skill：`src/skillreg/builtin/skillreg-skill/`
- UI 组件：`dashboard/src/components/`

## 设计留档

- `docs/archive/issues/`
  - 迁移实施拆解
- `docs/archive/dashboard-migration-matrix.md`
  - dashboard 迁移矩阵
