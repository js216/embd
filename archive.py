#!/usr/bin/env python3
import os
import re
import sys
import datetime
from pathlib import Path
from collections import defaultdict

# ---------- HTML intro and outro ----------

HTML_INTRO = """<!DOCTYPE html>
<html lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="author" content="Jakob Kastelic">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Browse the full archive of articles by Jakob Kastelic, organized by date and by topic."/>
<link rel="license" href="https://creativecommons.org/licenses/by/4.0/" />
<link rel="stylesheet" href="style.css">
<title>Archive</title>
</head>
<body>
<header class="site-banner">
<div class="logo">
<a href="http://embd.cc"><img src="favicon.ico" alt="logo">embd.cc : Archive</a>
</div>
<nav class="site-nav">
<a href="archive">Archive</a>
<a href="about">About</a>
</nav>
</header>
<p><em>See also the <a href="#topical">index by topic</a> below,
and my list of <a href="#patches">patches</a>.</em></p>
"""

PATCHES = """
<div class="article-topic"></div>
<h2 id="patches">Patches</h2>
<table>
  <thead>
    <tr>
      <th>Date</th>
      <th>Project</th>
      <th>Description</th>
      <th>Link(s)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>17/09/2025</td>
      <td>Buildroot</td>
      <td>Linux as TF-A BL33 on Qemu</td>
      <td><a href="https://lists.buildroot.org/pipermail/buildroot/2025-September/786597.html">Sub</a></td>
    </tr>
    <tr>
      <td>02/03/2026</td>
      <td></td>
      <td></td>
      <td><a href="https://lists.buildroot.org/pipermail/buildroot/2026-February/796037.html">Resp</a></td>
    </tr>
    <tr>
      <td>02/04/2026</td>
      <td></td>
      <td>v3</td>
      <td><a href="https://lists.buildroot.org/pipermail/buildroot/2026-February/796454.html">Sub</a></td>
    </tr>
    <tr>
      <td>02/05/2026</td>
      <td></td>
      <td></td>
      <td><a href="https://lists.buildroot.org/pipermail/buildroot/2026-February/796463.html">Resp</a></td>
    </tr>
    <tr>
      <td>02/05/2026</td>
      <td></td>
      <td>v4</td>
      <td><a href="https://lists.buildroot.org/pipermail/buildroot/2026-February/796518.html">Sub</a></td>
    </tr>
    <tr>
      <td>19/12/2024</td>
      <td>Buildroot</td>
      <td>STM32MP135 Without U-Boot</td>
      <td><a href="https://lists.buildroot.org/pipermail/buildroot/2024-December/769250.html">Sub</a></td>
    </tr>
    <tr>
      <td>16/12/2025</td>
      <td></td>
      <td></td>
      <td><a href="https://lists.buildroot.org/pipermail/buildroot/2025-May/778563.html">Resp</a></td>
    </tr>
    <tr>
      <td>17/09/2025</td>
      <td></td>
      <td></td>
      <td><a href="https://lists.buildroot.org/pipermail/buildroot/2025-September/786595.html">Sub</a> <a href="https://lists.buildroot.org/pipermail/buildroot/2025-September/786596.html">Sub</a> <a href="https://lists.buildroot.org/pipermail/buildroot/2025-September/786597.html">Sub</a></td>
    </tr>
    <tr>
      <td>02/04/2026</td>
      <td></td>
      <td></td>
      <td><a href="https://gitlab.com/buildroot.org/buildroot/-/commit/8e4c663529d135088c78a9c7f4b59354f19d6580">Merge</a></td>
    </tr>
    <tr>
      <td>8/8/2025</td>
      <td>sc</td>
      <td>rename cmds: left -> mleft, right -> mright</td>
      <td><a href="https://github.com/n-t-roff/sc/commit/26b07f236d1b709c351981c5db5d12c54382bbc7">Sub</a></td>
    </tr>
    <tr>
      <td>8/8/2025</td>
      <td></td>
      <td></td>
      <td><a href="https://github.com/n-t-roff/sc/commit/ea7f88fa4256130ccb9ba572f05cfbd485d117b7">Merge</a></td>
    </tr>
    <tr>
      <td>6/29/2025</td>
      <td>sc</td>
      <td>repeat search in opposite direction</td>
      <td><a href="https://github.com/n-t-roff/sc/commit/08fe9431797bdfd43a8bf2a115b178e7ae898a5a">Sub</a></td>
    </tr>
    <tr>
      <td>6/29/2025</td>
      <td></td>
      <td></td>
      <td><a href="https://github.com/n-t-roff/sc/commit/54080300dab84a3b50fde797542845547a600634">Merge</a></td>
    </tr>
    <tr>
      <td>12/12/2024</td>
      <td>mc</td>
      <td>fix ETA calculation overflow</td>
      <td><a href="https://github.com/MidnightCommander/mc/issues/4613">Sub/Mege</a></td>
    </tr>
    <tr>
      <td>8/15/2024</td>
      <td>sc</td>
      <td>fix typos in man page</td>
      <td><a href="https://github.com/n-t-roff/sc/commit/3d15ac8fdcd19bf2d21b47603cafc2263387ed3c">Sub</a></td>
    </tr>
    <tr>
      <td>8/15/2024</td>
      <td></td>
      <td></td>
      <td><a href="https://github.com/n-t-roff/sc/commit/e029bc0fb5fa29da1fd23b04fa2a97039a96d2ba">Merge</a></td>
    </tr>
    <tr>
      <td>12/12/2024</td>
      <td></td>
      <td></td>
      <td><a href="https://github.com/n-t-roff/sc/commit/5c8bea4b625b84317aec1a927cdc7d1a2c1de502">Sub</a></td>
    </tr>
    <tr>
      <td>12/13/2026</td>
      <td></td>
      <td></td>
      <td><a href="https://github.com/n-t-roff/sc/commit/c11a548fcdaddcc5ef005fc409f9826feca28223">Merge</a></td>
    </tr>
  </tbody>
</table>
"""

