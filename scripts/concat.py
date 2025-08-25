#!/usr/bin/env python3
import os
import sys

# Usage: python concat.py order.txt html_dir output.html

if len(sys.argv) != 4:
    print(f"Usage: {sys.argv[0]} order_file html_dir output_file")
    sys.exit(1)

order_file, html_dir, output_file = sys.argv[1], sys.argv[2], sys.argv[3]

# Header and footer HTML you want to wrap around the content:
HTML_HEADER = """<!DOCTYPE html>
<!-- saved from url=(0020)https://www.embd.cc/ -->
<html lang="en"><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>Test</title>
<style>
   html {
      color-scheme: light dark;
   }
   body {
      max-width: 70ch;
      padding: 3em 1em;
      margin: auto;
      line-height: 1.5;
      font-size: 1.25em;
      font-family: sans-serif;
      color: light-dark(#222222, #efefec)
   }
</style>
</head>
<body>
"""

HTML_FOOTER = """
</body>
</html>
"""

# Read order file: just names like "my_article" (no path, no extension)
with open(order_file, 'r', encoding='utf-8') as f:
    names = [line.strip() for line in f if line.strip()]

# Build full paths to html files, adding .html if needed
html_paths = []
for name in names:
    base = os.path.splitext(name)[0]  # remove .md or .html if present
    path = os.path.join(html_dir, base + ".html")
    html_paths.append(path)

# Concatenate files
with open(output_file, 'w', encoding='utf-8') as out:
    out.write(HTML_HEADER)
    for path in html_paths:
        if not os.path.isfile(path):
            print(f"Warning: {path} not found, skipping.", file=sys.stderr)
            continue
        with open(path, 'r', encoding='utf-8') as f:
            out.write(f.read())
            out.write("\n")  # add a newline between articles
    out.write(HTML_FOOTER)

