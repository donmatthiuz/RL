# Presentación final de PolyRL

La presentación tiene **8 diapositivas** y sigue la propuesta visual [Laboratorio nocturno](propuestas_estilo/02_laboratorio_nocturno/01_portada.png). El [guion](GUION_DIAPOSITIVAS.md) contiene el texto visible, las imágenes y las notas para hablar. Las tres primeras diapositivas del HTML original se conservaron: portada, mercado binario y cortes del dataset. La portada mantiene su composición y usa la nueva paleta. La demo aparece entre la explicación del simulador y la comparación de agentes.

## Archivos

- [index.html](index.html): presentación navegable en el navegador. Las fuentes están embebidas; las figuras se leen desde `img/`.
- [generar_pdf.sh](generar_pdf.sh) y [presentacion.pdf](presentacion.pdf): el PDF de las slides para Canvas, 8 páginas de 1600 × 900 px.
- [DESIGN.md](DESIGN.md): diseño de las slides 1 a 3 y la identidad de la demo de Streamlit.
- [REPARTO_EXPOSICION.md](REPARTO_EXPOSICION.md): quién explica cada diapositiva, las ideas clave y los relevos entre personas.
- [img/](img/): gráficos del informe, diagramas y marca utilizados por el guion.
- [fonts/](fonts/): archivos WOFF2 originales y licencias. JetBrains Mono se usa en títulos y datos; Inter, en explicación breve. Space Grotesk queda archivada como fuente anterior.
- [propuestas_estilo/02_laboratorio_nocturno/](propuestas_estilo/02_laboratorio_nocturno/): las dos imágenes que fijan la dirección visual.

## Uso

Abrir `index.html` en un navegador moderno. Flechas, espacio, `PageDown` o `Enter` avanzan; flecha izquierda, `PageUp` o `Backspace` retroceden. `o` abre la vista general, `n` las notas, `p` pantalla completa y `r` repite la animación. `?pdf` muestra las ocho diapositivas seguidas para imprimir; `?guion` añade las notas. `./generar_pdf.sh` imprime ese modo con Chrome o Chromium sin ventana y deja [presentacion.pdf](presentacion.pdf), el que se sube a Canvas. El enlace a la demo de la diapositiva 5 y su QR permiten abrirla durante la exposición.
