# AGENTS.md

Guía para quien trabaje en este proyecto (personas o asistentes de IA): qué es, cómo está armado, qué reglas seguir y qué se ha cambiado.

---

## 1. Qué es

Sistema POS para el restaurante **Las Hamacas**. Django 5.2 + Django Channels (WebSockets), SQLite, HTML/CSS/JS a mano, sin frameworks de frontend. Corre en la red local del restaurante; los celulares entran por QR.

Tres roles (`core.models.User.Role`):

| Rol | Pantalla de inicio | Qué hace |
|---|---|---|
| `WAITER` (mesero) | `/pos/waiter/tables/` | Toma pedidos, cobra, libera mesas |
| `KITCHEN` (cocina) | `/pos/kitchen/kds/` | Ve comandas pendientes, marca Empezar / Listo |
| `ADMIN` | `/pos/admin/dashboard/` | Reportes, productos, usuarios, ajustes |

## 2. Mapa del código

```
config/                 settings, urls, asgi, routing (WebSockets reales)
core/models.py          User con campo role
pos/models.py           BusinessConfig, Zone, Table, MenuCategory, MenuItem, Order, OrderItem, OrderEvent
pos/views/
  waiter.py             mesas y pantalla de pedido
  kitchen.py            KDS + API de cocina
  api.py                crear/editar/anular/cobrar/cambiar estado/liberar
  admin_views.py        todas las pantallas de admin
  helpers.py            roles, periodos, broadcast por WebSocket
pos/consumers.py        KitchenConsumer, TablesConsumer, TableOrderConsumer
pos/templates/
  base.html             layout común (topbar + menú lateral en celular)
  admin_base.html       layout de admin (extiende base.html)
  partials/             admin_nav.html, period_filter.html
pos/static/pos/
  base.css              sistema visual + pantallas del mesero + login
  admin.css             componentes de admin
  kitchen.css           KDS
pos/templatetags/pos_extras.py   filtros get_item y cop
```

Nota: `pos/routing.py` es un duplicado sin uso; las rutas WebSocket reales están en `config/routing.py`.

## 3. Flujo de un pedido (IMPORTANTE)

```
NEW ──(cocina: Empezar)──> PREP ──(cocina: Listo)──> READY ──(mesero: Liberar mesa)──> DONE
  └────────────── mesero puede Anular (CANCELED) mientras no esté pagado ──────────────┘
```

- **Cobrar no libera la mesa.** `api_pay_order` marca `is_paid=True` y NO cambia el estado. Se puede cobrar en `NEW`, `PREP` o `READY`.
- **Liberar mesa** = `api_finish_order` → `DONE`. Requiere `READY` **y** pagado.
- Los estados **solo avanzan**. `api_change_order_status` rechaza volver atrás (ej. de `READY` a `PREP`).
- Un pedido pagado no se puede editar ni anular, pero cocina sí puede seguir cambiándole el estado.
- La cocina solo ve `NEW` y `PREP`, ordenados por `created_at` (orden de llegada). Al marcar Listo desaparece del tablero.
- Una mesa está ocupada mientras tenga un pedido `NEW`/`PREP`/`READY`.

Cada cambio llama a `helpers._ws_send_table_status(order)`, que avisa por WebSocket a tres grupos: `tables`, `table_<zona>_<mesa>` y `kitchen`. El payload incluye `status`, `is_paid`, `since`, `zone`, `table`.

## 4. Reglas de diseño: estilo "Comanda"

El usuario pidió explícitamente que **no parezca hecho por IA**. Mantener este lenguaje visual:

- Paleta en `:root` de `base.css`: `--paper`, `--sheet`, `--ink`, `--ink-2`, `--rule`, un solo acento `--tomato`, y colores de estado `--blue` (nuevo), `--mustard` (en cocina), `--green` (listo/pagado).
- Esquinas rectas (`--r: 3px`), bordes de tinta, **reglas punteadas** (`.hr`) y **doble línea** para totales, como un recibo.
- Etiquetas y cifras en monoespaciada (`.label`, `.kicker`, `.mono`, `.tag`). Texto en la fuente del sistema (no usar Inter: el archivo incluido solo trae un grosor).
- **Prohibido:** degradados, sombras suaves difusas, pills redondeadas en todo, emojis, íconos dentro de cuadritos de colores.
- Componentes reutilizables: `.btn` (`primary`, `ink`, `go`, `danger`, `ghost`, `small`, `lg`, `block`), `.input`, `.tag` (`new`, `prep`, `ready`, `paid`, `done`, `warn`), `.notice` (`ok`, `err`, `info`), `.leader` (título ····· número), `.panel`, `.dtable`, `.kpis`, `.chips`, `.seg`, `.switch`.
- Dinero siempre con el filtro `{{ valor|cop }}` → `$ 48.000` (en JS: `"$ " + Math.round(n).toLocaleString("es-CO")`).
- **Nada de `alert()`, `confirm()` ni `prompt()`.** Confirmaciones dentro de la pantalla: pasos en línea o botones de dos toques (`class="confirm-btn" data-confirm="¿Seguro?"`, manejado en `admin_base.html`).
- Todo debe funcionar en celular (los meseros usan el teléfono). El menú lateral aparece por debajo de 860px.
- Al cambiar un CSS, subir el `?v=` en el `<link>` (base.html/login.html para base.css, admin_base.html para admin.css, kitchen_kds.html para kitchen.css).

