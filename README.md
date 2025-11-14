# RinBlog

FastAPI + Jinja2 博客，支持 Markdown 文章、分组、每日杂谈以及匿名评论。项目使用 `uv` 管理依赖。

## 环境准备

```bash
uv sync
```

## 本地开发

```bash
uv run uvicorn app.main:app --reload
```

访问 `http://localhost:8000`。

### 内容与评论存储

- Markdown 文章位于 `content/posts/`。
- 评论使用 SQLite，默认路径 `data/rinblog.db`，可通过环境变量覆盖：

```bash
set RINBLOG_DB_PATH=./data/rinblog.db
```

## 测试

```bash
uv run pytest
```

## 构建静态站点（GitHub Pages）

```bash
uv run python scripts/build_static.py --base-url your-repo-name
```

生成内容输出到 `site/`。若部署到顶级域名，可省略 `--base-url`。

### GitHub Pages 工作流

推送到 `main` 分支会触发 `.github/workflows/gh-pages.yml`，自动构建并发布静态站点。仓库需在 Settings → Pages 将 Source 设为 GitHub Actions。

## Vercel 部署

1. 在 Vercel 连接仓库，Framework 选择 “Other”，Python 版本设置为 3.10。
2. 配置环境变量：

```
RINBLOG_DB_PATH=/tmp/rinblog.db
```

3. 其余保持默认，Vercel 会根据 `vercel.json` 调用 `api/index.py` 运行 FastAPI 应用。

