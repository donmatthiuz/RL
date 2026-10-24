# Conectar el proyecto con Polymarket

La integración está en `src/rl_polymarket` y usa `polymarket-client==0.14.0`,
el SDK oficial unificado de Python. La versión se fija porque las versiones
menores de la serie 0.x pueden introducir cambios incompatibles.

Permite consultar mercados, precios, punto medio, libros de órdenes e historial.
También permite conectar una cuenta existente y consultar sus órdenes abiertas.
Los comandos de este proyecto son de consulta; no incluyen envío ni cancelación
de órdenes.

## 1. Instalar

Desde la raíz del repositorio, con Python 3.11 o posterior:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -e ".[dev]"
```

En Windows PowerShell, activa el entorno con `venv\Scripts\Activate.ps1`.
Si solo necesitas la integración, puedes instalar con `python -m pip install -e .`.

Se instala el comando `rl-polymarket`. También puedes ejecutar
`python -m rl_polymarket` con los mismos argumentos.

## 2. Probar la conexión pública

Consultar datos públicos no requiere cuenta, API key ni clave privada:

```bash
rl-polymarket markets --limit 5
```

El comando devuelve JSON con `items`, `has_more`, `next_cursor`, `total_count`
y `limit_reached`. Los mercados incluyen `id`, `slug`, `question`, `version`,
`state` y `outcomes`, entre otros campos. `total_count` puede ser `null`.

Por defecto se consultan mercados con `closed=false`; esto no garantiza que
acepten órdenes. Revisa `state.active` y `state.accepting_orders` si necesitas
mercados negociables. Para consultar mercados cerrados, agrega `--closed`.

Si `has_more` es `true`, copia el valor de `next_cursor` completo y sin modificar:

```bash
rl-polymarket markets --limit 5 --cursor 'CURSOR_DE_LA_RESPUESTA'
```

Conserva los filtros de la consulta original al continuar. El cursor del SDK
incluye la información necesaria para reanudar la paginación, incluido el tamaño
de página. No se descargan automáticamente todas las páginas.

## 3. Consultar un mercado, precios e historial

Usa un `slug` obtenido de `items`. Debe ser el slug del mercado individual;
un evento de Polymarket puede agrupar varios mercados con slugs diferentes.

```bash
rl-polymarket market SLUG_DEL_MERCADO
```

Cada resultado (`outcomes.yes` u `outcomes.no`) tiene su propio identificador.
Para mercados `version="v1"`, utiliza `token_id`. Para `version="v2"`, utiliza
`position_id`. Ese valor es el `ASSET_ID` de los siguientes comandos; no uses
el `id`, el `condition_id` ni el slug del mercado en su lugar.

```bash
rl-polymarket book ASSET_ID
rl-polymarket price ASSET_ID --side BUY
rl-polymarket price ASSET_ID --side SELL
rl-polymarket midpoint ASSET_ID
rl-polymarket history ASSET_ID --interval 1d --bucket-seconds 3600 --limit 100
```

Los precios se devuelven como cadenas decimales en JSON para conservar su
precisión. En Python se usan objetos `Decimal`. El historial incluye observaciones
con `timestamp`, `price` y `resolution_seconds`; puede estar vacío si no hay datos.
Los timestamps se serializan en formato ISO 8601 con zona horaria.

El historial también devuelve una página y admite `--cursor`. `--limit` acepta
de 1 a 10000 observaciones; para mercados, el límite es de 1 a 100 elementos.
Los intervalos disponibles son `1h`, `6h`, `1d`, `1w`, `1m`, `all` y `max`.
`1m` representa un mes. `--bucket-seconds` indica la resolución solicitada:
debe estar entre 60 y 86400; el mínimo sube a 300 para `1w` y a 600 para
`1m`, `all` y `max`.

Puedes guardar resultados con la redirección del shell:

```bash
rl-polymarket history ASSET_ID --interval 1d > precios.json
```

## 4. Conectar una cuenta existente

Prepara tu cuenta en Polymarket y obtén la clave privada del firmante y la
dirección de la cuenta que controla. La dirección puede ser una EOA, una
cartera proxy/Safe o una Deposit Wallet; no siempre coincide con la dirección
del firmante. Consulta la guía oficial de
[carteras y autenticación](https://docs.polymarket.com/trading/wallets-auth).

```bash
cp .env.example .env
```

Completa `.env` localmente:

```dotenv
POLYMARKET_PRIVATE_KEY=0xTU_CLAVE_PRIVADA
POLYMARKET_WALLET_ADDRESS=0xDIRECCION_DE_TU_CUENTA

