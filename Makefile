ARTICLES_MARK := $(wildcard articles/*.md)
ARTICLES_BOXS := $(wildcard articles/*.html)
ARTICLES_HTML := $(patsubst articles/%.md,html/%.html,$(ARTICLES_MARK))

all: html/index.html html/style.css html/robots.txt html/favicon.ico \
	html/projects.html html/about.html html/archive.html

html/%.html: articles/%.md template.html md2html.pl $(ARTICLES_BOXS) | html
	perl md2html.pl $< template.html > $@

html:
	mkdir html

clean:
	rm -rf html

# Special items

html/%: %
	cp $< $@

html/index.html: $(ARTICLES_HTML) concat.py
	python3 concat.py

html/archive.html: $(ARTICLES_HTML) archive.py
	python3 archive.py
