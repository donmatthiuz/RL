# Fuentes de la presentación

Originales WOFF2 de las tres familias que usa `index.html`. El deck las embebe en base64, así que
este directorio no se necesita para abrir la presentación; conserva los archivos para editar y
documenta su origen.

| Archivo | Familia | Origen | Licencia |
| --- | --- | --- | --- |
| `SpaceGrotesk.woff2` | Space Grotesk | `github.com/google/fonts`, carpeta `ofl/spacegrotesk` | SIL Open Font License 1.1 (`LICENSE-SpaceGrotesk.txt`) |
| `Inter.woff2` | Inter | `github.com/google/fonts`, carpeta `ofl/inter` | SIL Open Font License 1.1 (`LICENSE-Inter.txt`) |
| `JetBrainsMono.woff2` | JetBrains Mono | `github.com/google/fonts`, carpeta `ofl/jetbrainsmono` | SIL Open Font License 1.1 (`LICENSE-JetBrainsMono.txt`) |

- Los tres son los subconjuntos `latin` que sirve Google Fonts; incluyen los signos de puntuación
  del español que usa el deck.
- Son fuentes variables: el `@font-face` de `index.html` declara el rango de pesos que usa cada
  familia.
- No se descargan en tiempo de ejecución: el HTML no pide red al abrirse.
