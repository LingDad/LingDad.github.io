#!/usr/bin/env python3
"""
博客构建脚本 - 纯 Python 标准库，零依赖
从 content/*.md 生成 posts/*.html + index.html
"""
import os
import re
import html

SITE_TITLE = "LingDad's Blog"
SITE_DESC = "记录想法，分享故事"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE_DIR, 'content')
POSTS_DIR = os.path.join(BASE_DIR, 'posts')

# ===== 模板 =====

POST_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {site_title}</title>
    <link rel="icon" href="../favicon.svg" type="image/svg+xml">
    <link rel="icon" href="../favicon.ico" sizes="32x32">
    <link rel="apple-touch-icon" href="../apple-touch-icon.png">
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <header>
        <div class="container">
            <div class="header-row">
                <h1 class="site-title"><a href="../index.html"><img src="../favicon.svg" alt="十月天蝎" class="site-logo">{site_title}</a></h1>
                <button class="theme-toggle" id="themeToggle" aria-label="切换深色模式">☀️</button>
            </div>
            <p class="site-desc">{site_desc}</p>
        </div>
    </header>

    <main class="container">
        <a href="../index.html" class="back-link">← 返回首页</a>

        <div class="post-header">
            <h1>{title}</h1>
            <div class="post-meta">
                <span class="post-author">{author}</span>
                <span class="post-date">{date}</span>
            </div>
        </div>

        <div class="post-content">
{content_html}
        </div>

        <a href="../index.html" class="back-link">← 返回首页</a>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2026 {site_title}</p>
        </div>
    </footer>
    <script>
    (function(){{
        var btn=document.getElementById("themeToggle");
        var saved=localStorage.getItem("theme");
        if(saved==="dark"||(!saved&&window.matchMedia("(prefers-color-scheme: dark)").matches)){{document.documentElement.setAttribute("data-theme","dark");btn.textContent="🌙";}}
        btn.addEventListener("click",function(){{var d=document.documentElement.getAttribute("data-theme")==="dark";if(d){{document.documentElement.removeAttribute("data-theme");btn.textContent="☀️";localStorage.setItem("theme","light");}}else{{document.documentElement.setAttribute("data-theme","dark");btn.textContent="🌙";localStorage.setItem("theme","dark");}}}});
    }})();
    </script>
</body>
</html>'''

INDEX_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{site_title}</title>
    <link rel="icon" href="favicon.svg" type="image/svg+xml">
    <link rel="icon" href="favicon.ico" sizes="32x32">
    <link rel="apple-touch-icon" href="apple-touch-icon.png">
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <div class="container">
            <div class="header-row">
                <h1 class="site-title"><a href="index.html"><img src="favicon.svg" alt="十月天蝎" class="site-logo">{site_title}</a></h1>
                <button class="theme-toggle" id="themeToggle" aria-label="切换深色模式">☀️</button>
            </div>
            <p class="site-desc">{site_desc}</p>
        </div>
    </header>

    <main class="container">
        <section class="app-links" aria-labelledby="app-links-title">
            <div class="section-heading">
                <h2 id="app-links-title">我的应用</h2>
                <p>我做的两个小作品，点开就能直接使用。</p>
            </div>
            <div class="app-grid">
                <a class="app-card" href="https://lingdad.github.io/todo-app/" target="_blank" rel="noopener noreferrer" aria-label="打开 To-Do 应用">
                    <span class="app-card-glow" aria-hidden="true"></span>
                    <span class="app-card-top">
                        <span class="app-icon" aria-hidden="true">
                            <svg viewBox="0 0 24 24" role="presentation" focusable="false">
                                <path d="M9.2 16.6 4.9 12.3l1.4-1.4 2.9 2.9 8.5-8.5 1.4 1.4z"></path>
                                <path d="M19 12.5v6.2a1.3 1.3 0 0 1-1.3 1.3H5.3A1.3 1.3 0 0 1 4 18.7V6.3A1.3 1.3 0 0 1 5.3 5h9.2"></path>
                            </svg>
                        </span>
                        <span class="app-badge">Productivity</span>
                    </span>
                    <span class="app-info">
                        <strong>To-Do</strong>
                        <span class="app-summary">把想做的事排得清清楚楚，让每天更有节奏。</span>
                    </span>
                    <span class="app-card-bottom">
                        <span class="app-link-text">立即打开</span>
                        <span class="app-arrow" aria-hidden="true">↗</span>
                    </span>
                </a>
                <a class="app-card" href="https://lingdad.github.io/english_assistent/" target="_blank" rel="noopener noreferrer" aria-label="打开 English Assistant 应用">
                    <span class="app-card-glow" aria-hidden="true"></span>
                    <span class="app-card-top">
                        <span class="app-icon" aria-hidden="true">
                            <svg viewBox="0 0 24 24" role="presentation" focusable="false">
                                <path d="M12 4c4.4 0 8 2.9 8 6.5S16.4 17 12 17a9.8 9.8 0 0 1-2.8-.4L4.5 19l1.1-3.5A6 6 0 0 1 4 10.5C4 6.9 7.6 4 12 4z"></path>
                                <path d="M9.1 11.3h1.8l-.9-2.4zm-1.6 3.1 2.7-6.8h1.5l2.7 6.8h-1.5l-.6-1.6H8.8l-.6 1.6zm8.2 0V7.6h4.4v1.2h-2.9v1.6h2.5v1.2h-2.5v1.6H20v1.2z"></path>
                            </svg>
                        </span>
                        <span class="app-badge">Language</span>
                    </span>
                    <span class="app-info">
                        <strong>English Assistant</strong>
                        <span class="app-summary">随手练习英语，查词、表达和小对话都更方便。</span>
                    </span>
                    <span class="app-card-bottom">
                        <span class="app-link-text">去练一练</span>
                        <span class="app-arrow" aria-hidden="true">↗</span>
                    </span>
                </a>
            </div>
        </section>
        <section class="post-list">
{post_cards}
        </section>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2026 {site_title}</p>
        </div>
    </footer>
    <script>
    (function(){{
        var btn=document.getElementById("themeToggle");
        var saved=localStorage.getItem("theme");
        if(saved==="dark"||(!saved&&window.matchMedia("(prefers-color-scheme: dark)").matches)){{document.documentElement.setAttribute("data-theme","dark");btn.textContent="🌙";}}
        btn.addEventListener("click",function(){{var d=document.documentElement.getAttribute("data-theme")==="dark";if(d){{document.documentElement.removeAttribute("data-theme");btn.textContent="☀️";localStorage.setItem("theme","light");}}else{{document.documentElement.setAttribute("data-theme","dark");btn.textContent="🌙";localStorage.setItem("theme","dark");}}}});
    }})();
    </script>
</body>
</html>'''

