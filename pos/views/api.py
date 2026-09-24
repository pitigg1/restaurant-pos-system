"""
JSON API endpoints for waiter, kitchen, admin and payment.
"""
from decimal import Decimal
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.models import User
from pos.models import BusinessConfig, MenuItem, MenuCategory, Order, OrderItem, OrderEvent, Zone
from pos.printing import print_order_receipt
from .helpers import (
    json_body, slugify_simple, require_roles, _order_total,
    _ws_send_table_status, broadcast_table_status,
)

# Logger for this module
logger = logging.getLogger(__name__)


# -------------------------
# Menu API
# -------------------------

@login_required
def api_menu(request):
    items = MenuItem.objects.filter(available=True).select_related("category").order_by("category__order", "name")
    data = [
        {
            "id": m.id,
            "name": m.name,
            "price": str(m.price),
            "category": m.category.name if m.category else None,
            "category_id": m.category_id,
        }
        for m in items
    ]
    return JsonResponse(data, safe=False)


# -------------------------
# Active orders
# -------------------------

@login_required
def api_active_table_order(request, zone, table):
    zone_slug = slugify_simple(zone)

    zone_obj = Zone.objects.filter(slug=zone_slug).first()
    zone_name = zone_obj.name if zone_obj else zone.strip()

    order = (
        Order.objects
        .filter(zone__iexact=zone_name, table_number=table)
        .exclude(status__in=[Order.Status.CANCELED, Order.Status.DONE])
        .order_by("-created_at")
        .prefetch_related("items__menu_item")
        .first()
    )

    if not order:
        return JsonResponse({"order": None})

    return JsonResponse({
        "order": {
            "id": order.id,
            "zone": order.zone,
            "table_number": order.table_number,
            "status": order.status,
            "items": [
                {
                    "menu_item_id": it.menu_item_id,
                    "name": it.menu_item.name if it.menu_item else "Item eliminado",
                    "price": str(it.menu_item.price) if it.menu_item else "0",
                    "quantity": it.quantity,
                    "notes": it.notes or "",
                }
                for it in order.items.all()
            ],
        }
    })


# -------------------------
# Create order
# -------------------------

