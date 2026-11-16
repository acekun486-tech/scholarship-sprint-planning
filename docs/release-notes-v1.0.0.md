# v1.0.0 发布说明（Release Notes）

| 项目 | 内容 |
|---|---|
| 版本 | `v1.0.0` |
| 发布类型 | 首个可发布基线（Sprint 1） |
| 发布日期 | 2026-11-16 |
| 标签 | annotated tag `v1.0.0` |
| 对应分支 | `main` |
| 仓库 | <https://github.com/acekun486-tech/scholarship-sprint-planning> |
| 质量结论 | 自动化门禁通过；独立评审人确认待完成（见“已知问题”） |

## 版本摘要

Sprint 1 完成高校学工平台奖助学金管理子系统的最小可用闭环：学生可以查看通知和项目、提交申请与证明材料、查看审批进度；辅导员可以查看申请与材料、填写审批意见并完成合法状态流转。

## 新增功能

| 编号 | 功能 | 入口 | 验收要点 |
|---|---|---|---|
| US01 | 查看奖助学金通知 | `/notices` | 通知标题、内容、发布时间可展示 |
| US02 | 查询项目、查看详情 | `/projects`、`/projects/<id>` | 支持关键词搜索；展示资格条件、截止日期；`LIKE` 通配符已转义 |
| US03 | 填写并提交申请 | `/apply/<project_id>` | 服务端必填与长度校验、截止日期检查、重复提交防护 |
| US04 | 上传证明材料 | `/applications/<id>/upload` | 仅允许 PDF/PNG/JPG/JPEG；校验扩展名、文件签名、5 MB 上限；失败清理落盘文件 |
| US05 | 辅导员查看和审批 | `/counselor/applications` | 查看申请与材料；审批意见必填；阻止重复审批与非法状态流转 |
| US08 | 学生查看进度和结果 | `/dashboard` | 仅本人可见；展示状态、审批意见和材料 |

### 状态流转

```text
待审批 -> 通过
       -> 不通过
       -> 退回补充材料 -> 学生补传材料 -> 待审批
```

## 质量数据

| 指标 | 结果 | 门槛 | 结论 |
|---|---|---|---|
| 自动化测试 | 40 passed | 全绿 | 通过 |
| 语句/分支/函数/行覆盖率 | 100% / 100% / 100% / 100% | 核心 ≥80% | 通过 |
| 增量覆盖率（相对上一提交） | 49 行，100% | ≥60% | 通过 |
| Ruff | 0 项 | 0 项 | 通过 |
| Bandit | 0 Blocker / 0 Critical | 0 | 通过 |
| 重复代码（jscpd） | 0% | ≤3% | 通过 |
| 最大圈复杂度（Radon） | 9 | ≤10 | 通过 |
| 缺陷按时响应/关闭 | 100% / 100% | ≥90% | 通过 |

详细证据：

- [覆盖率记录](quality/coverage-record.md)
- [静态扫描记录](quality/static-scan.md)
- [代码评审记录](quality/code-review-record.md)
- [缺陷台账](quality/defect-ledger.md)
- [质量报告](quality/quality-report.md)

## 配置与兼容性

- Python 3.10+；本次验证环境为 Python 3.14.6（Windows）。
- 依赖清单：`requirements.txt`（运行）、`requirements-dev.txt`（质量工具）。
- 环境变量：`SECRET_KEY`、`DATABASE_PATH`、`UPLOAD_FOLDER`、`FLASK_HOST`、`PORT`。
- 数据库：首次启动自动建表并写入演示数据；旧版明文演示密码会升级为 Werkzeug 哈希。
- 不兼容变更：无（首个发布基线）。

## 升级与部署说明

1. 拉取 `v1.0.0`：`git checkout v1.0.0`。
2. 安装依赖：`pip install -r requirements.txt`。
3. 设置 `SECRET_KEY`，按需设置 `DATABASE_PATH` 和 `UPLOAD_FOLDER`。
4. 启动：`python app.py`（本地）或 `gunicorn app:app --bind 0.0.0.0:$PORT`（Render）。
5. 验证：访问 `/healthz` 返回 `{"status": "ok"}`，使用演示账号登录。

详细步骤见 [部署说明](deployment.md)。

## 已知问题与限制

| 编号 | 问题 | 影响 | 计划 |
|---|---|---|---|
| KI-01 | 演示账号使用固定口令 `student123` / `counselor123` | 公网部署存在账号风险 | 课程环境专用；真实部署前替换账号体系 |
| KI-02 | 登录无失败次数限制与验证码 | 可被暴力尝试 | 转入后续版本 |
| KI-03 | 上传仅校验扩展名与文件签名，无病毒扫描 | 恶意文件可能落盘 | 生产环境接入对象存储与病毒扫描 |
| KI-04 | SQLite 与本地文件存储 | 不适合高并发、多实例 | 生产迁移 PostgreSQL 与对象存储 |
| KI-05 | `_register_routes` 单函数语句较多（PLR0915） | 可维护性一般，圈复杂度为 1 | 已评审豁免；后续按蓝图拆分 |
| KI-06 | 独立评审人 approve 尚未确认 | 质量报告结论为“有条件合并” | 由团队第二成员完成评审后关闭 |

## 验证记录

- `pytest -q`：40 passed。
- `ruff check .`：All checks passed。
- `bandit -r app.py database.py -ll`：No issues identified。
- `jscpd`：0 clones / 0% duplication。
- 验收清单：[acceptance-checklist.md](acceptance-checklist.md)（团队第二成员评审项待勾选）。
- 提交历史、分支与标签：见 GitHub 仓库 `main`、`feature/*` 与 `v1.0.0`。

## 致谢

感谢 PO、SM、两位开发成员在 Sprint 1 的协作，以及质量检查阶段对静态扫描、覆盖率与缺陷修复的投入。