POST_CARD_TEMPLATE = '''            <article class="post-card">
                <a href="posts/{slug}.html">
                    <h2 class="post-title">{title}</h2>
                    <div class="post-meta">
                        <span class="post-author">{author}</span>
                        <span class="post-date">{date}</span>
                    </div>
                    <p class="post-excerpt">{excerpt}</p>
                </a>
            </article>'''


def parse_frontmatter(text):
    """解析 YAML-like front matter（纯字符串解析，不依赖 pyyaml）"""
    meta = {}
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.S)
    if not m:
        return meta, text
    fm = m.group(1)
    body = text[m.end():]
    for line in fm.strip().split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            meta[key.strip()] = val.strip()
    return meta, body


def md_to_html(body):
    """简易 Markdown → HTML：空行分段"""
    paragraphs = []
    current = []
    for line in body.split('\n'):
        stripped = line.strip()
        if stripped == '':
            if current:
                paragraphs.append(' '.join(current))
                current = []
        else:
            current.append(stripped)
    if current:
        paragraphs.append(' '.join(current))

    html_parts = []
    for p in paragraphs:
        html_parts.append(f'            <p>{html.escape(p)}</p>')
    return '\n\n'.join(html_parts)


def get_excerpt(body, max_len=100):
    """提取摘要：第一段，截断到 max_len 字符"""
    for line in body.split('\n'):
        stripped = line.strip()
        if stripped:
            if len(stripped) > max_len:
                return stripped[:max_len] + '……'
            return stripped
    return ''


def build():
    os.makedirs(POSTS_DIR, exist_ok=True)

    posts = []

    # 读取所有 content/*.md
    for fname in sorted(os.listdir(CONTENT_DIR)):
        if not fname.endswith('.md'):
            continue
        filepath = os.path.join(CONTENT_DIR, fname)
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()

        meta, body = parse_frontmatter(text)
        title = meta.get('title', fname.replace('.md', ''))
        author = meta.get('author', '佚名')
        date = meta.get('date', '')
        created = meta.get('created', '')
        slug = meta.get('slug', fname.replace('.md', ''))

        content_html = md_to_html(body)
        excerpt = get_excerpt(body)

        posts.append({
            'title': title,
            'author': author,
            'date': date,
            'created': created,
            'slug': slug,
            'excerpt': excerpt,
            'content_html': content_html,
        })

    # 按日期降序，同日期按创建时间降序（新发表的排前面）
    posts.sort(key=lambda p: (p['date'], p['created'] or '0'), reverse=True)

    # 生成文章页
    for post in posts:
        post_html = POST_TEMPLATE.format(
            title=post['title'],
            author=post['author'],
            date=post['date'],
            content_html=post['content_html'],
            site_title=SITE_TITLE,
            site_desc=SITE_DESC,
        )
        out_path = os.path.join(POSTS_DIR, f"{post['slug']}.html")
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(post_html)
        print(f'  📄 posts/{post["slug"]}.html')

    # 生成首页
    cards = []
    for post in posts:
        card = POST_CARD_TEMPLATE.format(
            slug=post['slug'],
            title=post['title'],
            author=post['author'],
            date=post['date'],
            excerpt=post['excerpt'],
        )
        cards.append(card)

    index_html = INDEX_TEMPLATE.format(
        site_title=SITE_TITLE,
        site_desc=SITE_DESC,
        post_cards='\n'.join(cards),
    )
    out_path = os.path.join(BASE_DIR, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(index_html)
    print(f'  🏠 index.html')

    print(f'\n✅ 构建完成！共 {len(posts)} 篇文章')


if __name__ == '__main__':
    build()
