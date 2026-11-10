# Slides de la presentación final

Requisitos en la sección 4 de [docs/10_entrega_final.md](../../../docs/10_entrega_final.md). El
sistema de diseño, el plan de las 10 slides, las fuentes de cada cifra y la compuerta de salida
están en [DESIGN.md](DESIGN.md).

## Entregables

| Archivo | Qué es | Estado |
| --- | --- | --- |
| [DESIGN.md](DESIGN.md) | Sistema de diseño, narrativa, fuentes y criterios de aceptación | Listo |
| `index.html` | Deck autocontenido, máximo 10 slides, con `?pdf` y `?guion` | En construcción: base, navegación, plantillas y slides 1 a 3 |
| `generar_pdf.sh` | Exporta los dos PDF con Chrome o Chromium sin interfaz | Pendiente |
| `PolyRL_presentacion.pdf` | Versión para Canvas, una slide por página | Pendiente |
| `PolyRL_guion.pdf` | Slide más notas del orador, para ensayar | Pendiente |
| `img/` | Originales editables de las capturas y figuras | Pendiente |
| `fonts/` | WOFF2 originales de Space Grotesk, Inter y JetBrains Mono con sus licencias | Listo |

## Controles del deck

- Flechas, espacio, `PageDown` y `Enter` avanzan; `PageUp`, `Backspace` y las flechas retroceden.
- `p` para pantalla completa y `o` para la vista general de las slides.
- `n` para las notas del orador y `r` para repetir la animación de la slide.
- `Home` y `End` van a la primera y a la última slide.
- Los enlaces `#N` abren la slide N; `#N-M` abre su paso M.
- Los modos `?pdf`, `?guion` y `?estatico` usan el mismo archivo.

## Estado

La base de `index.html` ya existe y se puede presentar con las tres primeras slides. El diseño
está cerrado; faltan las slides 4 a 10, la captura de la demo de la sección 9.10 del
[DESIGN.md](DESIGN.md), `generar_pdf.sh` y los dos PDF.

- Hecho: tokens de la sección 4, fuentes WOFF2 embebidas en base64, navegación, vista general,
  notas, `?pdf`, `?guion`, `?estatico`, las siete plantillas de la sección 5.2 y las slides 1 a 3.
- Pendiente: slides 4 a 10, captura real de la demo, script de exportación y revisión de la
  compuerta completa de la sección 11.2.

## Verificación de esta fase

- Chrome a 1920 $\times$ 1080, 1280 $\times$ 720 y 1024 $\times$ 768: sin desbordes de contenido;
  el lienzo se escala, queda centrado y la vista general pasa a dos columnas por debajo de 1156 px.
- `prefers-reduced-motion` deja visibles los controles y la ayuda, y desactiva animaciones y
  transiciones; `?estatico` y `?pdf` son los únicos modos que los ocultan para capturar.
- La vista general atrapa el foco con `Tab` y `Shift+Tab`, inertiza el fondo y devuelve el foco al
  botón de vista al cerrar. La barra de controles permanece visible mientras un botón tiene foco.
- Contraste AA en el texto normal y en las etiquetas; los ratios se calcularon sobre los tokens
  de la sección 4.1.
- `?pdf` y `?guion` generan tres páginas de prueba, una por slide, con tamaño 1600 $\times$ 900 px.
- El HTML no pide red al abrirse y pesa menos de 200 KB.
- Las capturas de verificación viven en el scratchpad, no en el repositorio.