Páginas nuevas de admin: extender `admin_base.html`, usar `{% block content %}` y `{% block admin_js %}` (no `extra_js`).

## 5. Cómo probar

```bash
venv/Scripts/python.exe manage.py test pos core
venv/Scripts/python.exe manage.py runserver
```

- La impresora térmica (`win32print`) falla si no está conectada; el cobro igual se registra y la pantalla lo avisa.
- Los mensajes "Logging error ... '→'" en consola son de Windows (codificación de la consola), no fallas de las pruebas.
- Si abres el sistema en `127.0.0.1` en dos puertos a la vez, las sesiones chocan (las cookies no distinguen puerto). Usa `localhost` para uno de ellos.

## 6. Pendientes conocidos

- (Resuelto) `/pos/admin/accounts/` fallaba por falta de `admin_accounts.html`; ahora es la pantalla **Caja**.
- Borrar un usuario borra sus pedidos (`Order.waiter` usa `on_delete=CASCADE`). La pantalla de confirmación lo advierte; mejor desactivar usuarios.
- (Resuelto) Propinas: al cobrar, el mesero elige "Sin propina" o la propina configurada en Ajustes (por defecto: sin propina, porque es voluntaria). El cálculo en pantalla replica el de `api_pay_order` (valor fijo, o `floor(subtotal × % / 100)`).

---

## 7. Registro de cambios

### 2026-10-01 — Pantalla de Caja

- Nueva plantilla `admin_accounts.html` (**Caja**): cuadre de lo cobrado por método de pago (con los nombres de Ajustes), número de pedidos por método, total y botón imprimir. Usa el filtro de periodo común. Enlazada en `partials/admin_nav.html`.
- `test_admin_pages_render` ahora incluye `admin_accounts`.

### 2026-09-30 — Menú del mesero por categorías y fechas en celular

- **Mesero (`waiter_order.html`):** el menú abre mostrando solo las categorías en tarjetas grandes (nombre, número de productos, cuántos van en la comanda). Al tocar una se ven sus productos, con "← Categorías" para volver; el botón atrás del celular también vuelve a categorías (`history.pushState`). El buscador sigue buscando en todo el menú. Se quitaron las pestañas de categorías (`.cat-chip`) y las secciones (`.menu-section`).
- **Orden de categorías:** el mesero las ve en el orden de `MenuCategory.order`. En Admin › Productos › Categorías hay flechas ↑↓ (acción `move_category`); las nuevas quedan al final. Se dejó: Entradas, Platos Principales, Especiales del Día, Acompañamientos, Postres, Bebidas Frías, Bebidas Calientes.
- **Fechas en celular:** los campos de fecha del filtro de periodo se salían de su casilla (los celulares les dan un ancho mínimo propio). Ahora la cuadrícula usa `minmax(0, 1fr)` y bajo 380 px van una debajo de otra. Lo mismo para `.form-row`.
- Nueva prueba `test_categories_reorder_and_new_go_last`. Total: 48 pruebas.
- Versiones de CSS: base v28, admin v35.

### 2026-09-29 (noche) — Aprovechar mejor el espacio

Reporte del usuario: en el Resumen quedaba un hueco vertical entre "Ventas por día" y "Métodos de pago"; pidió optimizar el espacio en todas las pantallas.

- **Resumen:** la gráfica y "Últimos pedidos" compartían fila, así que la fila tomaba la altura de la lista (10 pedidos) y dejaba un hueco bajo la gráfica. Ahora son dos columnas independientes (`.dash-grid` > dos `.stack`): gráfica + métodos de pago a la izquierda, últimos pedidos + propinas a la derecha. **Regla:** paneles de alto variable en columnas independientes, no en filas compartidas.
- **Mesas:** las zonas se acomodan lado a lado (`.floor`, flex-wrap) en vez de una fila completa cada una; tarjetas de 3 por fila. Las 30 mesas caben en una pantalla.
- **Compactado general** (sin achicar botones táctiles ni letras): barra superior, títulos de página, separación entre paneles (20→14 px, 16→12 px), rellenos de paneles, tablas, filas de productos/usuarios, KPIs, gráfica (240→210 px), ticket del mesero, tarjetas de producto y tablero de cocina. Panel lateral de admin 300→280 px.
- Versiones de CSS: base v27, admin v34, kitchen v21.

### 2026-09-29 (tarde) — Gráfica de ventas en vivo

Reporte del usuario: la gráfica "Ventas por día" no reflejaba los $ 240.500 cobrados en el día.

