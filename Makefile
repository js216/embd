MD_FILES := $(wildcard articles/*.md)
HTML_FILES := $(patsubst articles/%.md,html/%.html,$(MD_FILES))

all: index.html

index.html: $(HTML_FILES) order.txt scripts/concat.py
	python3 scripts/concat.py order.txt html index.html

html/%.html: articles/%.md
	pandoc -f markdown -t html -o $@ $<

clean:
	rm -f html/*
	rm -f index.html
