from django.conf import settings
from django.utils import timezone

# Formats an integer with a "." as the thousands separator (Colombian pesos).
def format_money(n):
    try:
        return f"{int(round(float(n))):,}".replace(",", ".")
    except:
        return str(n)

# Builds the plain-text receipt sent straight to the thermal printer.
def build_receipt_text(order, total, items):
    lines = []
    lines.append("LAS HAMACAS")
    lines.append("--------------------------------")
    lines.append(f"Pedido #{order.id}")
    lines.append(f"{order.zone} - Mesa {order.table_number}")
    lines.append(f"Fecha: {timezone.localtime(order.paid_at or order.updated_at).strftime('%Y-%m-%d %H:%M')}")
    lines.append("--------------------------------")

    for it in items:
        name = (it.menu_item.name if it.menu_item else "Item")
        qty = it.quantity
        price = (it.menu_item.price if it.menu_item else 0)
        lines.append(f"{qty} x {name}")
        if it.notes:
            lines.append(f"  Nota: {it.notes}")
        # optional: per-line price
        # lines.append(f"    ${format_money(price)}")

    lines.append("--------------------------------")
    lines.append(f"TOTAL: ${format_money(total)}")
    if order.payment_method:
        lines.append(f"PAGO: {order.get_payment_method_display()}")
    lines.append("--------------------------------")
    lines.append("Gracias por su compra")
    lines.append("\n\n")  # room for the paper cut

    # Note: thermal printers usually expect CP437 or UTF-8.
    # Trying UTF-8 first; switch encoding if you see garbled characters.
    return "\n".join(lines)

def print_raw_windows(text: str, printer_name: str):
    """
    Prints RAW text on Windows via win32print.
    Requires: pip install pywin32
    """
    import win32print

    handle = win32print.OpenPrinter(printer_name)
    try:
        job = win32print.StartDocPrinter(handle, 1, ("Ticket", None, "RAW"))
        try:
            win32print.StartPagePrinter(handle)

            data = text.encode("utf-8", errors="replace")
            win32print.WritePrinter(handle, data)

            # Paper cut (ESC/POS command "GS V 1"), supported by most printers.
            cut = b"\x1d\x56\x01"
            win32print.WritePrinter(handle, cut)

            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)

# Entry point used by the views to print a receipt for a paid order.
def print_order_receipt(order, total, items):
    printer = getattr(settings, "RECEIPT_PRINTER_NAME", "") or ""
    if not printer:
        raise RuntimeError("RECEIPT_PRINTER_NAME no está configurado en settings.py")

    text = build_receipt_text(order, total, items)
    print_raw_windows(text, printer)
