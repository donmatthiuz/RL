# Guion de la presentación final de PolyRL

Ocho diapositivas, aproximadamente **11–13 minutos**. Las tres primeras conservan el contenido que ya estaba en `index.html`; las cinco restantes condensan la solución, la demostración, la comparación y la conclusión. La referencia visual es [Laboratorio nocturno](propuestas_estilo/02_laboratorio_nocturno/01_portada.png). El texto visible debe ser breve: las explicaciones de «Para contar» son para el equipo, no para proyectar.

**Hilo:** pregunta → mercado y costo → datos disponibles → simulación honesta → ver una trayectoria en la demo → agentes comparables → resultado en test → explicación económica.

## 1. PolyRL: del dato histórico a la decisión — 0:50

**En pantalla:** `PolyRL` · «Del dato histórico a la decisión» · aprendizaje por refuerzo en mercados binarios · datos históricos y saldo ficticio. Mantener la composición actual de la portada: título y equipo a la izquierda, campo de probabilidades animado a la derecha. Cambiar solo su paleta y tipografía para que dialogue con Laboratorio nocturno.

**Imagen:** [monograma de PolyRL](img/01_polyrl.svg), pequeño en el pie. El campo animado pertenece al HTML.

**Para contar:** «¿Puede un agente aprender cuándo operar y cuándo esperar?». Se estudian mercados horarios ya resueltos; no hubo operaciones reales ni dinero real. Al final responderemos la pregunta con el mismo criterio para todos los agentes.

**Apoyo:** hacer una pausa tras la pregunta. No adelantar el resultado.

## 2. Una pregunta binaria cada hora — 1:20

**En pantalla:** `YES / NO` · el token ganador paga `1`, el perdedor `0` · `WAIT`, `BUY_YES`, `BUY_NO`, `SELL`. La pregunta que queda abierta: «¿Cuánto cuesta comprar?». Esta es la segunda diapositiva ya existente en el HTML; añadir la evidencia del costo sin perder su eje de 0 a 1 ni las cuatro acciones.

**Imagen:** [costo de operar según el precio de entrada](img/02_costo_de_operar.png). Debe leerse como evidencia, con un borde oscuro y una leyenda legible.

**Para contar:** acertar el resultado no basta; el precio pagado y los costos determinan el beneficio. Comprar un lado casi seguro deja poco margen si ese precio ya se acerca a 1. WAIT es una decisión válida.

**Puente:** antes de entrenar, hay que saber qué precio conocía realmente el agente en cada minuto.

## 3. 12 294 mercados, tres cortes — 1:20

**En pantalla:** `8 682` entrenamiento · `1 861` validación · `1 751` test; corte cronológico `70/15/15`. Esta es la tercera diapositiva ya existente en el HTML: conservar los conteos y la separación temporal, y añadir el desfase como hallazgo del análisis.

**Imagen:** [desfase entre el precio de Polymarket y el spot de BTC](img/03_desfase_precio_spot.png). Un rótulo aclara que en entrenamiento el precio disponible tenía **52 s de antigüedad mediana**.

**Para contar:** los mercados de test quedaron al final y no se usaron para seleccionar modelos. El gráfico muestra que una aparente oportunidad puede provenir de comparar un precio de mercado atrasado con un BTC más reciente. No atribuimos al agente información que aún no existía.

**Puente:** el simulador debe decidir con lo conocido en ese instante y ejecutar después.

## 4. Decidir no es ejecutar — 1:40

**En pantalla:** `observar → decidir → precio posterior` y `WAIT · BUY_YES · BUY_NO · SELL`. Un marcador `t + 2 s` separa decisión y ejecución. El texto visible se limita a esa secuencia y a la conclusión «la ventaja aparente desaparece con el precio ejecutable y los costos».

**Imágenes:** [bucle de decisión](img/04_bucle_decision_compacto.svg) como esquema compacto y [ventaja aparente con precio atrasado](img/04_ventaja_aparente.png) como evidencia principal. Las dos figuras deben tener espacio suficiente para leer sus rótulos.

**Para contar:** cada mercado tiene hasta 60 decisiones de un minuto y un monto de 20 USDC por compra. El estado incluye precio disponible, tiempo y cartera; el agente puede esperar. Una orden se simula con el primer precio disponible después de una latencia de dos segundos, además de spread y comisión. La ventaja observada al comprar al precio de `t` desaparece al respetar esa secuencia.

**Puente:** antes de comparar políticas, mostrar cómo se puede inspeccionar una decisión concreta.

## 5. Una decisión se puede inspeccionar — 0:45

