#!/usr/bin/env python3
import sys
import re
import markdown
from pathlib import Path


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
        if re.match(r'^\s*$', line):
            continue

        if re.match(r'^\S+:', line):  # new key: value
            key, value = line.split(':', 1)
            key, value = key.strip(), value.strip()
            if value in ('>', '|'):  # multi-line
                metadata[key] = ""
                is_literal = (value == '|')
            else:
                metadata[key] = value
                is_literal = False
        elif key:  # continuation line
            if is_literal:
                metadata[key] += "\n" + line
            else:
                metadata[key] += " " + line.strip()

    # Collapse whitespace for folded blocks
    for k, v in metadata.items():
        metadata[k] = re.sub(r'\s+', ' ', v.strip())

    return metadata, md_body


def convert_fenced_divs(md_text: str) -> str:
    """
    Convert ::: classname ... ::: into <div class="classname">...</div>.
    """
    pattern = re.compile(
        r':::\s*([a-zA-Z0-9_-]+)\s*\n(.*?)\n:::',
        re.DOTALL
    )

    def repl(match):
        class_name, inner_md = match.groups()
        inner_html = markdown.markdown(
            inner_md,
            extensions=['codehilite', 'fenced_code', 'footnotes'],
            extension_configs={'codehilite': {'guess_lang': False, 'noclasses': False}}
        )
        return f'<div class="{class_name}">\n{inner_html}\n</div>'

    return pattern.sub(repl, md_text)


def render_markdown(md_body: str) -> str:
    return markdown.markdown(
        md_body,
        extensions=['codehilite', 'fenced_code', 'footnotes'],
        extension_configs={'codehilite': {'guess_lang': False, 'noclasses': False}}
    )


def build_published_line(metadata: dict) -> str:
    if 'modified' in metadata:
        return (
            f'<div class="article-meta">'
            f'Published {metadata.get("date")}, '
            f'modified {metadata.get("modified")}. '
            f'Written by {metadata.get("author")}.'
            f'</div>'
        )
    else:
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
    else:
        return template + license_footer


def main():
    md_file, template_file, out_file = parse_args()

    md_text = md_file.read_text(encoding="utf-8")
    metadata, md_body = extract_metadata_and_body(md_text)

    md_body = convert_fenced_divs(md_body)
    html_body = render_markdown(md_body)

    template = template_file.read_text(encoding="utf-8")

    published_line = build_published_line(metadata)
    template = template.replace('$published$', published_line)
    template = template.replace('$body$', html_body)

    template = inject_metadata(template, metadata)
    template = add_license_footer(template)

    out_file.write_text(template, encoding="utf-8")


if __name__ == "__main__":
    main()
