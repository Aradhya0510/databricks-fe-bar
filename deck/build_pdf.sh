#!/usr/bin/env bash
# Markdown deck -> landscape slide PDF (pandoc + headless Chrome). One slide per "# " heading.
set -euo pipefail
cd "$(dirname "$0")"
pandoc osa_deck.md -s --metadata pagetitle="OSA Command Center" -c slides.css --section-divs -o osa_deck.html
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf="$PWD/osa_deck.pdf" "file://$PWD/osa_deck.html" 2>/dev/null
echo "wrote deck/osa_deck.pdf"
