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
<a href="http://embd.cc"><img src="favicon.ico">embd.cc : Archive</a>
</div>
<nav class="site-nav">
<a href="archive">Archive</a>
<a href="about">About</a>
</nav>
</header>
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
        # ✅ Ensure topic exists
        if "topic" not in meta or not meta["topic"].strip():
            meta["topic"] = "Uncategorized"
        articles.append(meta)
    return articles

# ---------- Render chronological listing ----------

def render_chronological(articles):
    lines = ['<div class="article-topic"></div>',
            "<h2>Chronological listing</h2>", "<ul>"]
    for a in sorted(articles, key=lambda x: x["date_obj"], reverse=True):
        fname = a["path"].with_suffix(".html").name
        lines.append(
        f'<li>{a["date"]}: <a href="/{fname}">{a["title"]}</a></li>'
    )
    lines.append("</ul>")
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
                fname = a["path"].with_suffix(".html").name
                lines.append(
                    f'<li><a href="/{fname}">{a["title"]}</a></li>'
                )
        else:
            lines.append(f"<li>{key}")
            lines.append(render_topic_tree(subtree, level + 1))
            lines.append("</li>")
    lines.append("</ul>")
    return "\n".join(lines)

def render_topical(articles):
    tree = build_topic_tree(articles)
    return '<div class="article-topic"></div><h2>Topical listing</h2>\n' + render_topic_tree(tree)

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
        f.write(HTML_OUTRO)

if __name__ == "__main__":
    main()