@login_required
def api_create_order(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Método no permitido"}, status=405)
    if not require_roles(request.user, [User.Role.WAITER, User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    payload = json_body(request)
    zone_slug = (payload.get("zone") or "").strip()

    # Validate table_number
    try:
        table_number = int(payload.get("table_number", 0))
    except (ValueError, TypeError):
        return JsonResponse({"detail": "Número de mesa debe ser un entero válido"}, status=400)

    items = payload.get("items", [])

    # Basic validation
    if not zone_slug:
        return JsonResponse({"detail": "Zona es requerida"}, status=400)
    if table_number <= 0:
        return JsonResponse({"detail": "Número de mesa debe ser mayor a 0"}, status=400)
    if not items:
        return JsonResponse({"detail": "El pedido debe tener al menos un item"}, status=400)
    if not isinstance(items, list):
        return JsonResponse({"detail": "Items debe ser una lista"}, status=400)

    # Validate zone
    zone_obj = Zone.objects.filter(slug=zone_slug, is_active=True).first()
    if not zone_obj:
        return JsonResponse({"detail": f"Zona '{zone_slug}' no existe o está inactiva"}, status=400)
    zone_name = zone_obj.name

    # Validate that the table exists in the zone
    table_exists = zone_obj.tables.filter(number=table_number, is_active=True).exists()
    if not table_exists:
        return JsonResponse(
            {"detail": f"Mesa {table_number} no existe en zona '{zone_name}' o está inactiva"},
            status=400
        )

    # Validate items
    validated_items = []
    for idx, it in enumerate(items):
        if not isinstance(it, dict):
            return JsonResponse({"detail": f"Item {idx + 1}: debe ser un objeto"}, status=400)

        # Validate menu_item_id
        try:
            menu_id = int(it.get("menu_item_id"))
        except (ValueError, TypeError):
            return JsonResponse(
                {"detail": f"Item {idx + 1}: menu_item_id debe ser un entero válido"},
                status=400
            )

        # Validate quantity
        try:
            qty = int(it.get("quantity", 1))
        except (ValueError, TypeError):
            return JsonResponse(
                {"detail": f"Item {idx + 1}: quantity debe ser un entero válido"},
                status=400
            )

        if qty <= 0:
            return JsonResponse(
                {"detail": f"Item {idx + 1}: quantity debe ser mayor a 0"},
                status=400
            )

        if qty > 100:
            return JsonResponse(
                {"detail": f"Item {idx + 1}: quantity no puede ser mayor a 100"},
                status=400
            )

        # Validate that the item exists and is available
        menu_item = MenuItem.objects.filter(id=menu_id, available=True).first()
        if not menu_item:
            return JsonResponse(
                {"detail": f"Item {idx + 1}: el producto no existe o no está disponible"},
                status=400
            )

        # Validate notes
        notes = it.get("notes", "") or ""
        if not isinstance(notes, str):
            notes = str(notes)
        if len(notes) > 500:
            return JsonResponse(
                {"detail": f"Item {idx + 1}: notas no pueden exceder 500 caracteres"},
                status=400
            )

        validated_items.append({
            "menu_item_id": menu_id,
            "quantity": qty,
            "notes": notes.strip()
        })

    # Create order inside a transaction
    try:
        with transaction.atomic():
            order = Order.objects.create(
                zone=zone_name,
                table_number=table_number,
                waiter=request.user,
                status=Order.Status.NEW
            )

            for item_data in validated_items:
                OrderItem.objects.create(
                    order=order,
                    menu_item_id=item_data["menu_item_id"],
                    quantity=item_data["quantity"],
                    notes=item_data["notes"]
                )

            OrderEvent.objects.create(order=order, event="created", user=request.user)

        logger.info(
            f"Pedido creado: ID={order.id}, zona={zone_name}, mesa={table_number}, "
            f"mesero={request.user.username}, items={len(validated_items)}"
        )

        _ws_send_table_status(order)

        return JsonResponse({"ok": True, "order_id": order.id})

    except Exception as e:
        logger.error(
            f"Error al crear pedido: zona={zone_slug}, mesa={table_number}, "
            f"mesero={request.user.username}, error={str(e)}",
            exc_info=True
        )
        return JsonResponse(
            {"detail": "Error al crear el pedido. Intenta de nuevo."},
            status=500
        )


# -------------------------
# Edit order
# -------------------------

@login_required
def api_edit_order(request, order_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Método no permitido"}, status=405)
    if not require_roles(request.user, [User.Role.WAITER, User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    # Validate order_id
    try:
        order_id = int(order_id)
    except (ValueError, TypeError):
        return JsonResponse({"detail": "ID de pedido inválido"}, status=400)

    order = get_object_or_404(Order, id=order_id)

    # Validate the order's status
    if order.status == Order.Status.CANCELED:
        return JsonResponse({"detail": "No se puede editar un pedido cancelado"}, status=400)
    if order.status == Order.Status.DONE:
        return JsonResponse({"detail": "No se puede editar un pedido finalizado"}, status=400)
    if order.is_paid:
        return JsonResponse({"detail": "No se puede editar un pedido ya pagado"}, status=400)

    payload = json_body(request)
    items = payload.get("items", [])

    # Basic validation
    if not items:
        return JsonResponse({"detail": "El pedido debe tener al menos un item"}, status=400)
    if not isinstance(items, list):
        return JsonResponse({"detail": "Items debe ser una lista"}, status=400)

    # Validate items
    validated_items = []
    for idx, it in enumerate(items):
        if not isinstance(it, dict):
            return JsonResponse({"detail": f"Item {idx + 1}: debe ser un objeto"}, status=400)

        # Validate menu_item_id
        try:
            menu_id = int(it.get("menu_item_id"))
        except (ValueError, TypeError):
            return JsonResponse(
                {"detail": f"Item {idx + 1}: menu_item_id debe ser un entero válido"},
                status=400
            )

        # Validate quantity
        try:
            qty = int(it.get("quantity", 1))
        except (ValueError, TypeError):
            return JsonResponse(
                {"detail": f"Item {idx + 1}: quantity debe ser un entero válido"},
                status=400
            )

        if qty <= 0:
            return JsonResponse(
                {"detail": f"Item {idx + 1}: quantity debe ser mayor a 0"},
                status=400
            )

        if qty > 100:
            return JsonResponse(
                {"detail": f"Item {idx + 1}: quantity no puede ser mayor a 100"},
                status=400
            )

        # Validate that the item exists and is available
        menu_item = MenuItem.objects.filter(id=menu_id, available=True).first()
        if not menu_item:
            return JsonResponse(
                {"detail": f"Item {idx + 1}: el producto no existe o no está disponible"},
                status=400
            )

        # Validate notes
        notes = it.get("notes", "") or ""
        if not isinstance(notes, str):
            notes = str(notes)
        if len(notes) > 500:
            return JsonResponse(
                {"detail": f"Item {idx + 1}: notas no pueden exceder 500 caracteres"},
                status=400
            )

        validated_items.append({
            "menu_item_id": menu_id,
            "quantity": qty,
            "notes": notes.strip()
        })

    # Update order inside a transaction (replace all items)
    try:
        with transaction.atomic():
            order.items.all().delete()

            for item_data in validated_items:
                OrderItem.objects.create(
                    order=order,
                    menu_item_id=item_data["menu_item_id"],
                    quantity=item_data["quantity"],
                    notes=item_data["notes"]
                )

            OrderEvent.objects.create(order=order, event="updated", user=request.user)

        logger.info(
            f"Pedido editado: ID={order.id}, zona={order.zone}, mesa={order.table_number}, "
            f"usuario={request.user.username}, items={len(validated_items)}"
        )

        _ws_send_table_status(order)

        return JsonResponse({"ok": True})

    except Exception as e:
        logger.error(
            f"Error al editar pedido: ID={order_id}, usuario={request.user.username}, "
            f"error={str(e)}",
            exc_info=True
        )
        return JsonResponse(
            {"detail": "Error al editar el pedido. Intenta de nuevo."},
            status=500
        )


# -------------------------
# Cancel order
# -------------------------

@login_required
def api_cancel_order(request, order_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Método no permitido"}, status=405)
    if not require_roles(request.user, [User.Role.WAITER, User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    # Validate order_id
    try:
        order_id = int(order_id)
    except (ValueError, TypeError):
        return JsonResponse({"detail": "ID de pedido inválido"}, status=400)

    order = get_object_or_404(Order, id=order_id)

    # Validate that the order can be canceled
    if order.status == Order.Status.CANCELED:
        return JsonResponse({"detail": "El pedido ya está cancelado"}, status=400)

    if order.status == Order.Status.DONE:
        return JsonResponse({"detail": "No se puede cancelar un pedido finalizado"}, status=400)

    if order.is_paid:
        return JsonResponse({"detail": "No se puede cancelar un pedido ya pagado"}, status=400)

    payload = json_body(request)
    reason = (payload.get("reason") or "").strip()

    # Validate reason length
    if reason and len(reason) > 500:
        return JsonResponse({"detail": "La razón no puede exceder 500 caracteres"}, status=400)

    # Cancel order
    order.status = Order.Status.CANCELED
    order.save(update_fields=["status", "updated_at"])

    OrderEvent.objects.create(
        order=order,
        event=f"canceled:{reason}" if reason else "canceled",
        user=request.user
    )

    logger.warning(
        f"Pedido cancelado: ID={order.id}, zona={order.zone}, mesa={order.table_number}, "
        f"usuario={request.user.username}, razón='{reason}'"
    )

    _ws_send_table_status(order, status_override="")

    return JsonResponse({"ok": True, "message": "Pedido cancelado exitosamente"})


# -------------------------
# Order detail (admin API)
# -------------------------

@login_required
def api_admin_order_detail(request, order_id):
    if not require_roles(request.user, [User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    order = get_object_or_404(
        Order.objects.select_related("waiter").prefetch_related("items__menu_item"),
        id=order_id
    )

    items = []
    for it in order.items.all():
        items.append({
            "name": it.menu_item.name if it.menu_item else "Item eliminado",
            "price": str(it.menu_item.price) if it.menu_item else "0",
            "quantity": it.quantity,
            "notes": it.notes or "",
        })

    return JsonResponse({
        "id": order.id,
        "status": order.status,
        "zone": order.zone,
        "table_number": order.table_number,
        "created_at": order.created_at.isoformat(),
        "waiter": order.waiter.username if order.waiter else "",
        "items": items,
    })


# -------------------------
# Finish order
# -------------------------

@login_required
def api_finish_order(request, order_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Método no permitido"}, status=405)

    if not require_roles(request.user, [User.Role.WAITER, User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    # Validate order_id
    try:
        order_id = int(order_id)
    except (ValueError, TypeError):
        return JsonResponse({"detail": "ID de pedido inválido"}, status=400)

    order = get_object_or_404(Order, id=order_id)

    # Status validation
    if order.status == Order.Status.CANCELED:
        return JsonResponse({"detail": "No se puede finalizar un pedido cancelado"}, status=400)

    if order.status == Order.Status.DONE:
        return JsonResponse({"detail": "El pedido ya está finalizado"}, status=400)

    if order.status != Order.Status.READY:
        return JsonResponse(
            {"detail": f"Solo se puede finalizar cuando esté LISTO. Estado actual: {order.get_status_display()}"},
            status=400
        )

    if not order.is_paid:
        return JsonResponse({"detail": "El pedido debe estar pagado antes de finalizarlo"}, status=400)

    # Finish order
    order.status = Order.Status.DONE
    order.save(update_fields=["status", "updated_at"])

    OrderEvent.objects.create(order=order, event="status:DONE", user=request.user)

    _ws_send_table_status(order)

    return JsonResponse({"ok": True, "order_id": order.id, "status": order.status})


# -------------------------
# Change status (kitchen)
# -------------------------

@login_required
def api_change_order_status(request, order_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Método no permitido"}, status=405)

    if not require_roles(request.user, [User.Role.KITCHEN, User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    # Validate order_id
    try:
        order_id = int(order_id)
    except (ValueError, TypeError):
        return JsonResponse({"detail": "ID de pedido inválido"}, status=400)

    order = get_object_or_404(Order, id=order_id)

    # Validate that the order isn't canceled or paid
    if order.status == Order.Status.CANCELED:
        return JsonResponse({"detail": "No se puede cambiar el estado de un pedido cancelado"}, status=400)

    if order.is_paid:
        return JsonResponse({"detail": "No se puede cambiar el estado de un pedido ya pagado"}, status=400)

    payload = json_body(request)
    raw = (payload.get("status") or "").strip()

    if not raw:
        return JsonResponse({"detail": "Estado es requerido"}, status=400)

    key = raw.upper().strip()

    # Alias map, accepts both English keys and their Spanish equivalents
    alias = {
        "NEW": Order.Status.NEW,
        "NUEVO": Order.Status.NEW,

        "PREP": Order.Status.PREP,
        "EN PREPARACION": Order.Status.PREP,
        "EN_PREPARACION": Order.Status.PREP,
        "PREPARACION": Order.Status.PREP,
        "PREPARANDO": Order.Status.PREP,

        "READY": Order.Status.READY,
        "LISTO": Order.Status.READY,
        "LISTA": Order.Status.READY,

        "DONE": Order.Status.DONE,
        "FINALIZADO": Order.Status.DONE,
        "FINALIZADA": Order.Status.DONE,
    }

    status = alias.get(key)

    if status is None:
        valid_options = "NEW, PREP, READY, DONE (o sus equivalentes en español)"
        return JsonResponse(
            {"detail": f"Estado inválido: '{raw}'. Opciones válidas: {valid_options}"},
            status=400
        )

    # Kitchen may only set PREP or READY
    if request.user.role == User.Role.KITCHEN and status not in [Order.Status.PREP, Order.Status.READY]:
        return JsonResponse(
            {"detail": "Cocina solo puede marcar estados PREP o READY"},
            status=400
        )

    # Validate allowed status transitions
    if order.status == Order.Status.DONE and status != Order.Status.DONE:
        return JsonResponse(
            {"detail": "No se puede revertir un pedido finalizado"},
            status=400
        )

    # Update status
    old_status = order.status
    order.status = status
    order.save(update_fields=["status", "updated_at"])

    OrderEvent.objects.create(
        order=order,
        event=f"status:{old_status}→{status}",
        user=request.user
    )

    logger.info(
        f"Estado cambiado: Pedido ID={order.id}, {old_status} → {status}, "
        f"usuario={request.user.username} ({request.user.get_role_display()})"
    )

    broadcast_table_status(order)

    return JsonResponse({"ok": True, "order_id": order.id, "status": order.status})


# -------------------------
# Payment / checkout
# -------------------------

def _print_receipt_usb(order, method_label: str, tip_amount: int = 0):
    """
    Prints a receipt on the SAT38TUSE (80mm) thermal printer.
    """
    import win32print
    import win32ui
    import time

    PRINTER_NAME = getattr(settings, "RECEIPT_PRINTER_NAME", "SAT38TUSE")

    def esc_init():
        return b"\x1b@"

    def esc_align(n: int):
        return b"\x1ba" + bytes([n])

    def esc_bold(on: bool):
        return b"\x1bE" + (b"\x01" if on else b"\x00")

    def esc_size(w: int = 1, h: int = 1):
        w = max(1, min(8, w))
        h = max(1, min(8, h))
        n = ((w - 1) << 4) | (h - 1)
        return b"\x1d!" + bytes([n])

    def esc_cut_partial():
        return b"\x1dV\x01"

    def esc_feed(lines: int):
        return b"\n" * max(0, lines)

    def esc_left_margin_dots(dots: int):
        dots = max(0, int(dots))
        nL = dots & 0xFF
        nH = (dots >> 8) & 0xFF
        return b"\x1dL" + bytes([nL, nH])

    def text(s: str):
        return s.encode("cp437", errors="replace")

    def money(n):
        try:
            n = float(n)
        except Exception:
            n = 0.0
        return f"${int(round(n)):,}".replace(",", ".")

    def item_line(name: str, qty: int, price_each: float, width=48):
        left = f"{qty} x {name}".strip()
        right = money(price_each)

        if len(left) > width - len(right) - 1:
            left = left[: (width - len(right) - 4)] + "..."
        spaces = " " * max(1, width - len(left) - len(right))
        return f"{left}{spaces}{right}\n"

    # Build the ticket (raw bytes)
    now = timezone.localtime(timezone.now())

    subtotal = order.total_amount()
    tip_amount = int(tip_amount or 0)
    total_final = subtotal + tip_amount

    WIDTH = 48
    LEFT_MARGIN_DOTS = 0

    b = bytearray()
    b += esc_init()
    b += esc_left_margin_dots(LEFT_MARGIN_DOTS)

    # Header — business name from BusinessConfig
    biz_name = BusinessConfig.get_config().name
    b += esc_align(1)
    b += esc_bold(True)
    b += esc_size(2, 2)
    b += text(f"{biz_name}\n")
    b += esc_size(1, 1)
    b += esc_bold(False)
    b += text("-" * WIDTH + "\n")

    # Meta info
    b += esc_align(1)
    b += esc_bold(True)
    b += text(f"Pedido #{order.id}\n")
    b += esc_bold(False)
    b += text(f"{order.zone} - Mesa {order.table_number}\n")
    if getattr(order, "waiter", None):
        b += text(f"Mesera: {order.waiter.username}\n")
    b += text(now.strftime("%Y-%m-%d %H:%M") + "\n")
    b += text("-" * WIDTH + "\n")

    # Items
    b += esc_align(0)
    for it in order.items.all():
        name = it.menu_item.name if it.menu_item else "Item"
        price_each = float(it.menu_item.price) if it.menu_item else 0.0

        b += text(item_line(name, it.quantity, price_each, width=WIDTH))

        if it.notes:
            note = (it.notes or "").strip()
            if note:
                max_note = WIDTH - 6
                if len(note) > max_note:
                    note = note[: max_note - 3] + "..."
                b += text(f"  * {note}\n")

    b += text("-" * WIDTH + "\n")

    # Subtotal / tip
    b += esc_align(1)
    b += esc_bold(True)
    b += text(f"SUBTOTAL: {money(subtotal)}\n")
    b += esc_bold(False)

    if tip_amount > 0:
        b += text(f"PROPINA:  {money(tip_amount)}\n")

    b += text("-" * WIDTH + "\n")

    # Total, printed larger
    b += esc_align(1)
    b += esc_bold(True)
    b += esc_size(2, 2)
    b += text(f"TOTAL: {money(total_final)}\n")
    b += esc_size(1, 1)
    b += esc_bold(False)

    # Payment method
    b += text(f"PAGO: {method_label}\n")
    b += text("-" * WIDTH + "\n")

    # Footer
    b += esc_align(1)
    b += text("Gracias por tu compra\n")

    b += esc_feed(8)
    b += esc_cut_partial()

    # Send to the Windows printer
    h = win32print.OpenPrinter(PRINTER_NAME)
    try:
        win32print.StartDocPrinter(h, 1, ("Ticket", None, "RAW"))
        win32print.StartPagePrinter(h)
        win32print.WritePrinter(h, bytes(b))
        win32print.EndPagePrinter(h)
        win32print.EndDocPrinter(h)

        time.sleep(0.25)
    finally:
        win32print.ClosePrinter(h)


@login_required
def api_pay_order(request, order_id):
    if request.method != "POST":
        return JsonResponse({"detail": "Método no permitido"}, status=405)

    if not require_roles(request.user, [User.Role.WAITER, User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    # Validate order_id
    try:
        order_id = int(order_id)
    except (ValueError, TypeError):
        return JsonResponse({"detail": "ID de pedido inválido"}, status=400)

    order = get_object_or_404(
        Order.objects.select_related("waiter").prefetch_related("items__menu_item"),
        id=order_id
    )

    # Order status validation
    if order.status == Order.Status.CANCELED:
        return JsonResponse({"detail": "No se puede pagar un pedido cancelado"}, status=400)

    if order.is_paid:
        return JsonResponse({"detail": "Este pedido ya fue pagado"}, status=400)

    # Validate that the order has items
    if not order.items.exists():
        return JsonResponse({"detail": "El pedido no tiene items"}, status=400)

    payload = json_body(request)
    method = (payload.get("method") or "").upper().strip()

    # Validate payment method
    valid_methods = {
        "CASH": "Efectivo",
        "NEQUI": "Nequi",
        "TRANSFER": "Transferencia",
    }

    if not method:
        return JsonResponse({"detail": "Método de pago es requerido"}, status=400)

    if method not in valid_methods:
        available_methods = ", ".join(valid_methods.keys())
        return JsonResponse(
            {"detail": f"Método de pago inválido. Opciones: {available_methods}"},
            status=400
        )

    # Validate and compute the tip
    biz = BusinessConfig.get_config()
    add_tip = payload.get("add_tip", False)

    if isinstance(add_tip, str):
        add_tip = add_tip.strip().lower() in ("1", "true", "yes", "y", "si", "sí", "on")
    else:
        add_tip = bool(add_tip)

    if not add_tip or biz.tip_type == BusinessConfig.TipType.NONE:
        tip_amount = 0
    elif biz.tip_type == BusinessConfig.TipType.FIXED:
        tip_amount = int(biz.tip_value)
    elif biz.tip_type == BusinessConfig.TipType.PERCENT:
        subtotal = order.total_amount()
        if subtotal <= 0:
            return JsonResponse({"detail": "El total del pedido debe ser mayor a 0"}, status=400)
        tip_amount = int(float(subtotal) * float(biz.tip_value) / 100)
    else:
        tip_amount = 0

    # Sanity-check the tip amount
    if tip_amount < 0:
        tip_amount = 0
    if tip_amount > 1000000:  # safety cap
        return JsonResponse({"detail": "Monto de propina excede el límite permitido"}, status=400)

    # Mark as paid
    order.is_paid = True
    order.payment_method = method
    order.paid_at = timezone.now()
    order.paid_by = request.user

    order.tip_amount = int(tip_amount or 0)
    order.has_tip = order.tip_amount > 0

    order.status = Order.Status.DONE

    order.save(update_fields=[
        "is_paid", "payment_method", "paid_at", "paid_by",
        "tip_amount", "has_tip",
        "status", "updated_at"
    ])

    try:
        OrderEvent.objects.create(
            order=order,
            event=f"paid:{method}:tip:{tip_amount}",
            user=request.user
        )
    except Exception:
        pass

    subtotal = order.total_amount()
    total_with_tip = subtotal + tip_amount

    logger.info(
        f"Pedido pagado: ID={order.id}, zona={order.zone}, mesa={order.table_number}, "
        f"método={valid_methods[method]}, subtotal=${subtotal:,.0f}, propina=${tip_amount:,.0f}, "
        f"total=${total_with_tip:,.0f}, usuario={request.user.username}"
    )

    # Print the receipt
    try:
        _print_receipt_usb(order, valid_methods[method], tip_amount=tip_amount)
        logger.info(f"Ticket impreso exitosamente para pedido ID={order.id}")
    except TypeError:
        _print_receipt_usb(order, valid_methods[method])
        logger.info(f"Ticket impreso exitosamente para pedido ID={order.id}")
    except Exception as e:
        logger.error(
            f"Error al imprimir ticket: Pedido ID={order.id}, error={str(e)}",
            exc_info=True
        )
        return JsonResponse({"ok": True, "printed": False, "print_error": str(e)})

    _ws_send_table_status(order)
    return JsonResponse({"ok": True, "printed": True})
