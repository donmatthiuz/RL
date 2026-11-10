#!/usr/bin/env bash
# Genera el PDF de las slides para Canvas: imprime index.html?pdf con Chrome o Chromium sin ventana.
# El modo ?pdf y el @page de 1600x900 de index.html dejan una diapositiva por página.
# Uso: ./generar_pdf.sh [salida.pdf]
set -euo pipefail

cd "$(dirname "$0")"
salida="$(realpath -m "${1:-presentacion.pdf}")"

for nombre in chromium chromium-browser google-chrome google-chrome-stable; do
    if command -v "$nombre" >/dev/null; then
        navegador=("$nombre")
        break
    fi
done
if [ -z "${navegador+x}" ]; then
    if command -v nix >/dev/null; then
        navegador=(nix shell nixpkgs#chromium -c chromium)
    else
        echo "Falta Chrome o Chromium en el PATH." >&2
        exit 1
    fi
fi

"${navegador[@]}" --headless=new --disable-gpu --no-sandbox --no-pdf-header-footer \
    --run-all-compositor-stages-before-draw --virtual-time-budget=8000 \
    --print-to-pdf="$salida" "file://$PWD/index.html?pdf" 2>/dev/null
echo "PDF generado: $salida"
