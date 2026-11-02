# 在线部署说明

## 方案一：Render

项目已提供 `render.yaml`，会创建 Python Web Service、生成 `SECRET_KEY`，并把数据库和上传目录放到 `data/`。

### 使用 Blueprint

1. 打开：
   <https://render.com/deploy?repo=https://github.com/acekun486-tech/scholarship-sprint-planning>
2. 登录 Render，并授权读取 GitHub 仓库。
3. 确认 Blueprint 名称和配置。
4. 选择可用实例类型并部署。
5. 部署成功后访问 Render 提供的网址。
6. 在 GitHub 仓库首页点击 `About` 旁的齿轮，把网址填入 `Website`。

### 手动创建 Web Service

| 配置项 | 值 |
|---|---|
| Language | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT` |
| Health Check Path | `/healthz` |

环境变量：

```text
SECRET_KEY=<随机长字符串>
SESSION_COOKIE_SECURE=1
DATABASE_PATH=data/scholarship.db
UPLOAD_FOLDER=data/uploads
```

### 数据持久化

不挂载磁盘时，`data/` 会在重新部署或实例重建后丢失。需要保留申请数据时：

1. 在 Render 服务中添加持久化磁盘，挂载到 `/var/data`。
2. 修改环境变量：

```text
DATABASE_PATH=/var/data/scholarship.db
UPLOAD_FOLDER=/var/data/uploads
```

3. 重新部署。

SQLite 只适合课程演示和低并发场景。正式系统应迁移到 PostgreSQL，并把材料上传到对象存储。

## 方案二：GitHub Codespaces

`.devcontainer/devcontainer.json` 已配置 Python 3.13、依赖安装、5000 端口转发和 Public 可见性。

1. 仓库页面选择 `Code → Codespaces → Create codespace on main`。
2. 环境创建完成后执行：

```bash
FLASK_HOST=0.0.0.0 python app.py
```

3. 打开 `Ports` 面板中的 5000 端口。
4. 访问生成的 `*.app.github.dev` 地址。

Codespaces 主要用于临时验收，不适合长期提供服务。

## 健康检查

应用提供：

```text
GET /healthz
```

数据库可用时返回：

```json
{"status":"ok"}
```

## GitHub Pages 的限制

GitHub Pages 只能托管静态 HTML、CSS 和 JavaScript，不能执行 Flask、访问 SQLite 或处理文件上传。因此不能使用 GitHub Pages 展示本项目的完整可交互功能。
