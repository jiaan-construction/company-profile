#!/usr/bin/env python3
"""从 4 份 markdown 生成 index.html（GitHub Pages 用）。

改了 .md 就跑一次 `python3 build.py`，再把 index.html 一起推。
只依赖标准库——这台机器上没装 markdown 库，也不打算为一页纸装。
"""
import html
import pathlib
import re

HERE = pathlib.Path(__file__).parent

# ── 极小 markdown 子集转换器 ────────────────────────────────
# 只支持这几份稿子实际用到的语法：h1-h3、表格、无序列表、引用、
# 分隔线、粗体、斜体、链接、行内代码、段落。不求通用，求可控。

def _inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', t)
    def link(m):
        text, href = m.group(1), m.group(2)
        if href.endswith('.md'):          # 站内 md 链接指向本页锚点
            href = '#' + re.sub(r'[^a-z0-9]+', '-', href[:-3].lower()).strip('-')
        ext = ' target="_blank" rel="noopener"' if href.startswith('http') else ''
        return f'<a href="{html.escape(href)}"{ext}>{text}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, t)


def md(src):
    out, lines, i = [], src.split('\n'), 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
        elif ln.startswith('|'):                                  # 表格
            block = []
            while i < len(lines) and lines[i].startswith('|'):
                block.append(lines[i]); i += 1
            cells = [[c.strip() for c in r.strip('|').split('|')] for r in block]
            sep = len(cells) > 1 and all(set(c) <= set('-: ') and '-' in c for c in cells[1])
            head, body = (cells[0], cells[2:]) if sep else (None, cells)
            out.append('<div class="tw"><table>')
            if head and any(c.strip() for c in head):   # 全空表头不渲染，否则出一条空灰带
                out.append('<thead><tr>' + ''.join(f'<th>{_inline(c)}</th>' for c in head) + '</tr></thead>')
            out.append('<tbody>')
            for row in body:
                out.append('<tr>' + ''.join(f'<td>{_inline(c)}</td>' for c in row) + '</tr>')
            out.append('</tbody></table></div>')
        elif re.match(r'^#{1,4} ', ln):                            # 标题
            lvl = len(ln) - len(ln.lstrip('#'))
            out.append(f'<h{lvl}>{_inline(ln[lvl:].strip())}</h{lvl}>')
            i += 1
        elif ln.startswith('> '):                                  # 引用
            block = []
            while i < len(lines) and lines[i].startswith('>'):
                block.append(lines[i].lstrip('>').strip()); i += 1
            out.append('<blockquote>' + '<br>'.join(_inline(b) for b in block if b) + '</blockquote>')
        elif re.match(r'^[-*] ', ln):                              # 列表
            items = []
            while i < len(lines) and re.match(r'^[-*] ', lines[i]):
                items.append(lines[i][2:].strip()); i += 1
            out.append('<ul>' + ''.join(f'<li>{_inline(x)}</li>' for x in items) + '</ul>')
        elif re.match(r'^-{3,}$', ln.strip()):
            out.append('<hr>'); i += 1
        else:                                                      # 段落
            para = []
            while i < len(lines) and lines[i].strip() and not re.match(r'^(\||#{1,4} |> |[-*] |-{3,}$)', lines[i]):
                para.append(lines[i].strip()); i += 1
            out.append('<p>' + _inline('<br>'.join(para)).replace('&lt;br&gt;', '<br>') + '</p>')
    return '\n'.join(out)


def strip_h1(src):
    """去掉每份稿子的一级标题与紧随的副标题块——页面自己有 header。"""
    lines = src.split('\n')
    while lines and not lines[0].startswith('# '):
        lines.pop(0)
    lines.pop(0)
    while lines and (lines[0].startswith('**') or lines[0].startswith('*') or
                     lines[0].startswith('UEN') or not lines[0].strip() or
                     lines[0].startswith('> ')):
        lines.pop(0)
    return '\n'.join(lines)


DOCS = {
    'en':    'Company-Profile-EN.md',
    'zh':    '公司简介_中文.md',
    'track': 'Track-Record.md',
    'certs': 'Certifications.md',
}
def clean(h):
    """去掉段首那条 <hr>——原稿里它是用来隔开抬头的，页面已经有信头了。"""
    return h[4:].lstrip() if h.startswith('<hr>') else h


body = {k: clean(md(strip_h1((HERE / v).read_text(encoding='utf-8')))) for k, v in DOCS.items()}
(HERE / 'index.html').write_text(
    (HERE / 'template.html').read_text(encoding='utf-8')
    .replace('<!--EN-->',    body['en'])
    .replace('<!--ZH-->',    body['zh'])
    .replace('<!--TRACK-->', body['track'])
    .replace('<!--CERTS-->', body['certs']),
    encoding='utf-8')
print('index.html 已生成', (HERE / 'index.html').stat().st_size, 'bytes')
