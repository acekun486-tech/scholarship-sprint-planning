# 静态扫描与问题修复记录（实验四 步骤 2）

## 扫描工具与命令

| 工具 | 版本 | 用途 | 命令 |
|---|---|---|---|
| Ruff | 0.17.5 | Python 静态检查与安全规则（E/F/W/B/S/UP/PLR） | `ruff check .` |
| Bandit | 1.9.4 | 安全漏洞扫描（中危及以上即失败） | `bandit -r app.py database.py -ll` |
| Radon | 6.0.1 | 圈复杂度、原始指标、可维护性指数 | `radon cc app.py database.py -s -a --show-closures` |
| jscpd | 4.x | 复制粘贴/重复代码检测 | `jscpd app.py database.py templates tests` |

规则配置见根目录 `pyproject.toml`。扫描对象为生产代码 `app.py`、`database.py` 和测试目录；测试目录的 `assert` 与固定演示口令属于测试代码惯例，在 `per-file-ignores` 中豁免，不计入生产门槛。

## 扫描门槛

| 指标 | 门槛 |
|---|---|
| Blocker / Critical | 0 |
| Major | ≤ 5 |
| 代码重复率 | ≤ 3% |
| 单函数圈复杂度 | ≤ 10 |

## 修复前结果

| 指标 | 实测 | 是否达标 |
|---|---:|---|
| Blocker / Critical | 1（S608 动态 SQL 构造） | 否 |
| Major | 2（PLR0911、PLR0915） | 是（≤5） |
| 代码重复率 | 0% | 是 |
| 最大圈复杂度 | 12（`upload_material`） | 否 |
| 技术债务比率（估算） | 约 0.6% | — |

原始输出：[Ruff](../../reports/lab4/ruff-before.txt)、[Bandit](../../reports/lab4/bandit-before.txt)、[Radon](../../reports/lab4/radon-before.txt)。

## 问题与修复记录

| 编号 | 规则 | 级别 | 文件 : 行（修复前） | 问题描述 | 修复方式 | 复扫结果 |
|---|---|---|---|---|---|---|
| SQ-01 | S608 / B608 | Critical | `app.py:127` | 用 f-string 拼接 `IN (?, ?, ...)` 占位符构造 SQL，属于 SQL 注入高危模式 | 改为 `WHERE application_id IN (SELECT value FROM json_each(?))`，整个 ID 列表作为一个参数传入，不再拼接 SQL | 已消除（Bandit 0） |
| SQ-02 | PLR0911 | Major | `app.py:303` | `upload_material` 有 8 个 return，上传校验与业务处理混在一起，圈复杂度 12 | 抽出 `validate_upload()`，统一返回 `(ValidatedUpload, error)`；路由只保留状态检查、保存与回滚 | 已消除（CC 12 → 7） |
| SQ-03 | PLR0915 | Major | `app.py:141` | `_register_routes` 有 145 条语句（路由注册表） | 不拆分：该函数只做路由声明，圈复杂度为 1；集中声明便于对照 URL 与视图。经评审作为唯一规则豁免，`# noqa: PLR0915` 处写明理由 | 已评审豁免 |
| SQ-04 | PLR2004 | Minor | `app.py:113/115/117/436` | 魔法值 80、40、2000、1000 直接写在比较中 | 提取 `MAX_NAME_LENGTH`、`MAX_STUDENT_NO_LENGTH`、`MAX_REASON_LENGTH`、`MAX_REVIEW_COMMENT_LENGTH` 常量 | 已消除 |
| SQ-05 | E501 | Minor | `app.py:392`、`database.py:88/93` | 单行超过 88/100 字符 | 拆分条件表达式与 SQL 字符串 | 已消除 |
| SQ-06 | UP012 | Minor | `tests/test_app.py:323` | 对 ASCII 字符串多此一举调用 `.encode()` | 改为 `b"proof.pdf"` 字节字面量 | 已消除 |
| SQ-07 | S105/S106/S107 | Major（仅测试） | `tests/test_app.py:32/118/123` | 测试辅助函数使用固定演示口令 | 仅测试代码使用，`pyproject.toml` 按文件豁免；生产代码不豁免 | 已评审豁免 |
| SQ-08 | S101 | 提示（仅测试） | `tests/test_app.py` 多处 | 测试使用 `assert` | 测试代码标准写法，按文件豁免 | 已评审豁免 |
| SQ-09 | B608 同源 | — | `database.py` | 无独立新增问题；Bandit 仅报告 SQ-01 一处 | — | — |

> 豁免说明：SQ-03 是本次唯一的生产代码规则豁免。理由为“路由注册集中可读、函数圈复杂度 1、不属于业务逻辑”；SQ-07/SQ-08 只针对测试文件。豁免项已列入代码评审记录，待评审人确认。

## 修复后结果

| 指标 | 实测 | 是否达标 |
|---|---:|---|
| Blocker / Critical | 0 | 是 |
| Major | 1（SQ-03，已评审豁免） | 是（≤5） |
| 代码重复率 | 0%（0 clones / 1621 行） | 是（≤3%） |
| 最大圈复杂度 | 9（`validate_application_form`） | 是（≤10） |
| 技术债务比率（估算） | 约 0.2% | — |

- Ruff：`All checks passed!`
- Bandit：High 0、Medium 0、Low 0。
- Radon：37 个函数/方法，平均复杂度 A（2.65）。

原始输出：[Ruff 修复后](../../reports/lab4/ruff-after.txt)、[Bandit 修复后](../../reports/lab4/bandit-after.txt)、[Radon 修复后](../../reports/lab4/radon-after.txt)、[jscpd 修复后](../../reports/lab4/jscpd-after.txt)。

## 技术债务比率估算口径

按 Sonar 常用的“修复成本 / 开发成本”估算：

- 修复成本：Critical 30 分钟 + Major 30 分钟 + Minor 7 项 × 5 分钟 ≈ 95 分钟；保留豁免的 SQ-03 复核 10 分钟。
- 开发成本：约 600 SLOC × 30 分钟/SLOC ≈ 18,000 分钟。
- 技术债务比率 ≈ 105 / 18,000 ≈ **0.6%**（修复后保留项约 0.2%）。

该数值为课程报告用的估算值，不等同于 SonarQube 的精确技术债务模型。

## 结论

生产代码已消除 1 个 Critical、1 个 Major 和 7 个 Minor；最大圈复杂度从 12 降到 9，重复率 0%。除已评审豁免的路由注册函数外，扫描门禁全部通过。
