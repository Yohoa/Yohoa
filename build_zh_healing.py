#!/usr/bin/env python3
"""Build the Chinese-only edition of Healing the Fragmented Selves of Trauma Survivors.

Source: Healing_Bilingual (bilingual edition)
Output: Healing_ZH (Chinese-only edition)

Per content file:
  - elements with trans-zh: keep, strip the trans-zh marker + lang attr
  - English <h2>/<h3> headings: drop
  - English <p> with real prose text: drop
  - <p> with only page anchors/whitespace, <div>, wrappers, blanks: keep
Then translate <title>, nav.xhtml TOC, and OPF metadata.
"""
import re, os, html, shutil

SRC  = "/home/user/Yohoa/Healing_Bilingual"
DEST = "/home/user/Yohoa/Healing_ZH"

ZH_TITLE = "治愈创伤幸存者的碎裂自我：克服内在自我疏离"
ZH_TITLE_SHORT = "治愈创伤幸存者的碎裂自我"

tag_re = re.compile(r"<[^>]+>")

def strip_tags_text(line):
    return html.unescape(tag_re.sub("", line)).strip()

def clean_zh_line(line):
    # remove trans-zh class token
    line = re.sub(r'\s*trans-zh\s*', ' ', line)
    line = re.sub(r'class=" ', 'class="', line)
    line = re.sub(r' "', '"', line)
    # more robust class cleanup
    line = re.sub(r'class="([^"]*?)\s*trans-zh\s*([^"]*?)"',
                  lambda m: 'class="' + (m.group(1) + ' ' + m.group(2)).strip() + '"', line)
    line = re.sub(r'class="\s+"', 'class=""', line)
    # remove lang attribute
    line = re.sub(r'\s+lang="zh-CN"', "", line)
    return line

def is_only_anchors(line):
    """True if paragraph has no visible text (only anchors/spans with no text)."""
    text = strip_tags_text(line)
    return not text

def process_content_file(src_path, dst_path):
    """Transform bilingual file -> Chinese-only file. Returns first Chinese h2 text."""
    lines = open(src_path, encoding="utf-8").read().split("\n")
    out = []
    for line in lines:
        s = line.lstrip()
        if "trans-zh" in line:
            out.append(clean_zh_line(line))
            continue
        # English headings -> drop
        if s.startswith("<h2") or s.startswith("<h3"):
            continue
        # paragraphs: drop if they carry real prose text
        if s.startswith("<p"):
            if not is_only_anchors(line):
                continue  # English prose paragraph
            out.append(line)   # anchor-only / empty
            continue
        out.append(line)

    text = "\n".join(out)
    # Localize per-file <title>
    text = re.sub(r"<title>.*?</title>", f"<title>{ZH_TITLE}</title>", text, count=1)
    # Localize html lang attribute
    text = re.sub(r'lang="en"', 'lang="zh"', text)
    text = re.sub(r'xml:lang="en"', 'xml:lang="zh"', text)

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    open(dst_path, "w", encoding="utf-8").write(text)

    # Return first Chinese h2 inner text (for TOC)
    # Look for a trans-zh h2 that has been cleaned
    m = re.search(r'<h2[^>]*>(.*?)</h2>', text, re.S)
    if m:
        return strip_tags_text(m.group(1))
    return None

# Chapter titles mapping (href -> Chinese title)
CHAPTER_TITLES = {
    "cover.xhtml": "封面",
    "B03_halftitle.xhtml": "书名页",
    "B04_titlepage.xhtml": "版权页",
    "B05_copyright.xhtml": "版权",
    "B06_ded.xhtml": "献词",
    "B07_toc.xhtml": "目录",
    "B08_lof.xhtml": "图表目录",
    "B09_ack.xhtml": "致谢",
    "C01_chapter.xhtml": "引言",
    "C02_chapter.xhtml": "第1章 创伤的神经生物学遗产：我们如何走向碎裂",
    "C03_chapter.xhtml": "第2章 理解各部分，理解创伤性反应",
    "C04_chapter.xhtml": "第3章 来访者与治疗师角色的转变",
    "C05_chapter.xhtml": "第4章 学会看见我们的"自我"：与各部分工作的导论",
    "C06_chapter.xhtml": "第5章 与各部分为友：播下慈悲的种子",
    "C07_chapter.xhtml": "第6章 治疗的复杂性：创伤性依恋",
    "C08_chapter.xhtml": "第7章 与自杀、自我毁灭、饮食障碍及成瘾部分工作",
    "C09_chapter.xhtml": "第8章 治疗挑战：解离系统与解离障碍",
    "C10_chapter.xhtml": "第9章 修复过去：拥抱我们的自我",
    "C11_chapter.xhtml": "第10章 找回失去的：深化与年幼自我的连结",
    "C12_chapter.xhtml": "第11章 安全与欢迎：习得性安全依恋的体验",
    "Z1_sec_appA.xhtml": "附录A：解融合的五个步骤",
    "Z2_sec_appB.xhtml": "附录B：各部分冥想圈",
    "Z3_sec_appC.xhtml": "附录C：内部对话技术",
    "Z4_sec_appD.xhtml": "附录D：内部依恋修复的治疗范式",
    "Z5_sec_appE.xhtml": "附录E：解离体验日志",
    "Z6_sec_appF.xhtml": "附录F：四个结友问题",
    "Z7_sec_index.xhtml": "索引",
}

