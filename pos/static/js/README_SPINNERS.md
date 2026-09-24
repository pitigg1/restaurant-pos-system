# Documentación de Spinners

Este documento explica cómo usar el sistema de spinners de carga en el frontend (`spinner.js`).

## 1. Spinner Global

```javascript
// Mostrar spinner
showSpinner('Procesando pago...');

// Realizar operación
setTimeout(() => {
    // Ocultar spinner
    hideSpinner();
}, 2000);
```

## 2. Spinner con Función Async

```javascript
await withSpinner(async () => {
    const response = await fetch('/api/data');
    const data = await response.json();
    return data;
}, 'Cargando datos...');
```

## 3. Spinner en Botón

```javascript
const button = document.getElementById('miBoton');

// Opción 1: Manual
const restore = showButtonSpinner(button, 'Guardando...');
// ... realizar operación ...
restore();  // Restaurar botón

// Opción 2: Con función async
await withButtonSpinner(
    button,
    async () => {
        const response = await fetch('/api/save', { method: 'POST' });
        return response.json();
    },
    'Guardando...'
);
```

## 4. Spinner en Contenedor

```javascript
// Mostrar spinner en un contenedor específico
showContainerSpinner('#miContenedor', 'Cargando tabla...');

// Realizar operación
fetch('/api/data')
    .then(response => response.json())
    .then(data => {
        // Ocultar spinner y mostrar datos
        hideContainerSpinner('#miContenedor');
        renderData(data);
    });
```

## Notas

- `spinner.js` es vanilla JS, no depende de jQuery ni Bootstrap.
- Los spinners incluyen sus propios estilos inline.
- Ninguna plantilla llama estas funciones todavía — quedan disponibles para cuando se necesiten (ej. en `waiter_order.html` al guardar/cobrar un pedido).