HTML_OUTRO = """<footer class="license-footer">
<p>Content licensed under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
</p>
</footer>
</body>
</html>
"""

# ---------- YAML parsing helpers ----------

YAML_HEADER_RE = re.compile(r"^---\n(.*?)\n---", re.S)

def extract_yaml_header(text):
    match = YAML_HEADER_RE.match(text)
    if not match:
        return {}
    header = {}
    for line in match.group(1).splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        header[key.strip()] = value.strip()
    return header

def parse_date(datestr):
    try:
        return datetime.datetime.strptime(datestr, "%d %b %Y")
    except ValueError:
        sys.exit(f"Invalid date format: {datestr!r}")

# ---------- Data gathering ----------

def get_articles(folder):
    articles = []
    for path in Path(folder).glob("*.md"):
        text = path.read_text(encoding="utf-8")
        meta = extract_yaml_header(text)
        if not meta:
            continue
        meta["path"] = path
        meta["date_obj"] = parse_date(meta["date"])
        # Ensure topic exists
        if "topic" not in meta or not meta["topic"].strip():
            meta["topic"] = "Uncategorized"
        articles.append(meta)
    return articles

# ---------- Render chronological listing ----------

def render_chronological(articles):
    lines = ["<h2>Chronological listing</h2>",
             '<div class="chronology">']
    for a in sorted(articles, key=lambda x: x["date_obj"], reverse=True):
        fname = a["path"].with_suffix("").name
        lines.append(
            f'<div><span class="date">{a["date"]}</span> <a href="{fname}">{a["title"]}</a></div>'
        )
    lines.append("</div>")
    return "\n".join(lines)

# ---------- Render topical listing ----------

def build_topic_tree(articles):
    tree = {}
    for a in articles:
        parts = [p.strip() for p in a["topic"].split("/") if p.strip()]
        node = tree
        for part in parts:
            node = node.setdefault(part, {})
        node.setdefault("_articles", []).append(a)
    return tree

def render_topic_tree(tree, level=0):
    lines = ["<ul>"]
    for key, subtree in sorted(tree.items()):
        if key == "_articles":
            for a in sorted(subtree, key=lambda x: x["date_obj"], reverse=True):
                fname = a["path"].with_suffix("").name
                lines.append(
                    f'<li><a href="{fname}">{a["title"]}</a></li>'
                )
        else:
            lines.append(f"<li>{key}")
            lines.append(render_topic_tree(subtree, level + 1))
            lines.append("</li>")
    lines.append("</ul>")
    return "\n".join(lines)

def render_topical(articles):
    tree = build_topic_tree(articles)
    return '<div class="article-topic"></div><h2 id="topical">Topical listing</h2>\n' + render_topic_tree(tree)

# ---------- Main ----------

def main():
    articles = get_articles("articles")
    if not articles:
        sys.exit("No articles found.")
    outpath = Path("html/archive.html")
    with outpath.open("w", encoding="utf-8") as f:
        f.write(HTML_INTRO)
        f.write(render_chronological(articles))
        f.write("\n\n")
        f.write(render_topical(articles))
        f.write(PATCHES)
        f.write(HTML_OUTRO)

if __name__ == "__main__":
    main()