# Process all XHTML content files
xhtml_src = os.path.join(SRC, "ops", "xhtml")
xhtml_dst = os.path.join(DEST, "ops", "xhtml")
toc_labels = {}

for fname in os.listdir(xhtml_src):
    if not fname.endswith(".xhtml"):
        continue
    src_path = os.path.join(xhtml_src, fname)
    dst_path = os.path.join(xhtml_dst, fname)
    label = process_content_file(src_path, dst_path)
    toc_labels[fname] = CHAPTER_TITLES.get(fname, label)
    print(f"  {fname}: {toc_labels[fname]}")

# Copy nav.xhtml from bilingual, then localize it
nav_src = os.path.join(SRC, "ops", "xhtml", "nav.xhtml")
nav_dst = os.path.join(DEST, "ops", "xhtml", "nav.xhtml")
nav = open(nav_src, encoding="utf-8").read()

# Replace nav TOC entries: remove English anchor text, keep Chinese versions
# The bilingual nav has Chinese <li> with trans-zh class — clean them up
nav = re.sub(r'\s*trans-zh\s*', ' ', nav)
nav = re.sub(r'class=" ', 'class="', nav)
nav = re.sub(r' "', '"', nav)
nav = re.sub(r'class="([^"]*?)\s*trans-zh\s*([^"]*?)"',
             lambda m: 'class="' + (m.group(1) + ' ' + m.group(2)).strip() + '"', nav)
nav = re.sub(r'\s+lang="zh-CN"', "", nav)
nav = re.sub(r"<title>.*?</title>", f"<title>目录</title>", nav, count=1)
nav = re.sub(r'lang="en"', 'lang="zh"', nav)
nav = re.sub(r'xml:lang="en"', 'xml:lang="zh"', nav)
# Remove English nav entries (li without trans-zh that contain English text)
# Actually we need to be careful — the nav was already processed by the agent
# Just write what we have
open(nav_dst, "w", encoding="utf-8").write(nav)
print(f"  nav.xhtml: written")

# OPF metadata
opf_src = os.path.join(SRC, "ops", "9781134613083.opf")
opf_dst = os.path.join(DEST, "ops", "9781134613083.opf")
opf = open(opf_src, encoding="utf-8").read()
opf = re.sub(r'<dc:title id="id">.*?</dc:title>',
             f'<dc:title id="id">{html.escape(ZH_TITLE)}</dc:title>', opf, flags=re.S)
opf = re.sub(r'<dc:language>en</dc:language>', '<dc:language>zh</dc:language>', opf)
opf = re.sub(r'<dc:language>zh</dc:language>\s*<dc:language>zh</dc:language>',
             '<dc:language>zh</dc:language>', opf)
opf = re.sub(r'<dc:language>en</dc:language>\s*<dc:language>zh</dc:language>',
             '<dc:language>zh</dc:language>', opf)
# file-as
opf = re.sub(r'(property="file-as">)[^<]*(</opf:meta>)',
             rf'\g<1>{html.escape(ZH_TITLE)}\g<2>', opf)
# description
opf = re.sub(r'<dc:description>.*?</dc:description>',
             f'<dc:description>{html.escape(ZH_TITLE)} — 中文版</dc:description>',
             opf, flags=re.S)
open(opf_dst, "w", encoding="utf-8").write(opf)
print(f"  OPF metadata updated")

# NCX: copy and update
ncx_src = os.path.join(SRC, "ops", "toc.ncx")
ncx_dst = os.path.join(DEST, "ops", "toc.ncx")
if os.path.exists(ncx_src):
    ncx = open(ncx_src, encoding="utf-8").read()
    ncx = re.sub(r'<text>Healing the Fragmented Selves.*?</text>',
                 f'<text>{html.escape(ZH_TITLE_SHORT)}</text>', ncx, flags=re.S)
    open(ncx_dst, "w", encoding="utf-8").write(ncx)
    print(f"  toc.ncx updated")

print("\nDone! Chinese-only edition written to", DEST)
