---
title: "Building this blog"
description: "Why I chose Astro for a minimal static blog and what the setup looks like."
pubDate: 2026-05-07
tags: ["notes", "build"]
---

Static sites are fast by default. No server, no database, no runtime — just files.

Astro fits that model well. It outputs plain HTML, supports Markdown natively, and adds only what you need. The blog template gives you posts, RSS, and a sitemap out of the box.

The setup here is intentionally simple:

- Posts live in `src/content/blog/` as Markdown files
- Each post has frontmatter: title, description, date, tags
- Pages are generated at build time — no client-side routing
- CSS is plain, no framework

Building is one command:

```bash
npm run build
```

Output goes to `dist/`. Deploy anywhere that serves static files.