# Opcionales: configura las tres o deja las tres vacías.
POLYMARKET_API_KEY=
POLYMARKET_API_SECRET=
POLYMARKET_API_PASSPHRASE=
```

Los valores de ejemplo son marcadores, no credenciales válidas. La clave privada
real tiene 64 caracteres hexadecimales, normalmente precedidos por `0x`.
El SDK la utiliza para firmar la autenticación; no se envía como parámetro HTTP.
Nunca agregues el archivo `.env` al repositorio. `.gitignore` excluye `.env`
y sus variantes, y permite únicamente la plantilla `.env.example`.

Para este proyecto, tanto la clave privada como la dirección son obligatorias
en modo autenticado. El SDK detecta el tipo de cartera. Usa una cuenta ya
configurada: el SDK comprueba que la cartera esté lista y una Deposit Wallet
sin desplegar puede activar su flujo de creación, que necesita configuración
adicional del Relayer/Builder y queda fuera de esta integración.

Las tres variables `POLYMARKET_API_*` corresponden a credenciales CLOB de
usuario (L2), vinculadas al firmante. Si las omites, el SDK las deriva al
conectarse. Si ya las tienes, debes proporcionar las tres. No uses claves de
Builder o Relayer en estos campos. No es necesario copiar credenciales
generadas para realizar las consultas públicas.

Comprueba la conexión autenticada y consulta las órdenes existentes:

```bash
rl-polymarket account
rl-polymarket open-orders
```

`account` devuelve únicamente `wallet` y `wallet_type`. `open-orders` devuelve
una página de órdenes abiertas y acepta `--cursor` para continuar. Los secretos
no aparecen en la salida de estos comandos ni en los mensajes de error del CLI.

Las variables de entorno del proceso tienen prioridad sobre `.env`, incluso si
están vacías. La lectura no modifica `os.environ`. También puedes elegir un
archivo explícito; coloca la opción antes del subcomando:

```bash
rl-polymarket --env-file /ruta/a/mi-config.env account
```

## 5. Usar desde Python o un notebook

Después de instalar el paquete, puedes importarlo desde cualquier directorio:

```python
from rl_polymarket import PolymarketClient, get_asset_id

with PolymarketClient() as client:
    page = client.list_markets(limit=5)
    for market in page.items:
        print(market.slug, market.question)

    # Elegir un mercado que acepte órdenes antes de consultar su libro.
    tradable = next(
        (market for market in page.items if market.state.accepting_orders),
        None,
    )
    if tradable is not None:
        asset_id = get_asset_id(tradable, outcome="yes")
        price = client.get_price(asset_id, side="BUY")
        book = client.get_order_book(asset_id)
        history = client.get_price_history(asset_id, interval="1d")
        print(price, len(book.bids), len(history.items))

    if page.has_more and page.next_cursor:
        next_page = client.list_markets(limit=5, cursor=page.next_cursor)
```

La conexión autenticada se solicita explícitamente; tener claves en el entorno
no cambia el modo público por defecto:

```python
from rl_polymarket import PolymarketClient, PolymarketSettings

settings = PolymarketSettings.from_env(".env")
with PolymarketClient(settings, authenticated=True) as client:
    print(client.get_account())
    orders = client.list_open_orders()
    for order in orders.items:
        print(order.id)
```

Usa `with` para liberar las conexiones HTTP. Si creas el cliente manualmente,
llama a `client.close()` cuando termines. Las listas devuelven `Page` del SDK;
los mercados y libros son modelos tipados del SDK.

## 6. Endpoints y errores

El SDK configura los servicios de producción; no es necesario modificar URLs:

| Servicio | URL base | Uso en el proyecto |
| --- | --- | --- |
| Gamma | `https://gamma-api.polymarket.com` | Descubrimiento y detalle de mercados |
| CLOB | `https://clob.polymarket.com` | Precios, libros y órdenes de cuenta |
| Data API | `https://data-api.polymarket.com` | Historial de precios en `/v2/prices-history` |

El SDK gestiona las solicitudes HTTP y sus tiempos de espera. El CLI devuelve
código 0 al completar la consulta, 1 ante errores de conexión/configuración
y 2 ante argumentos de línea de comandos inválidos. Los errores se escriben
en `stderr` y los datos JSON en `stdout`.

| Situación | Qué revisar |
| --- | --- |
| Falta una variable | Completar `.env` o exportar la variable; las tres credenciales L2 deben estar juntas |
| `UserInputError` | Formato de clave/dirección, identificador del resultado, cursor o parámetros del historial |
| HTTP 401/403 | Credenciales del firmante, dirección de cuenta, acceso autorizado y disponibilidad del servicio |
| HTTP 404 | Slug del mercado o identificador del resultado; el mercado puede no tener libro disponible |
| `RateLimitError` | Esperar antes de reintentar y reducir la frecuencia de consultas |
| `TransportError` | Conectividad, DNS, proxy o disponibilidad de Polymarket |
| `UnexpectedResponseError` | Respuesta incompatible o inesperada; comprobar el SDK y la documentación oficial |

Desde Python, las excepciones del SDK heredan de `polymarket.PolymarketError`.
Puedes capturarlas según el caso. `RateLimitError.retry_after`, cuando está
presente, indica cuánto esperar antes de reintentar.

## 7. Ejecutar las pruebas

```bash
python -m pytest
```

Las pruebas simulan HTTP y la conexión de cuenta: no necesitan red, fondos
ni credenciales reales. La autenticación con tu cuenta se verifica mediante
`rl-polymarket account` una vez configurado `.env`.

## Referencias oficiales

- [SDK de Python](https://docs.polymarket.com/getting-started/python)
- [Repositorio del SDK unificado](https://github.com/Polymarket/py-sdk)
- [Descubrir mercados](https://docs.polymarket.com/market-data/discover-markets)
- [Precios, libros e historial](https://docs.polymarket.com/market-data/prices-order-books)
- [Carteras y autenticación](https://docs.polymarket.com/trading/wallets-auth)
- [Migración desde los clientes anteriores](https://docs.polymarket.com/migrate/clob-sdk-to-unified-sdk)

No instales `py-clob-client` para esta integración: su repositorio fue archivado
y Polymarket indica que el cliente anterior ya no funciona.
