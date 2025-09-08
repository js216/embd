#!/usr/bin/env python3
import sys
import markdown
from pathlib import Path
import re

def convert_fenced_divs(md_text: str) -> str:
    """
    Convert ::: classname ... ::: into <div class="classname"> HTML </div>,
    converting the inner Markdown to HTML.
    """
    pattern = re.compile(
        r':::\s*([a-zA-Z0-9_-]+)\s*\n(.*?)\n:::',  # match ::: classname ... :::
        re.DOTALL
    )

    def repl(match):
        class_name = match.group(1)
        inner_md = match.group(2)
        inner_html = markdown.markdown(
            inner_md,
            extensions=[
                'codehilite',
                'fenced_code',
                'footnotes'
            ],
            extension_configs={
                'codehilite': {'guess_lang': False, 'noclasses': False},
                'footnotes': {}
            }
        )
        return f'<div class="{class_name}">\n{inner_html}\n</div>'

    return pattern.sub(repl, md_text)

if len(sys.argv) != 4:
    print("Usage: md2html.py input.md template.html output.html")
    sys.exit(1)

md_file, template_file, out_file = map(Path, sys.argv[1:])

# Read Markdown
md_text = md_file.read_text(encoding="utf-8")

# Extract YAML front matter
yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', md_text, re.DOTALL)
if yaml_match:
    yaml_text, md_body = yaml_match.groups()
    metadata = dict()
    for line in yaml_text.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip()] = value.strip()
else:
    md_body = md_text
    metadata = {}

# convert ::: blocks first
md_body = convert_fenced_divs(md_body)

# Convert Markdown to HTML with syntax highlighting and footnotes
html_body = markdown.markdown(
    md_body,
    extensions=[
        'codehilite',
        'fenced_code',
        'footnotes',
    ],
    extension_configs={
        'codehilite': {
            'guess_lang': False,
            'noclasses': False
        },
        'footnotes': {},
    }
)

# Read template
template = template_file.read_text(encoding="utf-8")

# Build the “published” line inside a metadata box
if 'modified' in metadata:
    published_line = (
        f'<div class="article-meta">'
        f'Published {metadata.get("date")}, modified {metadata.get("modified")}. '
        f'Written by {metadata.get("author")}.'
        f'</div>'
    )
else:
    published_line = (
        f'<div class="article-meta">'
        f'Published {metadata.get("date")}. Written by {metadata.get("author")}.'
        f'</div>'
    )

# Replace $published$ placeholder in template
template = template.replace('$published$', published_line)

# Replace placeholders
template = template.replace('$body$', html_body)
for key in ['title', 'author', 'date']:
    template = template.replace(f"${key}$", metadata.get(key, ''))

# Add license footer
license_footer = '''
<footer class="license-footer">
<p>Content licensed under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
</p>
</footer>
'''

# Insert before closing </body> if present, otherwise append
if '</body>' in template:
    template = template.replace('</body>', f'{license_footer}\n</body>')
else:
    template += license_footer

# Write output
out_file.write_text(template, encoding="utf-8")
