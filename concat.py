#!/usr/bin/env python3
import os
from bs4 import BeautifulSoup
from datetime import datetime

ARTICLES_DIR = "articles"
HTML_DIR = "html"
OUTPUT_FILE = os.path.join(HTML_DIR, "index.html")

HTML_TOP = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="author" content="Jakob Kastelic">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Articles on embedded Linux, STM32 development, low-level programming, and practical approaches to software productivity. Tutorials, experiments, and reflections on simplicity in computing." />
<link rel="license" href="https://creativecommons.org/licenses/by/4.0/" />
<title>embd.cc</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
"""

HTML_BOTTOM = """
</body>
</html>
"""

LICENSE_FOOTER = '''
<footer class="license-footer">
<p>Content licensed under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
</p>
</footer>
'''


def parse_date(date_str):
    for fmt in ("%d %b %Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None

def extract_body_and_date(file_path, link_href, keep_footer=False):
    """
    Extract body and date. Wrap each <h2> in a link to the original file.
    Strip <footer> unless keep_footer is True.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

        # Remove all footers unless we want to keep it
        if not keep_footer:
            for footer in soup.find_all("footer"):
                footer.decompose()

        # Extract date from meta tag
        meta_date_tag = soup.find("meta", attrs={"name": "date"})
        date = parse_date(meta_date_tag["content"]) if meta_date_tag else None

        # Wrap each <h2> in a link to the original html
        for h2 in soup.find_all("h2"):
            new_link = soup.new_tag("a", href=link_href)
            new_link.string = h2.get_text()
            h2.clear()
            h2.append(new_link)

        body_content = soup.body.decode_contents()
        return body_content, date


def main():
    md_files = {os.path.splitext(f)[0] for f in os.listdir(ARTICLES_DIR)
                if f.endswith(".md")}

    articles = []
    for stem in md_files:
        html_file = os.path.join(HTML_DIR, f"{stem}.html")
        if not os.path.isfile(html_file):
            continue
        body, date = extract_body_and_date(html_file, f"{stem}")
        if body:
            articles.append((body, date))

    # Sort by date, newest first
    articles.sort(key=lambda x: x[1] or datetime.min, reverse=True)

    concatenated_body = '\n<div class="article-sep"></div>\n'.join(body for body, _ in articles)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(HTML_TOP)
        f.write(concatenated_body)
        f.write(LICENSE_FOOTER)
        f.write(HTML_BOTTOM)

    print(f"Generated {OUTPUT_FILE} with {len(articles)} articles.")

if __name__ == "__main__":
    main()

