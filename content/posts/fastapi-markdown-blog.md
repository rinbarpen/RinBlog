---
title: Building a Markdown Blog with FastAPI
date: 2025-11-11
group:
  name: Development
  slug: development
summary: A short outline of how this blog stitches together FastAPI, Jinja2, and Markdown content.
tags:
  - fastapi
  - markdown
  - tutorial
---

Creating a lightweight blog does not require a heavyweight CMS. With FastAPI and Jinja2 you can render Markdown files directly into HTML templates.

Key ingredients:

1. A content loader that parses front matter and turns Markdown into HTML.
2. A router that serves list, detail, and grouping views.
3. An anonymous comment system powered by SQLModel.

This project keeps things simple enough to extend while still giving a comfortable authoring workflow.


