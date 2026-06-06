#!/usr/bin/env python3
"""Turn the bilingual copy in Why_Is_It_Always_About_You_ZH into a Chinese-only edition.

Per content file (one element per line):
  - line carrying `trans-zh`  -> Chinese block: keep, strip the trans-zh marker + lang attr
  - line that is an English <h2>/<h3> heading -> drop
  - line that is a <p> with real text (English prose) -> drop
  - <p> that is only page-anchors / whitespace, <div>, wrappers, blanks -> keep
Then translate <title>, nav.xhtml TOC, titlepage, and content.opf metadata.
"""
import re, glob, os, html

ROOT = "/home/user/Yohoa/Why_Is_It_Always_About_You_ZH"
ZH_TITLE = "为什么总是以你为中心？（中文版）"

tag_re = re.compile(r"<[^>]+>")

def strip_tags_text(line):
    return html.unescape(tag_re.sub("", line)).strip()

def clean_zh_line(line):
    # remove the trans-zh class token (it appears as part of a class value)
    line = line.replace(' trans-zh"', '"').replace('trans-zh ', '')
    # remove lang attribute
    line = re.sub(r'\s+lang="zh-CN"', "", line)
    return line

def process_content(path):
    out = []
    for line in open(path, encoding="utf-8").read().split("\n"):
        s = line.lstrip()
        if "trans-zh" in line:
            out.append(clean_zh_line(line))
            continue
        # English headings -> drop
        if s.startswith("<h2") or s.startswith("<h3"):
            continue
        # paragraphs: drop only if they carry real prose text
        if s.startswith("<p"):
            if strip_tags_text(line):
                continue  # English prose
            out.append(line)   # anchor-only / empty paragraph -> keep
            continue
        out.append(line)
    text = "\n".join(out)
    # localize the per-file <title>
    text = re.sub(r"<title>.*?</title>", f"<title>{ZH_TITLE}</title>", text, count=1)
    open(path, "w", encoding="utf-8").write(text)
    # return the first cleaned Chinese h2 inner text (for the TOC)
    m = re.search(r'<h2[^>]*class="h"[^>]*>(.*?)</h2>', text, re.S)
    if m:
        return strip_tags_text(m.group(1))
    return None

# ---- process all spine content files, in spine order ----
files = [f"part{n:04d}" for n in range(8, 33) if n not in ()]
toc_label = {}
for stem in files:
    p = os.path.join(ROOT, "OEBPS", "Text", stem + ".html")
    if os.path.exists(p):
        label = process_content(p)
        toc_label[stem + ".html"] = label

# ---- nav.xhtml: rewrite each TOC anchor text with the chapter's own Chinese heading ----
nav_path = os.path.join(ROOT, "nav.xhtml")
nav = open(nav_path, encoding="utf-8").read()
def repl_anchor(m):
    href = m.group(1)
    fname = href.split("/")[-1]
    label = toc_label.get(fname)
    if label:
        return f'<a href="{href}">{html.escape(label)}</a>'
    return m.group(0)
nav = re.sub(r'<a href="(OEBPS/Text/part\d+\.html)">.*?</a>', repl_anchor, nav, flags=re.S)
nav = nav.replace("<title>Navigation</title>", "<title>目录</title>")
nav = nav.replace('lang="en" xml:lang="en"', 'lang="zh" xml:lang="zh"')
nav = nav.replace('<a href="titlepage.xhtml" epub:type="cover">Cover</a>',
                  '<a href="titlepage.xhtml" epub:type="cover">封面</a>')
open(nav_path, "w", encoding="utf-8").write(nav)

# ---- titlepage.xhtml ----
tp_path = os.path.join(ROOT, "titlepage.xhtml")
tp = open(tp_path, encoding="utf-8").read()
tp = tp.replace("<title>Cover</title>", "<title>封面</title>")
open(tp_path, "w", encoding="utf-8").write(tp)

# ---- content.opf metadata ----
opf_path = os.path.join(ROOT, "content.opf")
opf = open(opf_path, encoding="utf-8").read()
opf = re.sub(r'(<dc:title id="id">).*?(</dc:title>)', rf'\g<1>{ZH_TITLE}\g<2>', opf)
opf = opf.replace("<dc:language>en</dc:language>", "<dc:language>zh</dc:language>")
opf = re.sub(r'(property="file-as">)Why Is It Always About You\?(</opf:meta>)',
             rf'\g<1>{ZH_TITLE}\g<2>', opf)
open(opf_path, "w", encoding="utf-8").write(opf)

print("TOC labels:")
for k in files:
    fn = k + ".html"
    if fn in toc_label:
        print(f"  {fn}: {toc_label[fn]}")
print("done")
