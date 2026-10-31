# Investigación: comisión taker de Polymarket para el simulador (ENV-03)

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
(pendiente)
```

## Cómo se usa

Con la respuesta se cierran los tests de ENV-03: los ejemplos oficiales del punto 4 pasan a ser
casos de test de `taker_fee`, y los puntos 2, 3 y 6 fijan el redondeo, la moneda y los límites de
precio en `src/polym4v/env/execution.py`. Si algo contradice S5 o el ADR-009, se anota aquí y se
revisa antes de mezclar el PR de ENV-03.
