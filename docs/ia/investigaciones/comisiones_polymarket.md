# Investigación: comisión taker de Polymarket (ENV-03)

Documentación oficial: [docs.polymarket.com](https://docs.polymarket.com).

## Por qué se investiga

ENV-03 implementa los costos del simulador según S5 y el ADR-009. La fórmula ya está fijada, pero
faltan detalles que cambian los números y los tests:

- Cómo se redondea la comisión y si el mínimo se aplica por orden o por cada ejecución.
- Si la comisión se paga en USDC o se descuenta de las acciones, al comprar y al vender.
- Los ejemplos oficiales, para usarlos como tests.
- El tick y los límites de precio, porque comprar a `p + medio spread` puede pasarse de 0,999.

## Lo que ya sabemos

- `markets.parquet` guarda dos esquemas, leídos del crudo de Gamma:
  - `crypto_fees_v2`: `rate = 0,07`, `exponent = 1`, `taker_only = true`, `rebate_rate = 0,2`. Lo tienen 2 292 mercados.
  - `crypto_fees`: `rate = 0,25`, `exponent = 2`, `taker_only = true`, `rebate_rate = 0,2`. Lo tienen 597 mercados.
  - Los otros 6 728 mercados no cobran comisión.
- El SDK `polymarket-client` 0.14.0 (`adjust_buy_amount_for_fees`) calcula la comisión de una
  compra como `(monto / precio) × rate × (precio × (1 - precio))^exponent` y la suma al monto: se
  paga en USDC aparte. No trae el caso de la venta ni el redondeo.
- `minimum_tick_size = 0,001` y `minimum_order_size = 5` en los mercados horarios revisados.
- S5 anotó "redondeada a 5 decimales, con un mínimo de 0,00001 USDC", pero sin la fuente exacta
  ni el modo de redondeo.

## Prompt para Perplexity

Copiar tal cual:

```text
Necesito información oficial y verificable sobre las comisiones (fees) de Polymarket para los
mercados cripto "Bitcoin Up or Down" horarios (serie btc-up-or-down-hourly), vigentes en 2026.
Prioriza la documentación oficial (docs.polymarket.com), el repositorio oficial de Polymarket en
GitHub (clientes CLOB, contratos CTF Exchange) y anuncios oficiales. Cita la URL de cada dato y
marca como "no confirmado" lo que no tenga fuente oficial.

Responde cada punto por separado:

1. Fórmula exacta de la comisión taker para los esquemas "crypto_fees_v2" (rate 0.07,
   exponent 1) y "crypto_fees" (rate 0.25, exponent 2). ¿Es
   fee = shares × rate × (p × (1 − p))^exponent? ¿Desde qué fecha se cobra en los mercados
   horarios de BTC y qué esquema aplica a cada periodo?
2. Redondeo: ¿a cuántos decimales se redondea la comisión y con qué modo (hacia arriba, hacia
   abajo, al más cercano)? ¿Existe una comisión mínima (por ejemplo 0.00001 USDC)? ¿Se calcula por
   orden o por cada ejecución (fill) cuando una orden cruza varios niveles del libro?
3. Moneda en que se cobra: en una COMPRA, ¿se paga en USDC aparte del monto o se descuentan
   acciones de las recibidas? En una VENTA, ¿se descuenta del USDC recibido o de las acciones?
4. Ejemplos numéricos oficiales (tabla de precio, acciones y comisión) copiados tal cual, con su
   URL.
5. ¿Los makers pagan comisión? ¿Qué significa "rebate_rate 0.2" y "taker_only true"?
6. Tick mínimo y límites de precio en estos mercados (¿0.001 a 0.999?) y tamaño mínimo de orden.
7. ¿Cobrar el pago de 1 USDC por acción ganadora al resolver (redeem) tiene comisión?
8. Cualquier cambio de las comisiones de mercados cripto anunciado entre 2025 y 2026, con fecha.
```

## Respuesta de Perplexity

Pegar aquí la respuesta completa, con sus enlaces:

```text
A continuación distingo claramente lo que está confirmado por documentación oficial de Polymarket de lo que **no está confirmado**. La fuente principal vigente es la página oficial de Trading Fees; el changelog oficial confirma la cronología de fees cripto en 2026. [docs.polymarket](https://docs.polymarket.com/trading/fees)

## 1. Fórmula y esquemas

**Sí, para el esquema vigente documentado la fórmula es equivalente a la que planteas:**

\[
\text{fee} = C \times \text{feeRate} \times p \times (1-p)
\]

donde \(C\) es el número de acciones operadas y \(p\) el precio por acción. Para Crypto, la documentación oficial indica `feeRate = 0.07`, maker fee `0` y rebate `20%`. [docs.polymarket](https://docs.polymarket.com/trading/fees)

Esto corresponde al esquema `crypto_fees_v2` con `rate = 0.07`, `exponent = 1`, `rebateRate = 0.2` y `takerOnly = true`, tal como aparece en la respuesta de la API reportada en un issue del repositorio oficial `Polymarket/rs-clob-client-v2`. [github](https://github.com/Polymarket/rs-clob-client-v2/issues/55)

- **`crypto_fees_v2` (rate 0.07, exponent 1):**
  \[
  \text{fee} = C \times 0.07 \times p \times (1-p)
  \]
  Es el esquema que la documentación pública actual documenta para la categoría Crypto. [docs.polymarket](https://docs.polymarket.com/trading/fees)

- **`crypto_fees` (rate 0.25, exponent 2):**
  **No confirmado** en la documentación oficial que pude verificar. No encontré en `docs.polymarket.com` una fórmula pública con `rate = 0.25` y `exponent = 2`, ni una tabla oficial que la documente. Por tanto, no debo afirmar su fórmula como oficial. Si ese esquema aparece en los metadatos de un mercado concreto, la interpretación natural sería \(C \times 0.25 \times [p(1-p)]^2\), pero eso es **inferencia, no confirmación oficial**.

**Fecha y esquema aplicable a BTC horario:** el changelog oficial dice que, desde el **6 de marzo de 2026**, los fees de taker y rebates de maker se extendieron a **todos los mercados cripto**, incluyendo 1H, 4H, diarios y semanales; solo los mercados nuevos creados a partir de esa fecha quedaron sujetos.  Por tanto, para un mercado **BTC Up or Down Hourly creado a partir del 6 de marzo de 2026**, aplica el esquema cripto vigente documentado: `crypto_fees_v2`, rate 0.07, exponent 1. [docs.polymarket](https://docs.polymarket.com/trading/fees)

Para mercados horarios creados **antes** del 6 de marzo de 2026, el changelog no afirma que la tarifa se aplicara retroactivamente; dice expresamente “Only new markets created after March 6 are affected”.  Si un mercado anterior muestra `crypto_fees` con 0.25/2, su tratamiento exacto es **no confirmado** con fuente oficial. [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md)

## 2. Redondeo, mínimo y base de cálculo

- **Precisión:** “Fees are rounded to 5 decimal places”. [docs.polymarket](https://docs.polymarket.com/trading/fees)
- **Mínimo:** la comisión mínima cobrada es **0.00001 USDC**; cualquier importe menor se redondea a cero. [docs.polymarket](https://docs.polymarket.com/trading/fees)
- **Modo de redondeo:** la documentación dice que se redondea a 5 decimales, pero **no especifica** si es hacia arriba, hacia abajo o al más cercano. **No confirmado.**
- **Por orden o por fill:** la documentación técnica oficial indica: “Fees are calculated per fill as `abs(Price * Quantity) * Rate`”.  Esto apunta a cálculo **por ejecución/fill**, no necesariamente agregado una sola vez por orden. Sin embargo, el modo exacto de redondeo cuando una orden cruza varios niveles —por fill y luego sumar, o agregar y redondear una vez— **no está confirmado** en la documentación pública; de hecho, hay un issue abierto en `Polymarket/py-sdk` solicitando precisamente esa aclaración. [docs.polymarket](https://docs.polymarket.com/llms-full.txt)

## 3. Moneda y forma de cobro

- La comisión se calcula y cobra en **USDC** según la página oficial de fees. [docs.polymarket](https://docs.polymarket.com/trading/fees)
- Se aplica “at match time” y el usuario no incluye información de fee al firmar la orden. [docs.polymarket](https://docs.polymarket.com/trading/fees)
- **Compra:** la documentación pública que verifiqué no especifica formalmente si el USDC de la comisión se cobra aparte o si se materializa recibiendo menos acciones. **No confirmado.**
- **Venta:** tampoco especifica formalmente si se descuenta del USDC recibido o de las acciones vendidas. **No confirmado.**
- La documentación de Polymarket US, jurisdicción distinta, sí dice que el fee de taker “is deducted from your balance at the time of the trade”, pero eso no debe extrapolarse automáticamente como regla de Polymarket global. [docs.polymarket](https://docs.polymarket.us/fees)

## 4. Ejemplos numéricos oficiales

La tabla oficial para **Crypto**, con 100 acciones, es la siguiente. La copio tal cual de la documentación: [docs.polymarket](https://docs.polymarket.com/trading/fees)

| Price | Trade Value | Taker Fee (USDC) |
|---:|---:|---:|
| $0.01 | $1 | $0.07 |
| $0.05 | $5 | $0.33 |
| $0.10 | $10 | $0.63 |
| $0.15 | $15 | $0.89 |
| $0.20 | $20 | $1.12 |
| $0.25 | $25 | $1.31 |
| $0.30 | $30 | $1.47 |
| $0.35 | $35 | $1.59 |
| $0.40 | $40 | $1.68 |
| $0.45 | $45 | $1.73 |
| $0.50 | $50 | $1.75 |
| $0.55 | $55 | $1.73 |
| $0.60 | $60 | $1.68 |
| $0.65 | $65 | $1.59 |
| $0.70 | $70 | $1.47 |
| $0.75 | $75 | $1.31 |
| $0.80 | $80 | $1.12 |
| $0.85 | $85 | $0.89 |
| $0.90 | $90 | $0.63 |
| $0.95 | $95 | $0.33 |
| $0.99 | $99 | $0.07 |

Fuente: [https://docs.polymarket.com/trading/fees](https://docs.polymarket.com/trading/fees) [docs.polymarket](https://docs.polymarket.com/trading/fees)

Estos valores corresponden a \(100 \times 0.07 \times p(1-p)\), con el máximo de $1.75 en \(p=0.50\). [docs.polymarket](https://docs.polymarket.com/trading/fees)

## 5. Makers, rebate y `taker_only`

- **Los makers no pagan comisión.** La documentación lo establece de forma explícita: “Makers are never charged fees. Only takers pay fees.” [docs.polymarket](https://docs.polymarket.com/trading/fees)
- **`rebate_rate = 0.2`** significa que el 20% de los fees de taker recolectados se redistribuye a makers mediante el Maker Rebates Program. Para Crypto, la tabla oficial muestra Maker Rebate = 20%. [docs.polymarket](https://docs.polymarket.com/trading/fees)
- El programa calcula un “fee equivalente” para cada orden de maker con la misma curva:
  \[
  \text{fee\_equivalent} = C \times \text{feeRate} \times p \times (1-p)
  \]
  y distribuye el pool proporcionalmente:
  \[
  \text{rebate} = \frac{\text{tu fee equivalente}}{\text{fee equivalente total}} \times \text{rebate pool}
  \]
 [docs.polymarket](https://docs.polymarket.com/programs/maker-rebates)
- **`taker_only = true`** significa que la comisión se cobra únicamente al lado taker; es coherente con “Makers are never charged fees”. [docs.polymarket](https://docs.polymarket.com/trading/fees)

## 6. Tick, límites de precio y tamaño mínimo

- **Límites de precio 0.001–0.999:** **No confirmado** para la serie `btc-up-or-down-hourly` con una fuente oficial específica. La documentación de Polymarket US usa \(p\) entre $0.01 y $0.99 para su fórmula, pero corresponde a Polymarket US y no prueba el rango exacto del mercado global horario. [docs.polymarket](https://docs.polymarket.us/fees)
- **Tick mínimo:** los endpoints oficiales exponen campos `tick_size` y `min_order_size` por mercado, pero el changelog no publica un valor universal para BTC horario.  Por tanto, el valor concreto —por ejemplo, 0.001— es **no confirmado** sin consultar los metadatos en vivo del mercado. [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md)
- **Tamaño mínimo de orden:** igualmente, `min_order_size` es un campo por mercado; no encontré un valor oficial publicado específicamente para `btc-up-or-down-hourly`. **No confirmado.**

La forma verificable de confirmar ambos valores es leer `tick_size` y `min_order_size` en los metadatos del token/mercado concreto mediante la API CLOB; el propio changelog oficial documenta que estos campos se añadieron a `get-book`/`get-books`. [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md)

## 7. Comisión al redeem

- Cada acción ganadora paga **$1** al resolver; así lo indican las páginas oficiales de los mercados BTC Up or Down Hourly. [polymarket](https://polymarket.us/event/btc-updown-1h-2026-10-30-0900z)
- La documentación oficial de fees declara que no hay fees de Polymarket para depositar o retirar USDC, pero **no encontré una afirmación explícita** de que el redeem/resolution esté libre de comisión. [docs.polymarket](https://docs.polymarket.com/trading/fees)
- Por tanto: **“el redeem no tiene comisión” es no confirmado como regla explícita**, aunque no encontré ninguna fuente oficial que cobre una comisión de redeem. El payout nominal de $1 por acción ganadora sí está confirmado. [polymarket](https://polymarket.us/event/btc-updown-1h-2026-10-30-0900z)

## 8. Cambios anunciados 2025–2026

Del changelog oficial de Polymarket: [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md)

| Fecha | Cambio |
|---|---|
| **5 de enero de 2026** | Se habilitan taker fees y maker rebates en mercados cripto de **15 minutos**; la curva alcanza 1.56% en 50%.  [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md) |
| **12 de febrero de 2026** | Lanzamiento de mercados cripto de **5 minutos** con taker fees habilitados y maker rebates; misma curva que 15 minutos.  [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md) |
| **1 de marzo de 2026** | Anuncio de extensión de taker fees y maker rebates a **todos los mercados cripto** —1H, 4H, diarios y semanales—.  [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md) |
| **6 de marzo de 2026** | Entrada en vigor: solo los mercados cripto **creados desde esa fecha** quedan sujetos a fees/rebates. Esto incluye los nuevos BTC Up or Down Hourly.  [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md) |
| **30 de marzo de 2026** | “Fee Structure V2”: nuevas categorías de fees, incluida Crypto, con tasas actualizadas; los mercados geopolíticos siguen sin fees.  [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md) |
| **31 de marzo de 2026** | La API indica que los fees deben calcularse con el objeto `feeSchedule` del mercado.  [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md) |
| **28 de abril de 2026** | CLOB V2 en producción: los fees se fijan en el matching, ya no mediante `feeRateBps` en la orden; pUSD reemplaza a USDC.e como colateral.  [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md) |
| **10 de julio de 2026** | Cambio de fee en **Sports**, no en Crypto: coefficient sube de 0.03 a 0.05 y rebate baja de 25% a 15%.  [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md) |

**No encontré en el changelog oficial un anuncio específico de cambio del fee cripto de 0.07 a otro valor, ni un anuncio formal del esquema legacy `crypto_fees` con rate 0.25 y exponent 2.** Ambos puntos quedan **no confirmados** con fuente oficial. [docs.polymarket](https://docs.polymarket.com/changelog/predictions.md)
```

## Evaluación de la respuesta

Evaluada el 31/10/2026 (R1). **Resultado: satisfactorio, con dos vacíos que cubrimos con
nuestros datos.** Se resume en el [historial de prompts](../historial_prompts.md) (P10).

| Punto | Qué confirma la respuesta | Qué cambia en ENV-03 |
| --- | --- | --- |
| Fórmula vigente | `acciones × 0,07 × p × (1 - p)`, con fuente oficial | Nada: ya era la fórmula |
| Ejemplos oficiales | Tabla de 100 acciones a 21 precios, mostrada en centavos | Pasan a ser tests |
| Redondeo | 5 decimales; el modo no está documentado | Se mantiene "mitad hacia arriba". La diferencia posible es de 0,000005 USDC por operación como mucho |
| Mínimo | 0,00001 USDC; lo que queda por debajo se redondea a cero | **Corrección:** el código subía esas comisiones al mínimo; ahora cobra cero |
| Por ejecución | La comisión se calcula por cada fill | Nada: el simulador ejecuta cada orden en un solo fill |
| Moneda | USDC. No confirma si en la compra se cobra aparte o en acciones | Se mantiene lo que hace el SDK oficial: suma la comisión al costo de la compra |
| Esquema `crypto_fees` | No lo confirma | Lo explicamos con el changelog y el crudo (abajo) |
| Tick y tamaño mínimo | No los confirma | Los confirma el crudo: tick de 0,001 en 12 447 de 12 471 mercados (0,01 en 24) y tamaño mínimo de 5 en todos |
| Pago al resolver | 1 USDC por acción ganadora; no dice explícitamente que no tenga comisión | Se mantiene sin comisión, como en `docs/08` |

**Lo que la respuesta no conectó.** Según el changelog citado, la curva de los mercados cripto de
15 minutos "alcanza 1,56 % en 50 %". Es exactamente `0,25 × (0,5 × 0,5)^2 = 0,015625`, el esquema
`crypto_fees` (rate 0,25, exponent 2). En nuestro crudo ese esquema aparece en mercados creados
entre el 04/03/2026 y el 03/04/2026, y `crypto_fees_v2` desde el 28/03/2026, en línea con la "Fee
Structure V2" del 30/03/2026. Los dos esquemas quedan explicados, y el ADR-009 sigue igual: el
simulador usa `crypto_fees_v2` para todos los mercados.

**Una inconsistencia a vigilar.** La respuesta también cita una frase técnica que calcula la
comisión como "abs(Price × Quantity) × Rate", que no coincide con la curva `p × (1 - p)`. La tabla
oficial sí coincide con la curva, así que se toma la curva. La frase probablemente es de otro
producto o de una versión anterior.

**¿Hace falta otra investigación?** No. Lo que queda sin confirmar (el modo de redondeo y la forma
del cobro en la compra) cambia como mucho fracciones de centavo por operación.

## Cómo se usa

Con la respuesta se cierran los tests de ENV-03: los ejemplos oficiales del punto 4 pasan a ser
casos de test de `taker_fee`, y los puntos 2, 3 y 6 fijan el redondeo, la moneda y los límites de
precio en `src/polym4v/env/execution.py`. Si algo contradice S5 o el ADR-009, se anota aquí y se
revisa antes de mezclar el PR de ENV-03.
