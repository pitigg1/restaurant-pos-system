# POS System - API Documentation

This document describes every JSON API endpoint exposed by the POS system.

## Table of Contents

- [Authentication](#authentication)
- [Menu](#menu)
- [Orders](#orders)
- [Kitchen](#kitchen)
- [Payments](#payments)
- [Admin](#admin)
- [HTTP Status Codes](#http-status-codes)
- [Usage Examples](#usage-examples)
- [WebSockets](#websockets)
- [Additional Notes](#additional-notes)

---

## Authentication

Every endpoint below requires an authenticated session. Authentication is handled through Django's session framework, not tokens.

### Login
```
POST /pos/login/
```

**Body (form-data):**
```
username: string (required)
password: string (required)
```

**Response:**
```
302 redirect to /pos/
```

### Logout
```
GET /pos/logout/
```

**Response:**
```
302 redirect to /pos/login/
```

---

## Menu

### Get the full menu

Returns every menu item currently marked as available.

```
GET /pos/api/menu/
```

**Permissions:** any authenticated user

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "Hamburguesa Clásica",
    "price": "18000.00",
    "category": "Platos Principales",
    "category_id": 4
  },
  {
    "id": 2,
    "name": "Coca Cola",
    "price": "5000.00",
    "category": "Bebidas Frías",
    "category_id": 1
  }
]
```

**Fields:**
- `id` (integer): item id
- `name` (string): item name
- `price` (string): decimal price
- `category` (string|null): category name
- `category_id` (integer|null): category id

---

## Orders

### Get a table's active order

Returns the active order (not canceled or finished) for a given table, if any.

```
GET /pos/api/orders/active/<zone>/<table>/
```

**URL parameters:**
- `zone` (string): zone slug (e.g. `"kiosco"`)
- `table` (integer): table number

**Permissions:** any authenticated user

**Response (200) - order found:**
```json
{
  "order": {
    "id": 123,
    "zone": "Kiosco",
    "table_number": 5,
    "status": "NEW",
    "items": [
      {
        "menu_item_id": 1,
        "name": "Hamburguesa Clásica",
        "price": "18000.00",
        "quantity": 2,
        "notes": "Sin cebolla"
      }
    ]
  }
}
```

**Response (200) - no active order:**
```json
{
  "order": null
}
```

**Order fields:**
- `id` (integer)
- `zone` (string): zone name
- `table_number` (integer)
- `status` (string): `NEW`, `PREP`, `READY`, `DONE`, or `CANCELED`
- `items` (array)

**Item fields:**
- `menu_item_id` (integer)
- `name` (string)
- `price` (string)
- `quantity` (integer)
- `notes` (string)

---

### Create an order

```
POST /pos/api/orders/create/
```

**Permissions:** `WAITER` or `ADMIN`

**Body (JSON):**
```json
{
  "zone": "kiosco",
  "table_number": 5,
  "items": [
    { "menu_item_id": 1, "quantity": 2, "notes": "Sin cebolla" },
    { "menu_item_id": 3, "quantity": 1, "notes": "" }
  ]
}
```

**Validation:**
- `zone`: required, must exist and be active
- `table_number`: required, must be > 0, must exist within the zone
- `items`: required, at least one item
- `items[].menu_item_id`: required, must exist and be available
- `items[].quantity`: required, 1-100
- `items[].notes`: optional, max 500 characters

**Response (200):**
```json
{
  "ok": true,
  "order_id": 123
}
```

**Typical errors (400):**
```json
{ "detail": "Zona es requerida" }
```
```json
{ "detail": "Mesa 5 no existe en zona 'Kiosco' o está inactiva" }
```
```json
{ "detail": "Item 1: el producto no existe o no está disponible" }
```

---

### Edit an order

Replaces all of an order's items with a new list.

```
POST /pos/api/orders/<order_id>/edit/
```

**URL parameters:**
- `order_id` (integer)

**Permissions:** `WAITER` or `ADMIN`

**Restrictions:**
- Cannot edit a canceled order
- Cannot edit a finished order (`DONE`)
- Cannot edit an order that's already been paid

**Body (JSON):**
```json
{
  "items": [
    { "menu_item_id": 1, "quantity": 3, "notes": "Término medio" }
  ]
}
```

**Validation:** same as order creation.

**Response (200):**
```json
{ "ok": true }
```

**Error example (400):**
```json
{ "detail": "No se puede editar un pedido cancelado" }
```

---

### Cancel an order

```
POST /pos/api/orders/<order_id>/cancel/
```

**URL parameters:**
- `order_id` (integer)

**Permissions:** `WAITER` or `ADMIN`

**Restrictions:**
- Cannot cancel an already canceled order
- Cannot cancel a finished order (`DONE`)
- Cannot cancel an order that's already been paid

**Body (JSON):**
```json
{ "reason": "Cliente cambió de opinión" }
```

**Fields:**
- `reason` (string, optional): cancellation reason, max 500 characters

**Response (200):**
```json
{
  "ok": true,
  "message": "Pedido cancelado exitosamente"
}
```

**Error example (400):**
```json
{ "detail": "El pedido ya está cancelado" }
```

---

### Finish an order

Marks an order as `DONE`. The order must be `READY` and already paid.

```
POST /pos/api/orders/<order_id>/finish/
```

**URL parameters:**
- `order_id` (integer)

**Permissions:** `WAITER` or `ADMIN`

**Restrictions:**
- Must currently be `READY`
- Must be paid

**Response (200):**
```json
{
  "ok": true,
  "order_id": 123,
  "status": "DONE"
}
```

**Error examples (400):**
```json
{ "detail": "Solo se puede finalizar cuando esté LISTO. Estado actual: En preparación" }
```
```json
{ "detail": "El pedido debe estar pagado antes de finalizarlo" }
```

---

### Change order status (kitchen)

```
POST /pos/api/orders/<order_id>/status/
```

**URL parameters:**
- `order_id` (integer)

**Permissions:** `KITCHEN` or `ADMIN`

**Restrictions:**
- Kitchen staff can only set `PREP` or `READY`
- Cannot change status on a canceled or already-paid order
- Cannot revert a finished order (`DONE`)

**Body (JSON):**
```json
{ "status": "PREP" }
```

**Accepted values** (English and Spanish aliases both work):
- `NEW` / `NUEVO`
- `PREP` / `EN PREPARACION` / `PREPARANDO`
- `READY` / `LISTO`
- `DONE` / `FINALIZADO`

**Response (200):**
```json
{
  "ok": true,
  "order_id": 123,
  "status": "PREP"
}
```

**Error examples (400):**
```json
{ "detail": "Estado inválido: 'xyz'. Opciones válidas: NEW, PREP, READY, DONE (o sus equivalentes en español)" }
```
```json
{ "detail": "Cocina solo puede marcar estados PREP o READY" }
```

---

## Kitchen

### List active orders

Used by the Kitchen Display System to render its board.

```
GET /pos/api/kitchen/orders/
```

**Permissions:** `KITCHEN` or `ADMIN`

**Response (200):**
```json
[
  {
    "id": 123,
    "zone": "Kiosco",
    "table_number": 5,
    "status": "PREP",
    "items": [
      { "name": "Hamburguesa Clásica", "quantity": 2, "notes": "Sin cebolla" }
    ]
  }
]
```

Excludes orders with status `CANCELED` or `DONE`.

---

## Payments

### Process a payment

Marks an order as paid, computes the tip, prints the receipt, and marks the order as `DONE`.

```
POST /pos/api/orders/<order_id>/pay/
```

**URL parameters:**
- `order_id` (integer)

**Permissions:** `WAITER` or `ADMIN`

**Restrictions:**
- Cannot pay a canceled order
- Cannot pay an order that's already paid
- The order must have at least one item

**Body (JSON):**
```json
{
  "method": "CASH",
  "add_tip": true
}
```

**Fields:**
- `method` (string, required): `CASH`, `NEQUI`, or `TRANSFER`
- `add_tip` (boolean, optional): whether to add a tip (default: `false`)

**Tip calculation:**
- `add_tip=false`, or the business tip type is `NONE`: tip = 0
- Tip type `FIXED`: tip = the configured fixed amount
- Tip type `PERCENT`: tip = subtotal * percentage / 100

**Response (200):**
```json
{
  "ok": true,
  "printed": true
}
```

**Response when printing fails (still 200, payment succeeded):**
```json
{
  "ok": true,
  "printed": false,
  "print_error": "Impresora no disponible"
}
```

**Error examples (400):**
```json
{ "detail": "Método de pago es requerido" }
```
```json
{ "detail": "Método de pago inválido. Opciones: CASH, NEQUI, TRANSFER" }
```
```json
{ "detail": "Este pedido ya fue pagado" }
```

---

## Admin

### Sales analytics

Returns a daily sales series for the selected date range, used by the dashboard chart.

```
GET /pos/api/admin/analytics/?period=today
```

**Query parameters:**
- `period`: `today`, `month`, `year`, or `range`
- `start`, `end` (YYYY-MM-DD): only used when `period=range`

**Permissions:** `ADMIN`

**Response (200):**
```json
{
  "labels": ["2026-03-01", "2026-03-02", "2026-03-03"],
  "totals": [125000.0, 98000.0, 210000.0]
}
```

---

### Order detail

Returns full information for a specific order.

```
GET /pos/api/admin/order/<order_id>/
```

**URL parameters:**
- `order_id` (integer)

**Permissions:** `ADMIN`

**Response (200):**
```json
{
  "id": 123,
  "status": "DONE",
  "zone": "Kiosco",
  "table_number": 5,
  "created_at": "2026-03-06T15:30:00Z",
  "waiter": "mesero1",
  "items": [
    { "name": "Hamburguesa Clásica", "price": "18000.00", "quantity": 2, "notes": "Sin cebolla" }
  ]
}
```

**Error (403):**
```json
{ "detail": "No autorizado" }
```

---

## HTTP Status Codes

| Code | Meaning | Used for |
|------|---------|----------|
| 200 | OK | successful operation |
| 302 | Redirect | login/logout |
| 400 | Bad Request | validation error or invalid data |
| 403 | Forbidden | insufficient permissions |
| 404 | Not Found | resource not found |
| 405 | Method Not Allowed | wrong HTTP method |
| 500 | Internal Server Error | server-side failure |

---

## Usage Examples

### Example 1: full order flow

**1. Load the menu**
```javascript
fetch('/pos/api/menu/')
  .then(res => res.json())
  .then(menu => console.log(menu));
```

**2. Check for an active order on the table**
```javascript
fetch('/pos/api/orders/active/kiosco/5/')
  .then(res => res.json())
  .then(data => {
    if (data.order) {
      console.log('Table occupied, order:', data.order.id);
    } else {
      console.log('Table is free');
    }
  });
```

**3. Create an order**
```javascript
const csrftoken = getCookie('csrftoken');

fetch('/pos/api/orders/create/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrftoken
  },
  body: JSON.stringify({
    zone: 'kiosco',
    table_number: 5,
    items: [
      { menu_item_id: 1, quantity: 2, notes: 'Sin cebolla' },
      { menu_item_id: 3, quantity: 1, notes: '' }
    ]
  })
})
.then(res => res.json())
.then(data => console.log('Order created:', data.order_id));
```

**4. Move it to "In Preparation" (kitchen)**
```javascript
fetch('/pos/api/orders/123/status/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
  body: JSON.stringify({ status: 'PREP' })
})
.then(res => res.json())
.then(data => console.log('Status updated:', data.status));
```

**5. Mark it "Ready"**
```javascript
fetch('/pos/api/orders/123/status/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
  body: JSON.stringify({ status: 'READY' })
})
.then(res => res.json())
.then(data => console.log('Order ready'));
```

**6. Process payment**
```javascript
fetch('/pos/api/orders/123/pay/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
  body: JSON.stringify({ method: 'CASH', add_tip: true })
})
.then(res => res.json())
.then(data => {
  if (data.ok && data.printed) {
    console.log('Paid and receipt printed');
  }
});
```

### Example 2: cancel an order

```javascript
fetch('/pos/api/orders/123/cancel/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
  body: JSON.stringify({ reason: 'Cliente solicitó cancelación' })
})
.then(res => res.json())
.then(data => { if (data.ok) console.log(data.message); });
```

### Example 3: edit an order

```javascript
fetch('/pos/api/orders/123/edit/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
  body: JSON.stringify({
    items: [
      { menu_item_id: 1, quantity: 3, notes: 'Término medio' },
      { menu_item_id: 5, quantity: 2, notes: '' }
    ]
  })
})
.then(res => res.json())
.then(() => console.log('Order updated'));
```

### Helper: read the CSRF cookie

```javascript
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
```

### Error handling pattern

```javascript
fetch('/pos/api/orders/create/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
  body: JSON.stringify(orderData)
})
.then(async res => {
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Error al crear pedido');
  }
  return data;
})
.then(data => console.log('Success:', data))
.catch(error => {
  console.error('Error:', error.message);
  alert('Error: ' + error.message);
});
```

---

## WebSockets

Real-time updates are pushed over three WebSocket routes:

| Route | Consumer | Purpose |
|-------|----------|---------|
| `ws/kitchen/` | `KitchenConsumer` | kitchen-wide broadcasts |
| `ws/tables/` | `TablesConsumer` | tables overview screen |
| `ws/table/<zone>/<table>/` | `TableOrderConsumer` | a single table's order screen |

### Connecting

```javascript
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/tables/`;

const socket = new WebSocket(wsUrl);

socket.onopen = () => console.log('WebSocket connected');
socket.onerror = (e) => console.error('WebSocket error:', e);
socket.onclose = () => console.log('WebSocket closed');

socket.onmessage = (e) => {
  const data = JSON.parse(e.data);
  console.log('Table update:', data);
  // data.table     - table number
  // data.zone      - zone slug
  // data.status    - NEW, PREP, READY, DONE, or "" (freed)
  // data.order_id  - order id
};
```

### Message format

Sent whenever an order is created, edited, its status changes, it's paid, or canceled:

```json
{
  "type": "table_status",
  "order_id": 123,
  "status": "PREP",
  "zone": "kiosco",
  "table": 5
}
```

**Possible `status` values:**
- `NEW` - new order
- `PREP` - being prepared
- `READY` - ready to serve
- `DONE` - finished
- `""` (empty) - table is free (order canceled or completed)

---

## Additional Notes

### Global rules

1. **Authentication:** every endpoint requires a logged-in session.
2. **CSRF token:** every `POST` request needs a valid CSRF token.
3. **JSON body:** request bodies must be valid JSON with `Content-Type: application/json`.
4. **Permissions:** some endpoints require a specific role (`ADMIN`, `WAITER`, `KITCHEN`).

### Limits

- Maximum 100 items per order
- Order notes: max 500 characters
- Cancellation reason: max 500 characters
- Tip amount: max $1,000,000

### Transactions

Order creation and editing run inside atomic database transactions, so a failure midway never leaves an order in a half-written state.

### Logging

Every critical operation (create, edit, pay, cancel) is written to the application logs with enough detail for auditing.
