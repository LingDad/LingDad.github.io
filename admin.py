#!/usr/bin/env python3
"""
博客后台管理 - 纯 Python 标准库，零依赖
功能：写文章、编辑、删除、一键发表（自动 build + git push）
"""
import os
import re
import json
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE_DIR, 'content')
PORT = 5000
# 简单密码保护，首次使用请修改
ADMIN_PASSWORD = 'lingdad2026'

# ===== HTML 模板 =====

LOGIN_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>登录 - 博客后台</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; background:#f0f2f5; display:flex; justify-content:center; align-items:center; min-height:100vh; }
.login-box { background:#fff; padding:40px; border-radius:12px; box-shadow:0 2px 12px rgba(0,0,0,0.1); width:360px; }
.login-box h1 { font-size:1.5rem; margin-bottom:24px; text-align:center; color:#1a1a2e; }
.login-box input { width:100%; padding:12px 16px; border:1px solid #ddd; border-radius:8px; font-size:1rem; margin-bottom:16px; }
.login-box button { width:100%; padding:12px; background:#2d5a27; color:#fff; border:none; border-radius:8px; font-size:1rem; cursor:pointer; }
.login-box button:hover { background:#3d7a35; }
.error { color:#e74c3c; font-size:0.9rem; margin-bottom:12px; text-align:center; }
</style>
</head>
<body>
<div class="login-box">
    <h1>🦂 博客后台</h1>
    {error}
    <form method="POST" action="/login">
        <input type="password" name="password" placeholder="输入密码" autofocus>
        <button type="submit">登录</button>
    </form>
</div>
</body>
</html>'''

ADMIN_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>博客后台</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; background:#f0f2f5; color:#333; }
.navbar { background:#1a1a2e; color:#fff; padding:16px 24px; display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; z-index:100; }
.navbar h1 { font-size:1.2rem; }
.navbar a { color:#aaa; text-decoration:none; font-size:0.9rem; }
.navbar a:hover { color:#fff; }
.container { max-width:960px; margin:24px auto; padding:0 24px; }
.btn { padding:8px 20px; border:none; border-radius:6px; cursor:pointer; font-size:0.9rem; transition:all 0.2s; }
.btn-primary { background:#2d5a27; color:#fff; }
.btn-primary:hover { background:#3d7a35; }
.btn-danger { background:#e74c3c; color:#fff; }
.btn-danger:hover { background:#c0392b; }
.btn-secondary { background:#666; color:#fff; }
.btn-secondary:hover { background:#555; }

/* 文章列表 */
.post-list { background:#fff; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.06); overflow:hidden; }
.post-item { display:flex; justify-content:space-between; align-items:center; padding:16px 24px; border-bottom:1px solid #f0f0f0; }
.post-item:last-child { border-bottom:none; }
.post-item:hover { background:#fafafa; }
.post-info h3 { font-size:1rem; margin-bottom:4px; }
.post-info .meta { font-size:0.85rem; color:#999; }
.post-actions { display:flex; gap:8px; }

/* 编辑器 */
.editor { display:none; background:#fff; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.06); padding:32px; margin-bottom:24px; }
.editor.active { display:block; }
.form-row { margin-bottom:16px; }
.form-row label { display:block; font-size:0.9rem; color:#666; margin-bottom:6px; font-weight:500; }
.form-row input, .form-row textarea { width:100%; padding:10px 14px; border:1px solid #ddd; border-radius:8px; font-size:1rem; font-family:inherit; }
.form-row input:focus, .form-row textarea:focus { outline:none; border-color:#2d5a27; box-shadow:0 0 0 2px rgba(45,90,39,0.15); }
.form-row textarea { min-height:400px; line-height:1.8; resize:vertical; }
.form-actions { display:flex; gap:12px; align-items:center; }
.slug-row { display:flex; gap:12px; }
.slug-row .form-row { flex:1; }

/* 状态提示 */
.toast { position:fixed; top:20px; right:20px; padding:14px 24px; border-radius:8px; color:#fff; font-size:0.95rem; z-index:200; transform:translateX(120%); transition:transform 0.3s ease; }
.toast.show { transform:translateX(0); }
.toast.success { background:#27ae60; }
.toast.error { background:#e74c3c; }
.toast.info { background:#2d5a27; }

/* 加载遮罩 */
.overlay { display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:150; justify-content:center; align-items:center; }
.overlay.active { display:flex; }
.overlay .spinner { color:#fff; font-size:1.2rem; }

.header-actions { display:flex; gap:12px; align-items:center; margin-bottom:24px; }
</style>
</head>
<body>
    <nav class="navbar">
        <h1>🦂 博客后台</h1>
        <div>
            <a href="https://lingdad.github.io" target="_blank" style="margin-right:16px">🌐 查看博客</a>
            <a href="/logout">退出</a>
        </div>
    </nav>

    <div class="container">
        <div class="header-actions">
            <button class="btn btn-primary" onclick="showEditor()">✏️ 写新文章</button>
        </div>

        <!-- 编辑器 -->
        <div class="editor" id="editor">
            <h2 id="editorTitle" style="margin-bottom:20px;">写新文章</h2>
            <input type="hidden" id="editingSlug" value="">
            <div class="form-row">
                <label>标题</label>
                <input type="text" id="postTitle" placeholder="文章标题">
            </div>
            <div class="slug-row">
                <div class="form-row">
                    <label>作者</label>
                    <input type="text" id="postAuthor" value="十月天蝎">
                </div>
                <div class="form-row">
                    <label>日期</label>
                    <input type="date" id="postDate">
                </div>
                <div class="form-row">
                    <label>文件名（slug）</label>
                    <input type="text" id="postSlug" placeholder="英文短名，如 my-article">
                </div>
            </div>
            <div class="form-row">
                <label>正文 <span style="color:#999; font-weight:normal;">（每段之间空一行）</span></label>
                <textarea id="postContent" placeholder="在这里写文章内容...&#10;&#10;段落之间空一行即可。"></textarea>
            </div>
            <div class="form-actions">
                <button class="btn btn-primary" onclick="savePost()">💾 保存草稿</button>
                <button class="btn btn-primary" onclick="publishPost()" style="background:#e67e22;">🚀 发表</button>
                <button class="btn btn-secondary" onclick="hideEditor()">取消</button>
            </div>
        </div>

        <!-- 文章列表 -->
        <div class="post-list" id="postList">
            <div style="padding:40px; text-align:center; color:#999;">加载中...</div>
        </div>
    </div>

    <!-- 加载遮罩 -->
    <div class="overlay" id="overlay">
        <div class="spinner">🚀 正在发表，构建并推送到 GitHub...</div>
    </div>

    <!-- 提示条 -->
    <div class="toast" id="toast"></div>

<script>
const today = new Date().toISOString().split('T')[0];
document.getElementById('postDate').value = today;

function showToast(msg, type='success') {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast ' + type + ' show';
    setTimeout(() => t.classList.remove('show'), 3000);
}

function showEditor(post) {
    const ed = document.getElementById('editor');
    if (post) {
        document.getElementById('editorTitle').textContent = '编辑文章';
        document.getElementById('editingSlug').value = post.slug;
        document.getElementById('postTitle').value = post.title;
        document.getElementById('postAuthor').value = post.author;
        document.getElementById('postDate').value = post.date;
        document.getElementById('postSlug').value = post.slug;
        document.getElementById('postContent').value = post.content;
        document.getElementById('postSlug').readOnly = true;
    } else {
        document.getElementById('editorTitle').textContent = '写新文章';
        document.getElementById('editingSlug').value = '';
        document.getElementById('postTitle').value = '';
        document.getElementById('postAuthor').value = '十月天蝎';
        document.getElementById('postDate').value = today;
        document.getElementById('postSlug').value = '';
        document.getElementById('postContent').value = '';
        document.getElementById('postSlug').readOnly = false;
    }
    ed.classList.add('active');
    document.getElementById('postTitle').focus();
}

function hideEditor() {
    document.getElementById('editor').classList.remove('active');
}

async function loadPosts() {
    const resp = await fetch('/api/posts');
    const posts = await resp.json();
    const list = document.getElementById('postList');
    if (posts.length === 0) {
        list.innerHTML = '<div style="padding:40px;text-align:center;color:#999;">还没有文章，点击"写新文章"开始吧</div>';
        return;
    }
    list.innerHTML = posts.map(p => `
        <div class="post-item">
            <div class="post-info">
                <h3>${esc(p.title)}</h3>
                <div class="meta">${esc(p.author)} · ${p.date} · ${p.slug}</div>
            </div>
            <div class="post-actions">
                <button class="btn btn-secondary" onclick='editPost(${JSON.stringify(JSON.stringify(p))})'>编辑</button>
                <button class="btn btn-danger" onclick="deletePost('${p.slug}')">删除</button>
            </div>
        </div>
    `).join('');
}

function editPost(jsonStr) {
    showEditor(JSON.parse(jsonStr));
}

function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

async function savePost() {
    const data = getFormData();
    if (!data) return;
    const resp = await fetch('/api/save', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(data)
    });
    const result = await resp.json();
    if (result.ok) {
        showToast('草稿已保存！');
        hideEditor();
        loadPosts();
    } else {
        showToast(result.error || '保存失败', 'error');
    }
}

async function publishPost() {
    const data = getFormData();
    if (!data) return;
    document.getElementById('overlay').classList.add('active');
    try {
        const resp = await fetch('/api/publish', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify(data)
        });
        const result = await resp.json();
        if (result.ok) {
            showToast('🎉 发表成功！已推送到 GitHub');
            hideEditor();
            loadPosts();
        } else {
            showToast(result.error || '发表失败', 'error');
        }
    } catch(e) {
        showToast('网络错误: ' + e.message, 'error');
    }
    document.getElementById('overlay').classList.remove('active');
}

async function deletePost(slug) {
    if (!confirm('确定删除这篇文章？')) return;
    document.getElementById('overlay').classList.add('active');
    try {
        const resp = await fetch('/api/delete', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({slug})
        });
        const result = await resp.json();
        if (result.ok) {
            showToast('已删除并推送');
            loadPosts();
        } else {
            showToast(result.error || '删除失败', 'error');
        }
    } catch(e) {
        showToast('错误: ' + e.message, 'error');
    }
    document.getElementById('overlay').classList.remove('active');
}

function getFormData() {
    const title = document.getElementById('postTitle').value.trim();
    const author = document.getElementById('postAuthor').value.trim();
    const date = document.getElementById('postDate').value;
    const slug = document.getElementById('postSlug').value.trim();
    const content = document.getElementById('postContent').value.trim();
    const editingSlug = document.getElementById('editingSlug').value;
    if (!title) { showToast('请填写标题', 'error'); return null; }
    if (!slug) { showToast('请填写文件名(slug)', 'error'); return null; }
    if (!content) { showToast('请填写正文', 'error'); return null; }
    if (!/^[a-z0-9-]+$/.test(slug)) { showToast('slug 只能包含小写字母、数字和横线', 'error'); return null; }
    return { title, author, date, slug, content, editingSlug };
}

// 标题自动生成 slug
document.getElementById('postTitle').addEventListener('input', function() {
    if (!document.getElementById('editingSlug').value && !document.getElementById('postSlug').readOnly) {
        // 不自动生成，中文 slug 不好看，留给用户手填
    }
});

loadPosts();
</script>
</body>
</html>'''


class BlogAdminHandler(BaseHTTPRequestHandler):
    sessions = set()  # 简易 session 管理

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

    def check_auth(self):
        cookie = self.headers.get('Cookie', '')
        for part in cookie.split(';'):
            part = part.strip()
            if part.startswith('session='):
                token = part.split('=', 1)[1]
                if token in self.sessions:
                    return True
        return False

    def send_html(self, html_content, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(length)

    def do_GET(self):
        if self.path == '/login' or self.path == '/':
            if self.check_auth():
                if self.path == '/login':
                    self.send_response(302)
                    self.send_header('Location', '/')
                    self.end_headers()
                else:
                    self.send_html(ADMIN_HTML)
            else:
                if self.path == '/':
                    self.send_response(302)
                    self.send_header('Location', '/login')
                    self.end_headers()
                else:
                    self.send_html(LOGIN_HTML.replace('{error}', ''))
        elif self.path == '/logout':
            self.send_response(302)
            self.send_header('Set-Cookie', 'session=; Max-Age=0; Path=/')
            self.send_header('Location', '/login')
            self.end_headers()
        elif self.path == '/api/posts':
            if not self.check_auth():
                self.send_json({'error': '未登录'}, 401)
                return
            self.handle_list_posts()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/login':
            body = self.read_body().decode('utf-8')
            params = urllib.parse.parse_qs(body)
            password = params.get('password', [''])[0]
            if password == ADMIN_PASSWORD:
                import secrets
                token = secrets.token_hex(16)
                self.sessions.add(token)
                self.send_response(302)
                self.send_header('Set-Cookie', f'session={token}; Path=/; HttpOnly')
                self.send_header('Location', '/')
                self.end_headers()
            else:
                self.send_html(LOGIN_HTML.replace('{error}', '<p class="error">密码错误</p>'))
            return

        if not self.check_auth():
            self.send_json({'error': '未登录'}, 401)
            return

        if self.path == '/api/save':
            self.handle_save(publish=False)
        elif self.path == '/api/publish':
            self.handle_save(publish=True)
        elif self.path == '/api/delete':
            self.handle_delete()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_list_posts(self):
        posts = []
        os.makedirs(CONTENT_DIR, exist_ok=True)
        for fname in sorted(os.listdir(CONTENT_DIR)):
            if not fname.endswith('.md'):
                continue
            filepath = os.path.join(CONTENT_DIR, fname)
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            meta, body = parse_frontmatter(text)
            posts.append({
                'title': meta.get('title', ''),
                'author': meta.get('author', ''),
                'date': meta.get('date', ''),
                'slug': meta.get('slug', fname.replace('.md', '')),
                'content': body.strip(),
            })
        posts.sort(key=lambda p: p['date'], reverse=True)
        self.send_json(posts)

    def handle_save(self, publish=False):
        data = json.loads(self.read_body().decode('utf-8'))
        slug = data.get('slug', '')
        title = data.get('title', '')
        author = data.get('author', '十月天蝎')
        date = data.get('date', '')
        content = data.get('content', '')

        if not slug or not title or not content:
            self.send_json({'ok': False, 'error': '标题、slug、正文不能为空'})
            return

        # 写入 md 文件
        md_content = f'---\ntitle: {title}\nauthor: {author}\ndate: {date}\nslug: {slug}\n---\n\n{content}\n'
        os.makedirs(CONTENT_DIR, exist_ok=True)
        md_path = os.path.join(CONTENT_DIR, f'{slug}.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        if publish:
            # 构建
            result = subprocess.run(
                ['python3', os.path.join(BASE_DIR, 'build.py')],
                cwd=BASE_DIR, capture_output=True, text=True
            )
            if result.returncode != 0:
                self.send_json({'ok': False, 'error': f'构建失败: {result.stderr}'})
                return

            # Git commit + push
            try:
                subprocess.run(['git', 'add', '-A'], cwd=BASE_DIR, check=True, capture_output=True)
                msg = f'发表: {title}'
                subprocess.run(['git', 'commit', '-m', msg], cwd=BASE_DIR, check=True, capture_output=True)
                result = subprocess.run(['git', 'push'], cwd=BASE_DIR, capture_output=True, text=True)
                if result.returncode != 0:
                    self.send_json({'ok': False, 'error': f'推送失败: {result.stderr}'})
                    return
            except subprocess.CalledProcessError as e:
                self.send_json({'ok': False, 'error': f'Git 操作失败: {e}'})
                return

            self.send_json({'ok': True, 'message': '发表成功'})
        else:
            self.send_json({'ok': True, 'message': '草稿已保存'})

    def handle_delete(self):
        data = json.loads(self.read_body().decode('utf-8'))
        slug = data.get('slug', '')
        if not slug:
            self.send_json({'ok': False, 'error': 'slug 不能为空'})
            return

        md_path = os.path.join(CONTENT_DIR, f'{slug}.md')
        html_path = os.path.join(BASE_DIR, 'posts', f'{slug}.html')

        if os.path.exists(md_path):
            os.remove(md_path)
        if os.path.exists(html_path):
            os.remove(html_path)

        # 重新构建
        subprocess.run(['python3', os.path.join(BASE_DIR, 'build.py')],
                       cwd=BASE_DIR, capture_output=True)

        # Git commit + push
        try:
            subprocess.run(['git', 'add', '-A'], cwd=BASE_DIR, check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', f'删除: {slug}'], cwd=BASE_DIR, check=True, capture_output=True)
            subprocess.run(['git', 'push'], cwd=BASE_DIR, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass

        self.send_json({'ok': True})


def parse_frontmatter(text):
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


def main():
    print(f'''
╔══════════════════════════════════════╗
║     🦂 LingDad 博客后台管理         ║
╠══════════════════════════════════════╣
║  地址: http://localhost:{PORT}          ║
║  密码: {ADMIN_PASSWORD}               ║
╚══════════════════════════════════════╝
    ''')
    server = HTTPServer(('0.0.0.0', PORT), BlogAdminHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n👋 后台已关闭')
        server.server_close()


if __name__ == '__main__':
    main()
