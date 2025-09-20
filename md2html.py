#!/usr/bin/env python3
import sys
import re
from pathlib import Path
from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.anchors import anchors_plugin
import hashlib
from markdown_it.rules_block import StateBlock
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter


formatter = HtmlFormatter(cssclass="codehilite", nowrap=False)


def parse_args():
    if len(sys.argv) != 4:
        print("Usage: md2html.py input.md template.html output.html")
        sys.exit(1)
    return map(Path, sys.argv[1:])


def extract_metadata_and_body(md_text: str):
    """
    Extract YAML-style metadata (between ---) and the Markdown body.
    Supports simple key: value pairs, including multi-line values with '>' or '|'.
    """
    yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', md_text, re.DOTALL)
    if not yaml_match:
        return {}, md_text

    yaml_text, md_body = yaml_match.groups()
    metadata = {}
    key = None
    is_literal = False

    for line in yaml_text.splitlines():
        if not line.strip():
            continue
        if re.match(r'^\S+:', line):
            key, value = line.split(':', 1)
            key, value = key.strip(), value.strip()
            if value in ('>', '|'):
                metadata[key] = ""
                is_literal = (value == '|')
            else:
                metadata[key] = value
                is_literal = False
        elif key:
            if is_literal:
                metadata[key] += "\n" + line
            else:
                metadata[key] += " " + line.strip()

    for k, v in metadata.items():
        metadata[k] = re.sub(r'\s+', ' ', v.strip())

    return metadata, md_body


def pygments_highlight(code: str, lang: str, attrs: dict) -> str:
    """Highlight code using Pygments; fallback to plain text."""
    try:
        lexer = get_lexer_by_name(lang, stripall=True)
    except Exception:
        lexer = TextLexer(stripall=True)
    return highlight(code, lexer, formatter)


def convert_fenced_divs(md: MarkdownIt, md_text: str) -> str:
    """
    Convert ::: classname ... ::: into <div class="classname">...</div>.
    """
    pattern = re.compile(r':::\s*([a-zA-Z0-9_-]+)\s*\n(.*?)\n:::', re.DOTALL)

    def repl(match):
        class_name, inner_md = match.groups()
        inner_html = md.render(inner_md)
        return f'<div class="{class_name}">\n{inner_html}\n</div>'

    return pattern.sub(repl, md_text)


def build_published_line(metadata: dict) -> str:
    if 'modified' in metadata:
        return (
            f'<div class="article-meta">'
            f'Published {metadata.get("date")}, '
            f'modified {metadata.get("modified")}. '
            f'Written by {metadata.get("author")}.' 
            f'</div>'
        )
    return (
        f'<div class="article-meta">'
        f'Published {metadata.get("date")}. '
        f'Written by {metadata.get("author")}.' 
        f'</div>'
    )


def inject_metadata(template: str, metadata: dict) -> str:
    for key in ['title', 'author', 'date', 'description', 'topic']:
        template = template.replace(f"${key}$", metadata.get(key, ''))
    return template


def add_license_footer(template: str) -> str:
    license_footer = '''
<footer class="license-footer">
<p>Content licensed under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
</p>
</footer>
'''
    if '</body>' in template:
        return template.replace('</body>', f'{license_footer}\n</body>')
    return template + license_footer


def main():
    md_file, template_file, out_file = parse_args()

    md_text = md_file.read_text(encoding="utf-8")
    metadata, md_body = extract_metadata_and_body(md_text)

    md = MarkdownIt("commonmark", {"highlight": pygments_highlight, "typographer": True})
    md.enable(["replacements", "smartquotes"])
    md.use(footnote_plugin)
    md.use(anchors_plugin, min_level=1, max_level=3, permalink=False)
    md_body = convert_fenced_divs(md, md_body)
    html_body = md.render(md_body)

    # add hash prefix to footnote IDs and backrefs
    article_hash = hashlib.md5(md_text.encode("utf-8")).hexdigest()[:8]
    html_body = re.sub(r'\bid="fn(\d+)"', fr'id="{article_hash}-fn\1"', html_body)
    html_body = re.sub(r'\bid="fnref(\d+)"', fr'id="{article_hash}-fnref\1"', html_body)
    html_body = re.sub(r'href="#fn(\d+)"', fr'href="#{article_hash}-fn\1"', html_body)
    html_body = re.sub(r'href="#fnref(\d+)"', fr'href="#{article_hash}-fnref\1"', html_body)

    template = template_file.read_text(encoding="utf-8")
    template = template.replace('$published$', build_published_line(metadata))
    template = template.replace('$body$', html_body)
    template = inject_metadata(template, metadata)
    template = add_license_footer(template)

    out_file.write_text(template, encoding="utf-8")


if __name__ == "__main__":
    main()

