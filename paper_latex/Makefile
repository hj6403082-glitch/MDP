# Manuscript build. Usage: `make` (build), `make clean`, `make cleanall`.
MAIN = main
LATEXMK := $(shell command -v latexmk 2>/dev/null)

.PHONY: all clean cleanall

all:
ifeq ($(LATEXMK),)
	pdflatex -interaction=nonstopmode -halt-on-error $(MAIN).tex
	bibtex $(MAIN) || true
	pdflatex -interaction=nonstopmode -halt-on-error $(MAIN).tex
	pdflatex -interaction=nonstopmode -halt-on-error $(MAIN).tex
else
	latexmk -pdf -bibtex -interaction=nonstopmode -halt-on-error $(MAIN).tex
endif

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out \
	      $(MAIN).fls $(MAIN).fdb_latexmk $(MAIN).toc sections/*.aux

cleanall: clean
	rm -f $(MAIN).pdf
