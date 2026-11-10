# Guion del video final

Video de la entrega final de PolyRL (DOC-11). Muestra la solución funcionando, cómo está
implementada y los hallazgos principales, en 3 a 4 minutos. El enlace se completa al final.

## 1. Requisitos y duración objetivo

- **Duración objetivo:** 3:40. Rango aceptable: 3:20 a 4:00. Si la toma se pasa de 4:00,
  recortar la escena de implementación, no la de resultados.
- **Formato:** MP4, H.264, 1920 x 1080, 30 fps, audio de 48 kHz.
- **Tono:** explicación tranquila, en español neutro; no es un anuncio ni una clase completa.
- **Voz:** una sola persona. Se puede grabar la voz aparte y montarla sobre la pantalla.
- **Apoyo visual:** la demo publicada es el centro. Las slides 7 y 8 aparecen solo unos segundos.
- **Requisito del curso:** que se vea la solución funcionando, la implementación y los hallazgos.
- **Límite:** no hay que repetir la presentación de clase; el video tiene otro orden y otro ritmo.

## 2. Las tres preguntas que responde el video

- **¿Qué hace el sistema?** Decide cada minuto si compra YES, compra NO, vende o espera en
  mercados horarios de Bitcoin, y se evalúa contra no operar en mercados que no vio.
- **¿Cómo está hecho?** Es un paquete de Python con datos, variables, entorno, agentes y
  evaluación; un pipeline arma episodios de 60 pasos y una demo reproduce trayectorias ya
  calculadas.
- **¿Qué encontramos?** Ningún agente cumplió el criterio de superioridad frente a no operar:
  PPO quedó equivalente, CQL inferior y DQN dependió del modo de ejecución; además, en el tramo
  de precios 0,98–1, acertar el lado no bastó para ganar.

## 3. Escenas

| Tiempo | Qué se ve en pantalla | Qué se dice | Fuente de la cifra |
| --- | --- | --- | --- |
| 0:00–0:30 | Demo publicada, página **Inicio**. Cursor sobre el título y las tarjetas de contexto. | «¿Puede un agente decidir mejor que no hacer nada? Este es PolyRL. Cada hora, Polymarket abre un mercado que pregunta si Bitcoin va a cerrar arriba o abajo de su apertura. El sistema decide, minuto a minuto, si compra YES, compra NO, vende o espera. No usa dinero real: trabaja sobre mercados históricos y un saldo ficticio, y se evalúa en mercados que no vio al entrenar.» | Sin cifras de resultados. |
| 0:30–1:10 | Demo, página **Simulación**. Mercado del 13/08/2026, 12:00 UTC, política PPO y semilla 0. Reproducir en velocidad Rápida o saltar al minuto 50; señalar el precio de YES, la posición y la cartera plana. | «Abro una hora concreta: el 13 de agosto de 2026, a las 12:00 UTC, con PPO y la semilla 0. La demo reproduce una trayectoria grabada. En esta hora se ve que el agente espera casi todo el tiempo. Cerca del final compra YES, cuando el precio ya está muy cerca de uno. Al cierre acierta el lado, pero la hora termina casi en cero: el margen era mínimo.» | Demo publicada: identificadores del mercado y de la política. Sin cifras de resultados. |
| 1:10–1:30 | Demo, página **Comparación**. Mantener visible la curva del mercado y el veredicto; no recorrer todas las pestañas. | «En la misma pantalla puedo comparar esa hora con no operar y con valor justo. Pero una hora no dice nada. La pregunta se responde en todo el conjunto de test, con el mismo protocolo para todos. Antes de mirarlo, veamos de dónde sale cada episodio.» | Sin cifras. |
| 1:30–2:00 | Terminal en la raíz: la línea `demo:` del `Makefile` y el árbol de `src/polym4v/` sin `__pycache__`. No ejecutar `make demo` en cámara: bloquea la terminal. | «Esa hora sale de un pipeline. Por dentro es el paquete `polym4v`: separa datos, variables, entorno, agentes y evaluación. El pipeline baja precios de Polymarket y velas de Binance, arma un episodio de 60 pasos por mercado y deja el test aparte. La demo no entrena: reproduce trayectorias ya calculadas.» | Sin cifras. |
| 2:00–2:50 | Slide 7, **Nadie superó a NoTrade**, señalando cero, los intervalos y el umbral. Si se preparó un rótulo aparte, mostrar la fórmula `D = media por mercado de (PnL del agente − PnL de NoTrade) / stake`; no está dentro de la slide. | «La evaluación final usó 1 751 mercados de test, en 76 días, con cinco semillas por agente. La métrica es el PnL por mercado frente a no operar, dividido por el monto de la apuesta. PPO, en modo normal, quedó en −0,0005, con un intervalo de confianza del 98,75 % entre −0,0029 y +0,0018: equivalente a no operar. Equivalente no significa idéntico: todo el intervalo quedó dentro del margen fijado antes de mirar test. Ningún agente llegó a +1 % del stake por mercado, es decir, 0,01 sobre el monto. CQL quedó inferior, DQN pasó a inconcluso con el criterio conservador y BC operó muy poco. El test se abrió una sola vez.» | `Informe_final.md`, secciones 6.1 y 6.3; `reports/test/comparison.csv`. |
| 2:50–3:20 | Slide 8, **Acertar casi siempre aún puede perder**, con el 99,76 % y el −27,23 USDC. Señalar primero el acierto y después el neto. | «Un hallazgo ilustra por qué acertar no basta. PPO compró 838 veces con el precio entre 0,98 y 1, sumando las cinco semillas. Acertó el lado el 99,76 % de las veces, pero solo el 97,37 % terminó con ganancia neta. Ese grupo perdió 27,23 USDC: la ganancia media fue 0,02 y la pérdida media, 2,14. Acertar el lado no es lo mismo que ganar.» | `reports/test/inspection_payoff.csv`, filas de PPO en el tramo 0,98–1, agregadas sobre cinco semillas. |
| 3:20–3:40 | Demo, página **Inicio**, o slide 1 como cierre. Cursor quieto; sin scroll. | «La respuesta, en estas condiciones, es que no se demostró que un agente supere a no operar. Quedó un pipeline reproducible y una evaluación honesta. El código y el informe están en el repositorio; la demo, en el enlace de la entrega. Gracias.» | `Informe_final.md`, sección 7. Sin cifras nuevas. |

