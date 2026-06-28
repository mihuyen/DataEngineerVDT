TEX := stock_lakehouse_ieee

.PHONY: all clean

all:
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -pdf -interaction=nonstopmode -halt-on-error $(TEX).tex; \
	elif command -v tectonic >/dev/null 2>&1; then \
		tectonic --keep-logs $(TEX).tex; \
	else \
		echo "Missing LaTeX engine: install latexmk or tectonic"; exit 1; \
	fi

clean:
	@rm -f $(TEX).aux $(TEX).bbl $(TEX).blg $(TEX).log \
		$(TEX).out $(TEX).pdf $(TEX).synctex.gz
