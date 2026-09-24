"""
Shared helper functions used across all view modules.
"""
import json
import socket
from datetime import date, datetime, timedelta
from decimal import Decimal

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from core.models import User
from pos.models import Order


# -------------------------
# Base helpers
# -------------------------

def json_body(request):
    """Parses a request's JSON body."""
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return {}


def slugify_simple(s: str) -> str:
    """Simple slug for zones (no dependency on django.utils.text)."""
    return (
        (s or "")
        .strip()
        .lower()
        .replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        .replace("ñ", "n")
        .replace(" ", "-")
    )


def _order_total(order: Order) -> float:
    """Calculates an order's total by iterating over its items."""
    total = 0.0
    for it in order.items.all():
        total += float(it.menu_item.price) * int(it.quantity)
    return total


def require_roles(user, roles):
    """Checks that the user has one of the given roles."""
    return user.is_authenticated and (user.is_superuser or getattr(user, "role", None) in roles)


def _admin_only(request):
    """Returns a 403 JsonResponse if the user isn't an admin, or None if they are."""
    from django.http import JsonResponse
    if not require_roles(request.user, [User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)
    return None


def _parse_period(request):
    """
    Parses date-range parameters from GET.
    period: today|month|year|range
    start/end: YYYY-MM-DD (when period=range)
    Returns: (period, start_date, end_date) as date objects
    """
    period = (request.GET.get("period") or "today").lower()
    today = timezone.localdate()

    if period == "today":
        start = end = today
    elif period == "month":
        start = today.replace(day=1)
        end = today
    elif period == "year":
        start = today.replace(month=1, day=1)
        end = today
    elif period == "range":
        s = request.GET.get("start")
        e = request.GET.get("end")
        try:
            start = datetime.strptime(s, "%Y-%m-%d").date() if s else today
            end = datetime.strptime(e, "%Y-%m-%d").date() if e else today
        except Exception:
            start = end = today
    else:
        start = end = today

    if end < start:
        start, end = end, start

    return period, start, end


# -------------------------
# WebSockets / broadcast
# -------------------------

def _ws_send_table_status(order: Order, status_override: str | None = None):
    """
    Notifies over WebSocket:
    - The global "tables" group (tables overview screen)
    - The table-specific "table_<zoneSlug>_<table>" group (single table screen)
    """
    try:
        channel_layer = get_channel_layer()
        zone_slug = slugify_simple(order.zone)

        payload = {
            "type": "table_status",
            "order_id": order.id,
            "status": (status_override or order.status),
            "zone": zone_slug,
            "table": order.table_number,
        }

        async_to_sync(channel_layer.group_send)(
            "tables",
            {"type": "tables_event", "payload": payload}
        )

        async_to_sync(channel_layer.group_send)(
            f"table_{zone_slug}_{order.table_number}",
            {"type": "table_event", "payload": payload}
        )
    except Exception as e:
        print("WS broadcast failed:", str(e))


def broadcast_table_status(order: Order):
    """Alias for _ws_send_table_status (kept for compatibility)."""
    _ws_send_table_status(order)


# -------------------------
# Network utilities
# -------------------------

def _get_local_ip():
    """Returns the PC's local IP (so phones on the LAN can reach it)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _build_base_url(request, port=8000):
    """Builds a base_url using the real local IP."""
    ip = _get_local_ip()
    return f"http://{ip}:{port}"


# -------------------------
# USB / printer discovery
# -------------------------

def _find_epson_usb_ids():
    """
    Lists connected USB devices (to discover VID/PID).
    Useful to run once from the Django shell.
    """
    try:
        import usb.core
        import usb.util

        devs = usb.core.find(find_all=True)
        out = []
        for d in devs:
            out.append((hex(d.idVendor), hex(d.idProduct)))
        return out
    except Exception as e:
        return [("error", str(e))]


# -------------------------
# ESC/POS printing helpers
# -------------------------

def _col_widths(paper="58"):
    return 32 if paper == "58" else 48


def _center(text, width):
    text = str(text)
    if len(text) >= width:
        return text[:width]
    pad = (width - len(text)) // 2
    return (" " * pad) + text


def _lr(left, right, width):
    left = str(left)
    right = str(right)
    space = width - len(left) - len(right)
    if space < 1:
        left = left[: max(0, width - len(right) - 1)]
        space = 1
    return left + (" " * space) + right


def _money_cop(n):
    n = float(n)
    return "$" + f"{int(round(n)):,}".replace(",", ".")


def _sanitize(s):
    return (s or "").replace("\t", " ").strip()
