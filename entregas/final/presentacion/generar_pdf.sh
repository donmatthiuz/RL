#!/usr/bin/env bash
# PDF de las slides para Canvas (DOC-10 y DOC-14): imprime index.html?pdf con Chrome sin interfaz.
# Uso: entregas/final/presentacion/generar_pdf.sh [salida.pdf]
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SALIDA="${1:-$DIR/PolyRL_presentacion.pdf}"
CHROME="${CHROME:-$(command -v google-chrome || command -v chromium || command -v chromium-browser)}"

"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer --virtual-time-budget=8000 \
    --print-to-pdf="$SALIDA" "file://$DIR/index.html?pdf" 2>/dev/null

if command -v pdfinfo > /dev/null; then
    pdfinfo "$SALIDA" | grep -E '^(Pages|Page size):'
fi
echo "PDF en $SALIDA"
