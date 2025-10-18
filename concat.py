#!/usr/bin/env python3
import os
from bs4 import BeautifulSoup
from datetime import datetime

ARTICLES_DIR = "articles"
HTML_DIR = "html"
ARTICLES_PER_PAGE = 3

HTML_TOP = """<!DOCTYPE html>
<html lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="author" content="Jakob Kastelic">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Articles on embedded Linux, STM32 development, low-level programming, and practical approaches to software productivity. Tutorials, experiments, and reflections on simplicity in computing.">
<link rel="license" href="https://creativecommons.org/licenses/by/4.0/">
<link rel="stylesheet" href="style.css">
<link rel="icon" href="favicon.ico">
<title>embd.cc</title>
</head>
<body>
<header class="site-banner">
<div class="logo">
<a href="http://embd.cc"><img src="favicon.ico" alt="logo">embd.cc</a>
</div>
<nav class="site-nav">
<a href="archive">Archive</a>
<a href="about">About</a>
</nav>
</header>
"""

HTML_BOTTOM = """
<footer class="license-footer">
<p>Content licensed under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
</p>
</footer>
</body>
</html>
"""

def parse_date(date_str):
    for fmt in ("%d %b %Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None

def extract_body_and_date(file_path, link_href, keep_footer=False):
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

        if not keep_footer:
            for footer in soup.find_all("footer"):
                footer.decompose()

        meta_date_tag = soup.find("meta", attrs={"name": "date"})
        date = parse_date(meta_date_tag["content"]) if meta_date_tag else None

        for h2 in soup.find_all("h2"):
            new_link = soup.new_tag("a", href=link_href)
            new_link.string = h2.get_text()
            h2.clear()
            h2.append(new_link)

        body_content = soup.body.decode_contents()
        return body_content, date

def page_filename(page_index):
    """Return output filename for given page index (0-based)."""
    return "index.html" if page_index == 0 else f"page{page_index + 1}.html"

def make_nav_links(page_index, total_pages):
    """Return navigation HTML for 'Older' (left) and 'Newer' (right) links."""
    older_html = ""
    newer_html = ""

    if page_index < total_pages - 1:
        older_html = (
            f'<a class="older" href="{page_filename(page_index + 1)}">'
            '← Older articles</a>'
        )
    if page_index > 0:
        newer_html = (
            f'<a class="newer" href="{page_filename(page_index - 1)}">'
            'Newer articles →</a>'
        )

    if not (older_html or newer_html):
        return ""

    return f"""
    <div class="nav-links" style="display:flex; justify-content:space-between;">
        <div>{older_html}</div>
        <div>{newer_html}</div>
    </div>
    """

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

    articles.sort(key=lambda x: x[1] or datetime.min, reverse=True)
    total_articles = len(articles)
    total_pages = (total_articles + ARTICLES_PER_PAGE - 1) // ARTICLES_PER_PAGE

    for i in range(total_pages):
        start = i * ARTICLES_PER_PAGE
        end = start + ARTICLES_PER_PAGE
        page_articles = articles[start:end]

        concatenated_body = '\n<div class="article-sep"></div>\n'.join(
            body for body, _ in page_articles)

        nav_html = make_nav_links(i, total_pages)

        output_file = os.path.join(HTML_DIR, page_filename(i))
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(HTML_TOP)
            f.write(concatenated_body)
            f.write(nav_html)
            f.write(HTML_BOTTOM)

        print(f"Generated {output_file} with {len(page_articles)} articles.")

if __name__ == "__main__":
    main()

