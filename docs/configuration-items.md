# 配置项清单（实验三 步骤 8）

> 基线：`v1.0.0`（annotated tag，对应 `main` 发布提交）。
> 配置管理员：SM 兼。配置项按角色标识负责人，姓名与学号见《实验三 实验报告》成员表。
> 版本号遵循语义化版本 `MAJOR.MINOR.PATCH`；本表版本号指随 v1.0.0 发布的基线版本。

## 配置项识别原则

满足以下任一条件的文件或目录纳入配置管理：影响构建与运行、影响业务行为、影响验收与质量判定、需要对外发布或追溯。数据库运行文件、上传材料和本地密钥不进入 Git，按“环境数据”管理。

## 配置项清单

| 编号 | 配置项 | 类别 | 版本 | 负责人 | 存储位置 | 变更控制 |
|---|---|---|---|---|---|---|
| CI-01 | `app.py` | 源代码 | 1.0.0 | 开发 A | Git `main`，tag `v1.0.0` | 是 |
| CI-02 | `database.py` | 源代码（数据库脚本） | 1.0.0 | 开发 B | Git `main`，tag `v1.0.0` | 是 |
| CI-03 | `templates/`（11 个页面模板） | 源代码（视图） | 1.0.0 | 开发 B | Git `main`，tag `v1.0.0` | 是 |
| CI-04 | `tests/test_app.py` | 测试代码 | 1.0.0 | 开发 A、开发 B | Git `main`，tag `v1.0.0` | 是 |
| CI-05 | `requirements.txt` | 构建脚本（运行依赖） | 1.0.0 | SM | Git `main`，tag `v1.0.0` | 是 |
| CI-06 | `requirements-dev.txt` | 构建脚本（质量工具） | 1.0.0 | SM | Git `main`，tag `v1.0.0` | 是 |
| CI-07 | `pyproject.toml` | 构建配置（pytest / Ruff） | 1.0.0 | SM | Git `main`，tag `v1.0.0` | 是 |
| CI-08 | `.github/workflows/quality.yml` | 构建配置（CI 质量门禁） | 1.0.0 | SM | Git `main`，tag `v1.0.0` | 是 |
| CI-09 | `render.yaml`、`Procfile` | 部署配置 | 1.0.0 | SM | Git `main`，tag `v1.0.0` | 是 |
| CI-10 | `.devcontainer/devcontainer.json` | 开发环境配置 | 1.0.0 | SM | Git `main`，tag `v1.0.0` | 是 |
| CI-11 | `scripts/quality.ps1` | 构建/质量脚本 | 1.0.0 | SM | Git `main`，tag `v1.0.0` | 是 |
| CI-12 | `tools/coverage_metrics.py` | 质量度量脚本 | 1.0.0 | SM | Git `main`，tag `v1.0.0` | 是 |
| CI-13 | `README.md` | 文档（用户手册/运行说明） | 1.0.0 | PO | Git `main`，tag `v1.0.0` | 是 |
| CI-14 | `docs/sprint-backlog.md`、`docs/acceptance-checklist.md`、`docs/test-report.md` | 文档（计划与验收） | 1.0.0 | PO、SM | Git `main`，tag `v1.0.0` | 是 |
| CI-15 | `docs/quality/`（5 份质量记录） | 文档（质量证据） | 1.0.0 | SM | Git `main`，tag `v1.0.0` | 是 |
| CI-16 | `docs/standup-records.md`、`docs/configuration-items.md`、`docs/change-control.md`、`docs/release-notes-v1.0.0.md`、`docs/git-conflict-exercise.md`、`docs/team-roles.md` | 文档（过程记录） | 1.0.0 | SM | Git `main`，tag `v1.0.0` | 是 |
| CI-17 | `docs/screenshots/homepage.png` | 文档附件（界面截图） | 1.0.0 | PO | Git `main`，tag `v1.0.0` | 是 |
| CI-18 | `reports/lab4/` 扫描与覆盖率证据 | 质量证据（构建产物） | 1.0.0 | SM | Git `main`，tag `v1.0.0` | 是 |
| CI-19 | `v1.0.0` 标签与 Release Notes | 发布基线 | 1.0.0 | SM | Git tag + GitHub Release | 是 |

## 不纳入版本控制的配置项

| 项目 | 原因 | 管理方式 |
|---|---|---|
| `scholarship.db` | 运行时数据库，含本地演示数据，随环境变化 | 由 `database.py` 初始化；不提交，不作为发布物 |
| `uploads/` 下的用户材料 | 含申请人个人信息与文件内容 | 本地/服务器存储，随机文件名，按权限下载 |
| `.env`、`SECRET_KEY` | 密钥类敏感配置 | 环境变量注入；仓库只保留示例说明 |
| `.venv/`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/` | 可再生的本地环境与缓存 | 由 `.gitignore` 排除 |
| `reports/lab4/baseline-src` 临时快照 | 基线度量时的临时文件 | 度量完成后删除，不提交 |

## 版本号规则与本项目映射

| 版本位 | 递增条件 | 本项目示例 |
|---|---|---|
| MAJOR | 不兼容的接口或数据结构变更 | 无（v1.0.0 为首个发布基线） |
| MINOR | 向下兼容的功能新增 | 新增 US06 学院汇总、US07 名额管理时递增为 1.1.0 |
| PATCH | 向下兼容的缺陷修复 | 修复审批提示或上传边界问题时递增为 1.0.1 |

## 分支与标签规则

| 类型 | 命名 | 用途 | 合并要求 |
|---|---|---|---|
| 主干 | `main` | 始终保持可发布 | 受保护，禁止直接提交 |
| 功能 | `feature/<主题>` | 新功能或重构 | PR + 至少 1 人评审 + 质量门禁通过 |
| 缺陷 | `bugfix/<主题>` | 缺陷修复 | 同上 |
| 紧急修复 | `hotfix/<版本>` | 发布后紧急修复 | 同上，合并后打 PATCH 标签 |
| 发布标签 | `v<MAJOR>.<MINOR>.<PATCH>` | 标识可发布基线 | annotated tag，附发布说明 |

## 配置审计检查点

- [x] 源码、测试、构建配置、部署配置、过程文档均已纳入 Git。
- [x] 敏感信息（密钥、数据库、上传材料）未提交；`.gitignore` 覆盖本地环境与缓存。
- [x] `v1.0.0` 标签指向发布提交，Release Notes 与标签一致。
- [x] 依赖版本在 `requirements*.txt` 中锁定范围，CI 与本地使用同一份清单。
- [x] 变更均通过分支和 PR 进入 `main`，变更记录见 `docs/change-control.md`。