**En pantalla:** `estado → acción → cartera` · [demo de PolyRL](https://polyrl-demo-248394644314.us-east1.run.app). El enlace debe quedar grande y clicable; un código QR permite abrirla desde el público. La diapositiva va **después del simulador y antes de los agentes** para mostrar un caso concreto antes de comparar resultados agregados.

**Imagen:** [QR de la demo](img/05_demo_qr.svg), codificado con el enlace exacto. Mantener alto contraste y una zona blanca alrededor para facilitar el escaneo.

**Para contar:** abrir una trayectoria histórica en la demo y señalar qué información estaba disponible, qué hizo el agente y cómo cambió la cartera. El saldo es ficticio. La demo permite inspeccionar un ejemplo; la evaluación de rendimiento viene después.

**Puente:** ahora que se ha visto una trayectoria, comparar los cuatro agentes bajo la misma prueba.

## 6. Cuatro agentes, una misma prueba — 1:30

**En pantalla:** `PPO · DQN | CQL | BC` · cinco semillas por agente · mismos costos y mismo test · `NoTrade = WAIT siempre = retorno 0`. La cadena de verificación aparece como apoyo pequeño, no como lista de tecnologías para leer.

**Imágenes:** [familias de agentes](img/06_familias_agentes.svg) y [cadena de verificación](img/07_cadena_verificacion_compacta.svg). El primero explica las tres formas de aprendizaje; el segundo conecta validar, simular, entrenar, comprobar y mostrar.

**Para contar:** PPO y DQN interactúan con el simulador; CQL aprende de transiciones fijas y BC imita acciones observadas. Las configuraciones se eligieron en validación y el test se abrió una sola vez. NoTrade es la referencia retenida por la regla de validación: no es un modelo entrenado, sino abstenerse siempre.

**Puente:** la comparación principal pregunta si operar aportó algo frente a esa referencia de cero.

## 7. En test, nadie superó a NoTrade — 2:00

**En pantalla:** `0 / 4` superaron a NoTrade · `PPO y DQN: equivalentes` · `CQL: inferior` · mejora mínima relevante `+1 %` por mercado.

**Imagen:** [diferencias frente a NoTrade e intervalos ajustados](img/08_intervalos_test.png), figura completa del informe. La línea sólida marca cero; la discontinua, el umbral de +1 %. Azul es el modo normal y rojo el modo estricto. Una nota discreta indica «BC: 23 mercados informativos; intervalo poco confiable».

**Para contar:** en los 1 751 mercados de test, PPO y DQN obtuvieron diferencias pequeñas, compatibles con la equivalencia definida de antemano. CQL fue inferior. BC casi no operó y su intervalo exige cautela. «Equivalente» no significa que las políticas sean idénticas a NoTrade, sino que la diferencia quedó dentro del margen fijado. Los intervalos consideran días y semillas.

**Apoyo:** señalar primero cero, después los intervalos y finalmente el umbral de +1 %. Dejar una pausa antes de pasar a la explicación económica.

## 8. Acertar casi siempre aún puede perder — 1:50

**En pantalla:** `99,76 %` de lados acertados en compras de PPO a precio `0,98–1` · `−27,23 USDC` netos en esas 838 compras.

**Imagen:** [asimetría entre ganancias y pérdidas de PPO](img/09_asimetria_ppo.png). La ganancia media de una operación ganadora en ese tramo es `+0,02 USDC`; la pérdida media de una perdedora es `−2,14 USDC`.

**Para contar:** acertar el lado no garantiza rentabilidad cuando se compra cerca de 1: pocas pérdidas grandes anulan muchas ganancias pequeñas. Esta inspección posterior explica el resultado; no sustituye la prueba principal de la diapositiva 7. La conclusión se limita a estos datos, costos y condiciones de simulación.

**Cierre:** responder la pregunta inicial con precisión y abrir preguntas.

## Respuestas breves para preguntas

- **¿Qué es NoTrade?** Una política fija que siempre elige WAIT; no opera y su retorno es cero.
- **¿Por qué no basta el acierto?** La rentabilidad depende de cuánto se gana cuando se acierta, cuánto se pierde cuando se falla y cuánto cuesta ejecutar.
- **¿Qué significa equivalente?** La diferencia completa quedó dentro del margen predefinido de ±1 % del monto de referencia por mercado; no prueba igualdad exacta.
- **¿Qué es «lado acertado»?** Que el lado comprado ganó al resolver el mercado. «Mercado con ganancia» es otra métrica: exige PnL positivo después de costos.
- **¿Esto demuestra que ninguna estrategia funciona?** No. La conclusión se limita a las políticas, los datos y el protocolo de este experimento.

**Fuentes principales:** [informe final](../informe/Informe_final.md), [comparación en test](../../../reports/test/comparison.md) e [inspección de test](../../../reports/test/inspection.md).
