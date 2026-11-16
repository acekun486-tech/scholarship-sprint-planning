# 单元测试覆盖率记录（实验四 步骤 1）

## 执行环境

| 项目 | 值 |
|---|---|
| 日期 | 2026-11-15 至 2026-11-16 |
| 操作系统 | Windows |
| Python | 3.14.6 |
| pytest / pytest-cov | 8.4.2 / 7.1.0 |
| coverage | 7.16.2 |
| 统计范围 | `app.py`、`database.py`（模板与静态资源不属于 Python 语句覆盖范围） |

## 执行命令

```powershell
.\.venv\Scripts\python.exe -m pytest -q --cov --cov-report=term-missing `
  --cov-report=json:reports/lab4/coverage-after.json `
  --cov-report=xml:reports/lab4/coverage-after.xml
.\.venv\Scripts\python.exe tools/coverage_metrics.py reports/lab4/coverage-after.json
.\.venv\Scripts\diff-cover.exe reports/lab4/coverage-after.xml --compare-branch=HEAD
```

## 覆盖率结果

实验室要求的“语句、分支、函数、行”四项指标如下。函数覆盖率按“函数体至少执行一行”估算（含嵌套函数），行覆盖率按已执行可执行行 / 全部可执行行计算。

### 改造前基线（原代码 + 原 22 条用例）

| 文件 | 语句 % | 分支 % | 函数 % | 行 % |
|---|---:|---:|---:|---:|
| `app.py` | 90.1% (254/282) | 81.1% (60/74) | 93.3% (28/30) | 90.1% (254/282) |
| `database.py` | 88.9% (32/36) | 80.0% (8/10) | 100.0% (4/4) | 88.9% (32/36) |
| **合计** | **89.9%** (286/318) | **81.0%** (68/84) | **94.1%** (32/34) | **89.9%** (286/318) |

### 补测前后对比（同一版改造后代码）

| 文件 / 模块 | 语句 % | 分支 % | 函数 % | 行 % | 补测后 | 是否达标 |
|---|---:|---:|---:|---:|---:|---|
| `app.py` | 90.9% | 81.6% | 93.8% | 90.9% | **100%** | 是 |
| `database.py` | 88.9% | 80.0% | 100.0% | 88.9% | **100%** | 是 |
| **合计** | **90.7%** | **81.4%** | **94.4%** | **90.7%** | **100%** | 是 |

补测后共 **40 条测试全部通过**；语句 334/334、分支 86/86、函数 36/36、行 334/334。核心模块 `app.py` 与 `database.py` 均达到 100%，高于“核心模块 ≥ 80%”的门槛。

> 2026-11-16 复跑时发现：种子数据使用固定截止日期 `2026-11-15`，到期后申请流程测试全部失败。已把种子截止日期改为“当天 + 30/45 天”，并新增 `test_seeded_projects_have_open_deadlines` 防止回归；`database.py` 因此增加 2 条语句，总数由 332 变为 334，覆盖率仍为 100%。

> 说明：本项目只有 2 个 Python 源文件，无法机械凑出“3 个文件”。因此按“文件 + 函数”两个维度补充：下节列出基线中覆盖率最低的 3 个函数，并说明补测用例。

### 基线中行覆盖最低的 3 个函数

| 函数 | 行范围 | 基线行覆盖 | 补测方式 |
|---|---|---:|---|
| `app.py:bad_request` | 471-473 | 0% | 新增非法审批决定用例，触发 400 错误页 |
| `app.py:request_too_large` | 491-493 | 0% | 新增 6 MB 请求体用例，触发 413 错误页 |
| `app.py:project_is_open` | 104-107 | 50% | 新增非法日期、空日期与当天截止的边界断言 |

### 新增的 18 条用例

| 类别 | 覆盖内容 |
|---|---|
| 表单边界 | 姓名 81 字、学号 41 字、理由 2001 字；GET 申请页；未知项目 404 |
| 上传边界 | 未选择文件；数据库写入失败时删除已落盘文件；存储文件名含路径；已删除材料文件 |
| 审批边界 | 非法决定 400；审批意见 1001 字；申请不存在 404；并发状态变化（`rowcount=0`） |
| 请求边界 | 6 MB 请求体触发 413；匿名访问重定向登录；未知用户名登录 |
| 数据库与搜索 | 唯一索引冲突降级、旧明文密码升级、连接复用；`%`/`_` 通配符转义 |
| 种子数据 | 种子项目截止日期必须晚于当天，避免演示与测试随日期过期 |

## 增量代码覆盖率

`diff-cover` 以当前 `main`（HEAD）为基线统计本次修改的 Python 行：

```text
Total:   49 lines
Missing: 0 lines
Coverage: 100%
```

增量覆盖率 **100%**，高于“增量代码 ≥ 60%”的门槛。原始输出见 [diff-cover-after.txt](../../reports/lab4/diff-cover-after.txt)。

## 证据文件

- [改造前覆盖率报告](../../reports/lab4/coverage-before.md) / [JSON](../../reports/lab4/coverage-before.json)
- [补测前覆盖率报告](../../reports/lab4/coverage-pre-tests.md) / [JSON](../../reports/lab4/coverage-post-refactor-pre-tests.json)
- [补测后覆盖率报告](../../reports/lab4/coverage-after.md) / [JSON](../../reports/lab4/coverage-after.json) / [XML](../../reports/lab4/coverage-after.xml)
- [pytest 补测后输出](../../reports/lab4/pytest-coverage-after.txt)
- 可视化 HTML：本地执行 `pytest --cov --cov-report=html` 后打开 `htmlcov/index.html`

## 结论

四项覆盖率均达标，补测有效：同一版代码在补测前为 90.7% / 81.4% / 94.4% / 90.7%，补测后全部为 100%。覆盖率提升来自新增断言和边界用例，没有用 `# pragma: no cover` 绕过。