Pausas: 2 segundos después de «casi en cero», después de «−27,23 USDC» y antes del cierre.

## 4. Qué tener abierto antes de grabar y cómo grabar

**Antes de grabar:**

- La demo publicada, ya cargada en **Inicio**:
  <https://polyrl-demo-248394644314.us-east1.run.app>. Abrirla al menos un minuto antes: Cloud Run
  puede arrancar en frío y la primera carga tarda.
- La página **Simulación** con el mercado del 13/08/2026, 12:00 UTC, PPO y semilla 0, y el minuto
  en 0. Probar una vez que la reproducción llega al cierre.
- La página **Comparación** con no operar y valor justo visibles.
- Las slides 7 y 8 abiertas en otra pestaña, o el PDF en esas páginas, para entrar y salir rápido.
- Si se va a usar el rótulo con la fórmula de la escena 5, tenerlo preparado aparte; no está en la
  slide.
- Una terminal en la raíz del repositorio, con la línea `demo:` del `Makefile` localizada y el
  árbol de `src/polym4v/` listo. No ejecutar `make demo` en cámara: el comando queda en primer
  plano y bloquea la terminal. La demo que se graba es la publicada.
- El guion impreso o en una segunda pantalla, no en la misma que se graba.

**Cómo grabar:**

- Resolución 1920 x 1080 y navegador al 100 % de zoom. Ocultar la barra de marcadores.
- Activar No molestar y cerrar notificaciones, correo y mensajería.
- Grabar en una sola toma por escena; si algo sale mal, repetir la escena completa.
- Mover el cursor despacio y señalar solo lo que se nombra. No hacer scroll mientras se habla.
- Grabar la voz con micrófono a unos 10 cm de la boca, sin aire acondicionado ni ventilador.
- Hacer una prueba de 10 segundos y escucharla antes de la toma buena.
- Revisar al final: duración entre 3 y 4 minutos, cifras correctas y ninguna frase prohibida.

## 5. Qué NO decir

- Nada de dinero real, inversión, recomendaciones financieras ni «esto sirve para operar».
- No decir que el agente «gana», «le gana al mercado» o «predice» el mercado. Decide y se mide.
- No decir que PPO es rentable: su media en test es ligeramente negativa.
- No decir «equivalente» como sinónimo de «igual»: es equivalencia dentro de un margen fijado.
- No decir que CQL «pierde siempre»: el resultado es inferior bajo este protocolo y estos datos.
- No decir que el test se evaluó varias veces o que se ajustó con test: se abrió una sola vez.
- No llamar «agente» a NoTrade: es una regla fija que siempre espera, no un modelo entrenado.
- No decir «12 294 mercados de test»: el test tiene 1 751; 12 294 es la suma de entrenamiento,
  validación y test.
- No generalizar el 99,76 %: es solo el tramo de compras de PPO entre 0,98 y 1.
- No afirmar que la prueba tenía potencia para detectar una mejora de 1 % en CQL y BC: su
  diferencia mínima detectable superaba ese umbral.
- No decir que se demostró que ninguna estrategia puede funcionar, ni generalizar fuera de estos
  datos, costos y condiciones de simulación.

## 6. Enlace al video

- **Enlace:** pendiente.
