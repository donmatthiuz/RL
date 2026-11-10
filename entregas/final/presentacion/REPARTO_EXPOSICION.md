# Reparto de la exposición

Este reparto sigue las ocho diapositivas del [guion](GUION_DIAPOSITIVAS.md) y las áreas de trabajo descritas en [roles](../../../docs/03_roles.md). Ese archivo todavía no identifica a José; este reparto incorpora la corrección del equipo. Es una guía de ideas y relevos: cada persona puede explicarlas con sus propias palabras, sin leer la pantalla.

Josué presentará la **diapositiva 5, la demo**. Por eso no se le asignan otras diapositivas en este reparto.

| Persona | Diapositivas | Tiempo aproximado | Parte del relato |
| --- | --- | --- | --- |
| **Mathew — datos** | 1, 2 y 3 | 3:30 | La pregunta, el mercado y los datos disponibles |
| **Gustavo — entorno y simulación** | 4 | 1:40 | Cómo se toma y ejecuta una decisión |
| **José — agentes** | 6 | 1:30 | Qué agentes se comparan y bajo qué condiciones |
| **Carlos — evaluación** | 7 y 8 | 3:50 | Qué ocurrió en test y por qué |

## Mathew — planteamiento y datos (diapositivas 1–3)

**1. PolyRL: del dato histórico a la decisión.** Presentar la pregunta que guía todo: «¿Puede un agente aprender cuándo operar y cuándo esperar?». Aclarar que se usaron mercados históricos y saldo ficticio. Presentar al equipo brevemente y prometer una respuesta basada en la misma prueba para todos.

**2. Una pregunta binaria cada hora.** Explicar qué significan YES y NO, y que el lado ganador paga 1 mientras el perdedor paga 0. Señalar las acciones posibles, incluida WAIT. Usar el gráfico para plantear el problema económico: acertar no basta si se paga demasiado o si los costos consumen el margen.

**3. 12 294 mercados, tres cortes.** Explicar el corte cronológico entre entrenamiento, validación y test, y por qué el test se reservó para el final. Señalar en el gráfico el desfase del precio disponible; la mediana de antigüedad en entrenamiento fue de 52 segundos. Cerrar con la idea de que el agente solo puede usar información conocida en cada instante.

**Relevo a Gustavo:** «Con esos datos, había que construir un entorno que respetara el tiempo real de cada decisión».

## Gustavo — simulación (diapositiva 4)

**4. Decidir no es ejecutar.** Recorrer el bucle observar → decidir → actualizar cartera. Explicar que la orden se simula con dos segundos de latencia y el primer precio posterior disponible, además de spread y comisión. Usar la figura de la ventaja aparente para mostrar por qué el precio del mismo instante daba una impresión engañosa. Recordar que esperar también es una acción.

**Relevo a Josué para la diapositiva 5:** «Ahora veamos una trayectoria concreta en la demo: qué observó el agente, qué eligió y qué pasó con la cartera».

## José — agentes (diapositiva 6)

**Entrada después de la demo:** «Ya vimos una decisión paso a paso. Ahora comparemos las distintas formas de aprender a tomarla».

**6. Cuatro agentes, una misma prueba.** Retomar la historia después de la demo. Identificar brevemente PPO y DQN como agentes que interactúan con el simulador, CQL como aprendizaje con transiciones fijas y BC como imitación. Destacar lo que hace justa la comparación: mismo entorno, costos y test; cinco semillas por agente. Explicar NoTrade como la referencia que siempre espera y obtiene retorno cero. La explicación de los algoritmos debe ser breve; aquí interesa preparar la lectura de resultados.

**Relevo a Carlos:** «Ya sabemos cómo se tomó cada decisión y bajo qué condiciones se evaluó. Veamos si operar mejoró la referencia».

## Carlos — resultados y cierre (diapositivas 7–8)

**7. En test, nadie superó a NoTrade.** Empezar por el resultado principal: 0 de 4 agentes alcanzaron la mejora exigida. Señalar en la gráfica la línea de cero, los intervalos y después el umbral de +1 %. Explicar que PPO y DQN quedaron equivalentes dentro del margen definido, CQL fue inferior y BC aporta evidencia limitada porque casi no operó. «Equivalente» no significa «idéntico».

**8. Acertar casi siempre aún puede perder.** Resolver la aparente contradicción: en las compras de PPO a precio 0,98–1 se acertó el lado el 99,76 % de las veces, pero esas 838 compras perdieron 27,23 USDC netos. Mostrar la asimetría del gráfico: una ganancia media de 0,02 USDC frente a una pérdida media de 2,14 USDC. Responder la pregunta inicial: en este experimento, las políticas evaluadas no demostraron una mejora económica frente a esperar. Aclarar que la conclusión se limita a estos datos y condiciones; abrir preguntas.

## Relevos y ritmo

El orden al hablar es **Mathew → Gustavo → Josué (demo) → José → Carlos**. La demo ocupa aproximadamente 0:45; con ella, el tiempo estimado de exposición es **11:15**, más preguntas. Dejar una pausa breve al cambiar de persona y evitar repetir lo que acaba de explicarse. Si la demo tarda en cargar, Josué puede señalar en la diapositiva el recorrido **estado → acción → cartera** y devolver la palabra a José sin romper el hilo.
