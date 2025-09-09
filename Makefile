ARTICLES_MARK := $(wildcard articles/*.md)
ARTICLES_HTML := $(patsubst articles/%.md,html/%.html,$(ARTICLES_MARK))

all: html/index.html html/style.css html/robots.txt html/favicon.ico \
	html/about.html

html/index.html: $(ARTICLES_HTML) concat.py style.css
	python3 concat.py

html/%.html: articles/%.md template.html md2html.py
	python3 md2html.py $< template.html $@

clean:
	rm -f html/*

# Special items
#
html/style.css: style.css
	cp $< $@

html/robots.txt: robots.txt
	cp $< $@

html/favicon.ico: favicon.ico
	cp $< $@

html/about.html: about/about.html
	cp $< $@
