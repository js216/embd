ARTICLES_MARK := $(wildcard articles/*.md)
ARTICLES_HTML := $(patsubst articles/%.md,html/%.html,$(ARTICLES_MARK))

all: html/index.html html/style.css html/robots.txt html/favicon.ico \
	html/about.html html/archive.html

html/%.html: articles/%.md template.html md2html.pl | html
	perl md2html.pl $< template.html $@

html:
	mkdir html

clean:
	rm -rf html

# Special items

html/style.css: style.css
	cp $< $@

html/robots.txt: robots.txt
	cp $< $@

html/favicon.ico: favicon.ico
	cp $< $@

html/about.html: about.py
	python3 about.py > $@

html/index.html: $(ARTICLES_HTML) concat.py
	python3 concat.py

html/archive.html: $(ARTICLES_HTML) archive.py
	python3 archive.py
