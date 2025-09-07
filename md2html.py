#!/usr/bin/env python3
import sys
import markdown
from pathlib import Path
import re

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

# Convert Markdown to HTML with syntax highlighting and footnotes
html_body = markdown.markdown(
    md_body,
    extensions=[
        'codehilite',
        'fenced_code',
        'footnotes'
    ],
    extension_configs={
        'codehilite': {
            'guess_lang': False,
            'noclasses': False
        },
        'footnotes': {}
    }
)

# Read template
template = template_file.read_text(encoding="utf-8")

# Build the “published” line
if 'modified' in metadata:
    published_line = f'<p><em>Published {metadata.get("date")}, modified {metadata.get("modified")}. Written by {metadata.get("author")}.</em></p>'
else:
    published_line = f'<p><em>Published {metadata.get("date")}. Written by {metadata.get("author")}.</em></p>'

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
