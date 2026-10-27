#!/usr/bin/env bash
# Build the manuscript PDF. Prefers latexmk; falls back to pdflatex+bibtex.
# Usage: bash compile.sh   (run from the paper_latex/ directory)
set -euo pipefail
cd "$(dirname "$0")"

MAIN=main

if command -v latexmk >/dev/null 2>&1; then
    latexmk -pdf -bibtex -interaction=nonstopmode -halt-on-error "$MAIN.tex"
elif command -v pdflatex >/dev/null 2>&1; then
    pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex"
    bibtex "$MAIN" || true
    pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex"
    pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex"
else
    echo "ERROR: neither latexmk nor pdflatex found." >&2
    echo "Install TeX Live (sudo apt-get install texlive-full) or upload to Overleaf." >&2
    exit 1
fi

echo "Built $MAIN.pdf"
