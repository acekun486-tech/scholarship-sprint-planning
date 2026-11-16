# 代码评审记录（实验四 步骤 3）

## 评审信息

| 项目 | 内容 |
|---|---|
| 仓库 | <https://github.com/acekun486-tech/scholarship-sprint-planning> |
| 变更分支 | `feature/quality-gate`（质量修复与门禁） |
| 目标分支 | `main` |
| 作者 | acekun486-tech |
| 评审人 | 〔待填：团队第二成员姓名 / 学号〕 |
| 评审日期 | 2026-11-16 |
| 评审范围 | 质量修复、测试补充、CI 门禁、实验文档 |
| 合并结论 | 〔待评审人确认：approve / request changes〕 |

对照检查单逐项评审：命名、可读性、边界与异常、重复代码、测试、安全（密钥 / 注入 / 越权）。以下意见均指明文件与行，作者逐条回复。

## 评审意见与闭环

| 编号 | 文件 : 行（修复前） | 问题类型 | 评审意见 | 作者处理 | 状态 |
|---|---|---|---|---|---|
| CR-01 | `app.py:127-134` | 安全 / 注入 | `materials_by_application` 用 f-string 拼接 `IN` 占位符。虽然当前参数仍走绑定，但这种写法容易在后续改动中演变成真实注入，建议改为单参数 JSON 查询，彻底消除字符串拼接。 | 已改为 `application_id IN (SELECT value FROM json_each(?))`，ID 列表 `json.dumps` 后作为一个参数绑定；Bandit 复扫 0 问题。 | 已闭环 |
| CR-02 | `app.py:303-342` | 可读性 / 复杂度 | `upload_material` 同时负责状态检查、文件校验、落盘、数据库写入和事务回滚，8 个 return、圈复杂度 12，超过单函数 ≤10 的门槛。建议抽出上传校验函数。 | 已抽取 `validate_upload()`，用 `ValidatedUpload` 命名元组返回校验结果；路由圈复杂度从 12 降到 7。 | 已闭环 |
| CR-03 | `app.py:243-256` | 边界 / 正确性 | 项目搜索把用户输入直接拼进 `LIKE` 模式，输入 `%` 或 `_` 会变成通配符，`q=%` 会返回全部项目。建议转义 `%`、`_` 和反斜杠并使用 `ESCAPE`。 | 已新增 `escape_like()`，SQL 增加 `ESCAPE '\'`；新增 `%` 与 `_` 查询用例，均返回“没有找到符合条件的项目”。 | 已闭环 |
| CR-04 | `tests/test_app.py:212-232` | 测试 | 上传测试只覆盖非法扩展名、伪造 PDF 和空文件，没有覆盖“未选择文件”“数据库写入失败回滚”“已删除材料文件”“路径式存储名”“413 请求体超限”。这些正是最容易留下孤儿文件和 500 错误的边界。 | 已新增 18 条边界用例：上传失败删除落盘文件、材料 404、路径式存储名、413、400/404 审批、并发 `rowcount=0`、数据库迁移与连接复用、种子截止日期回归等。覆盖率达到 100%。 | 已闭环 |
| CR-05 | `tests/test_app.py:70-80` | 测试 / 可读性 | 多条断言重复使用 `"中文".encode()`，可读性一般；建议统一为字节字面量。 | 已将可替换处改为 `b"..."`；其余保留 `.encode()` 的断言涉及中文常量拼接，暂不改动。 | 已闭环（部分） |
| CR-06 | `app.py:141` | 可读性 / 规模 | `_register_routes` 有 145 条语句，建议按 public / student / counselor / error handler 拆成多个注册函数。 | 不改：该函数只做 URL 与视图的声明式绑定，圈复杂度为 1；拆成多个函数会增加跳转成本。已加 `# noqa: PLR0915` 并在静态扫描记录中列为唯一生产代码豁免。 | 不修改（有理由） |
| CR-07 | `database.py:81-82` | 安全 / 凭据 | 演示账号密码固定写在种子数据中，公网部署时任何人可用 `student/student123`、`counselor/counselor123` 登录。建议改为环境变量或首次启动随机口令。 | 不修改：本仓库是课程演示环境，README 和测试报告均明确标注“仅课程环境”；真实部署前必须替换账号体系。已列入发布说明“已知问题”和下个版本改进项。 | 不修改（有理由） |

## 评审检查单

| 检查项 | 结果 | 说明 |
|---|---|---|
| 命名 | 通过 | 新增常量、`ValidatedUpload`、`escape_like` 命名清晰 |
| 可读性 | 通过 | 上传校验与路由职责分离；SQL 改为单参数 JSON 查询 |
| 边界与异常 | 通过 | 补齐 400/404/413、空文件、超大文件、存储失败回滚、并发审批 |
| 重复代码 | 通过 | jscpd 0 clones / 0% |
| 测试 | 通过 | 40 条测试全部通过，四项覆盖率 100%，增量覆盖 100% |
| 安全（密钥 / 注入 / 越权） | 通过（有已知限制） | S608 已消除；上传越权、材料越权、CSRF、安全响应头有测试；演示账号为已知限制 |

## 合并前检查

- [x] PR 描述写清“改了什么、为什么改、怎么验证”
- [x] 至少 3 条评审意见指明文件与行
- [x] 作者逐条回复“已改”或“不改 + 理由”
- [x] CI 质量门禁通过（Ruff / Bandit / pytest / coverage）
- [ ] 至少 1 名其他成员 approve（待评审人确认）
- [ ] 合并后删除 `feature/quality-gate` 分支（待合并执行）

## 验证方式

```powershell
.\.venv\Scripts\python.exe -m pytest -q --cov --cov-report=term-missing
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m bandit -r app.py database.py -ll
.\.venv\Scripts\diff-cover.exe reports/lab4/coverage-after.xml --compare-branch=HEAD
```

预期结果：40 passed、覆盖率 100%、Ruff 通过、Bandit 0 问题、增量覆盖 100%。
