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

- Markdown 文章支持层级目录结构：`content/专栏名/小专栏名/文章.md`
  - 例如：`content/技术/前端/React入门.md` 会创建一个"技术"专栏下的"前端"小专栏
  - 也可以直接在专栏下放置文章：`content/技术/文章.md`
  - 根目录下的文章（如 `content/文章.md`）不归属于任何专栏
- 评论使用 SQLite，默认路径 `data/rinblog.db`，可通过环境变量覆盖：

```bash
set RINBLOG_DB_PATH=./data/rinblog.db
```

### 标签集合定制

- 在 `content/tag_collections.yaml` 中定义标签集合，示例：

```yaml
collections:
  - name: Tutorials
    slug: tutorials
    description: Deep dive guides and how-tos.
    color: "#7c8cff"
    tags:
      - fastapi
      - tutorial
```

- 文章 front matter 中出现的标签会自动匹配集合并在页面上显示彩色徽标。
- 点击标签徽标可查看该集合下的所有相关文章（访问 `/collections/<collection_slug>`）。

### 多语言支持

- 在文章 front matter 中添加 `lang: en` 或 `lang: zh` 来指定文章语言。
- 默认语言为 `en`（英语），支持的语言包括：`en`（英语）、`zh`（中文）。
- 使用导航栏右上角的语言切换器可以在不同语言版本之间切换。
- 切换语言后，页面会只显示对应语言的文章。
- 示例：`welcome-to-rinblog.md`（英文）和 `welcome-to-rinblog-zh.md`（中文）是同一篇文章的不同语言版本。

## 测试

```bash
uv run pytest
```

## 构建静态站点（GitHub Pages / Cloudflare Pages）

```bash
uv run python scripts/build_static.py
```

生成内容输出到 `site/`。若部署到非顶级域名，可使用 `--base-url` 参数。

### Cloudflare Pages 部署

已添加 GitHub Actions 工作流 `.github/workflows/deploy-cloudflare.yml`。

1.  将代码推送到 GitHub。
2.  在 Cloudflare Dashboard 中创建一个新的 Pages 项目，连接你的 GitHub 仓库。
3.  或者使用 GitHub Actions 自动部署（需要在 Cloudflare 获取 Account ID 和 API Token 并配置到 GitHub Secrets）。
    *   `CLOUDFLARE_ACCOUNT_ID`
    *   `CLOUDFLARE_API_TOKEN`

**注意**：部署到 Cloudflare Pages 等静态托管服务时，评论功能（动态 API）将不可用。

### GitHub Pages 工作流

推送到 `main` 分支会触发 `.github/workflows/gh-pages.yml`，自动构建并发布静态站点。仓库需在 Settings → Pages 将 Source 设为 GitHub Actions。

## Vercel 部署

### 一键部署

点击下方按钮即可在 Vercel 上一键部署：

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/rinbarpen/RinBlog&env=RINBLOG_DB_PATH&envDescription=SQLite%20path%20for%20comments&envValue=/tmp/rinblog.db&project-name=rinblog&repository-name=RinBlog)

### 手动配置

1. 在 Vercel 连接仓库，Framework 选择 “Other”，Python 版本设置为 3.10。项目配置入口：`https://vercel.com/dashboard/settings/projects/<你的项目名称>`（将尖括号替换为真实项目名）。
2. 在该页面的 Environment Variables 中添加：

```
RINBLOG_DB_PATH=/tmp/rinblog.db
```

3. 其余保持默认，Vercel 会根据 `vercel.json` 调用 `api/index.py` 运行 FastAPI 应用。