- **Causa:** `admin_analytics` agrupaba por `o.created_at.date()`, que es la fecha en **UTC**. En Bogotá (UTC-5) todo pedido después de las 19:00 caía en "mañana" y se descartaba. Ahora usa `timezone.localtime(o.created_at).date()`. **Regla:** para agrupar por día usar siempre `timezone.localtime(...)`, nunca `.date()` directo sobre un datetime guardado.
- La gráfica ahora cuenta solo pedidos **cobrados**, igual que el KPI "Ventas cobradas" (antes sumaba también los sin cobrar).
- La API devuelve además `summary` (`paid_total`, `orders_count`, `avg_ticket`, `tips_total`, `by_method`). El Resumen actualiza en vivo cada 10 s la gráfica, los KPIs y los métodos de pago (elementos con `data-live`, `data-method`, `data-bar`).
- Si Chart.js no carga (sin internet, viene de un CDN), los números siguen actualizándose y la gráfica muestra un aviso.
- Nueva prueba `SalesAnalyticsTest` (pedido a las 22:30 hora local). Total: 44 pruebas.

### 2026-09-29 — Rediseño "Comanda" y mejoras por rol

Pedido del usuario: mejorar las vistas de los tres roles sin que parezcan hechas por IA, más una lista de mejoras concretas. Decisiones tomadas con el usuario: flujo **"cobrar y luego liberar"** y estilo **"Comanda"**.

**Mesero**
- `waiter_tables.html`: tarjetas de mesa por estado (libre punteada, nuevo, en cocina, listo), minutos ocupada, sello "PAGADA", botones arriba para filtrar por estado, actualización en vivo.
- `waiter_order.html` reescrito: categorías, buscador, productos en cuadrícula con cantidad pedida, pedido en forma de ticket con notas por producto, barra inferior "Ver comanda" en celular.
- Anular y cobrar ahora son pasos dentro del ticket (**sin ventanas emergentes**).
- Nuevo botón **Liberar mesa**, activo cuando el pedido está pagado y listo; al liberar vuelve a la lista de mesas.
- Aviso de cambios sin guardar; no deja cobrar con cambios pendientes.
- Corregido: el WebSocket apuntaba a `/ws/orders/...` en vez de `/ws/table/...` (el estado en vivo nunca funcionaba).
- Corregido: si la sesión expira, la API redirige al login y antes se tomaba como éxito.

**Cocina**
- `kitchen_kds.html` + `kitchen.css` reescritos: comandas en un riel, en orden de llegada (1°, 2°…), hora de llegada, minutos transcurridos (rojo desde 15 min), reloj y contadores.
- "Empezar" solo aparece en pedidos nuevos; en preparación solo queda "Listo".
- Los pedidos listos salen del tablero (API filtra `NEW`/`PREP`).
- Ahora recibe avisos en vivo (antes nadie enviaba al grupo `kitchen`; solo refrescaba cada 5 s).

**Admin**
- Nuevo `admin_base.html` + `partials/admin_nav.html`: navegación común con sección activa.
- Nuevo `partials/period_filter.html`: filtro de periodo (Hoy/Mes/Año/Rango) reutilizado.
- **Productos** (`admin_menu.html`): carta agrupada por categoría, buscador, filtro de agotados, interruptor Disponible/Agotado de un toque (acción `toggle_available`), edición en la misma fila, borrado múltiple con confirmación de dos toques, categorías con número de productos.
- **Usuarios** (`admin_users.html`): agrupados por rol con conteos, estado, último ingreso, creación en panel lateral.
- Rediseñados: Resumen, Pedidos (tabla), Detalle de pedido, Meseros, Detalle de mesero, QR (con botón imprimir), Ajustes, Editar/Eliminar usuario.
- Métodos de pago muestran los nombres personalizados de Ajustes.
- Corregido: el ticket promedio dividía lo cobrado entre todos los pedidos (ahora solo entre los cobrados).

**Backend**
- `api.py`: el cobro ya no pone `DONE`; no se puede cobrar un pedido `DONE`; el aviso por WebSocket se envía antes de imprimir (antes, si la impresora fallaba, las pantallas no se enteraban); estados solo avanzan; pedidos pagados pueden seguir en cocina; `api_active_table_order` devuelve `is_paid`, `payment_method`, `created_at`.
- `helpers.py`: el aviso incluye `is_paid` y `since`, y también va al grupo `kitchen`.
- `waiter.py`: la vista de mesas envía `is_paid` y `since` por mesa.
- `kitchen.py`: solo `NEW`/`PREP`, orden por llegada, incluye `created_at`.
- `admin_views.py`: `toggle_available`, productos ordenados para agrupar, conteos por categoría y por rol.
- `pos_extras.py`: filtro `cop`.

**Pruebas y documentación**
- `pos/tests.py`: +9 pruebas (`TableLifecycleTest`, `AdminMenuTest`): cobrar no libera, liberar requiere listo y pagado, cocina no retrocede, tablero sin listos y en orden de llegada, interruptor de disponibilidad, todas las páginas de admin cargan. Total en ese momento: 43 pruebas, todas pasan.
- `API_DOCUMENTATION.md` actualizado con el nuevo flujo.
- Verificado a mano en el navegador (computador y celular) con una copia de la base de datos.

Cambios previos del usuario que no se tocaron: `pos/admin.py` (comentarios quitados) y `requirements.txt` (`python-decouple`, `python-json-logger`).
