# 高校学工平台——奖助学金管理子系统

本项目依据软件项目管理实验二的 Sprint Planning 实现，跑通“通知与项目查询—提交申请—上传材料—辅导员审批—学生查询结果”的核心闭环。

## Sprint 范围

| 用户故事 | 实现内容 | 页面或接口 |
|---|---|---|
| US01 | 查看奖助学金通知 | `/notices` |
| US02 | 查询项目、查看详情、条件和截止日期 | `/projects`、`/projects/<id>` |
| US03 | 填写并提交申请，服务端校验和重复提交防护 | `/apply/<project_id>` |
| US04 | 上传 PDF/PNG/JPG/JPEG，校验扩展名、文件签名和 5 MB 限制 | `/applications/<id>/upload` |
| US05 | 辅导员查看申请与材料、填写审批意见、更新状态 | `/counselor/applications` |
| US08 | 学生查看本人状态、意见和材料 | `/dashboard` |

US06（学院汇总上报）和 US07（名额管理与公示）不在当前 Sprint 内。

审批状态按以下规则流转：

```text
待审批 -> 通过
       -> 不通过
       -> 退回补充材料 -> 学生补传材料 -> 待审批
```

已通过或已不通过的申请不能再次审批，也不能继续上传材料。

## 技术栈与结构

- Python 3.10+
- Flask、Flask-WTF
- SQLite
- Jinja2、HTML/CSS
- pytest、pytest-cov

```text
app.py                应用工厂、路由、校验、权限和上传处理
database.py           表结构、种子数据、旧密码迁移和连接清理
templates/            页面模板
tests/test_app.py     业务、权限、上传与审批自动化测试
docs/                 Sprint Backlog、验收清单和测试记录
uploads/              本地材料存储目录
```

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = "replace-with-a-long-random-value"
python app.py
```

打开 <http://127.0.0.1:5000>。

未设置 `SECRET_KEY` 时，应用会生成本次进程使用的临时密钥，重启后现有登录会话失效。课程演示也应设置稳定密钥。

首次启动会创建 `scholarship.db` 并写入演示数据。旧版本创建的明文演示密码会在初始化时自动升级为哈希密码。

## 演示账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| 学生 | `student` | `student123` |
| 辅导员 | `counselor` | `counselor123` |

演示密码只用于课程环境。用户密码在数据库中保存为 Werkzeug 哈希，不保存明文。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q --cov --cov-report=term-missing
```

当前测试结果为 20 passed，总覆盖率 88%。实际执行记录见 `docs/test-report.md`。

## 安全与权限

- 表单启用 CSRF 防护，登录会话使用 HttpOnly、SameSite Cookie。
- 学生只能查看和下载本人申请材料；辅导员可查看审批所需材料。
- 申请提交同时执行重复检查和数据库唯一索引。
- 材料使用随机存储名，避免同名覆盖；下载时重新校验数据归属。
- 上传文件除扩展名外还校验 PDF、PNG、JPEG 文件签名。
- 服务端校验必填项、字段长度、审批意见、项目截止日期和状态流转。
- 响应增加 `nosniff`、同源 CSP、防嵌入等安全头。

## DoD 与课程边界

核心故事具备自动化测试、错误提示、角色权限、材料关联和运行文档。提交前仍需按 `docs/acceptance-checklist.md` 演示，由至少一名其他成员完成代码评审，并由 PO 对照故事验收标准确认。

本项目仍是课程原型：SQLite 和本地文件存储适合单机演示，未覆盖生产部署所需的对象存储、病毒扫描、审计日志、备份、邮件提醒、管理员名额维护和公示流程。
