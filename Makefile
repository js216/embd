MD_FILES := $(wildcard articles/*.md)
HTML_FILES := $(patsubst articles/%.md,html/%.html,$(MD_FILES))

all: html/index.html html/style.css

html/index.html: $(HTML_FILES) concat.py style.css
	python3 concat.py

html/style.css: style.css
	cp $< $@

html/%.html: articles/%.md template.html
	pandoc $< -o $@ \
	  -f markdown -t html \
	  --standalone --template template.html \

clean:
	rm -f html/*
