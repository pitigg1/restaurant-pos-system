"""
Kitchen views (KDS - Kitchen Display System).
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from core.models import User
from pos.models import Order
from .helpers import require_roles


# -------------------------
# Kitchen UI
# -------------------------

@login_required
def kitchen_kds(request):
    if not require_roles(request.user, [User.Role.KITCHEN, User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)
    return render(request, "kitchen_kds.html")


@login_required
def kitchen_orders_api(request):
    if not require_roles(request.user, [User.Role.KITCHEN, User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    # Only what the kitchen still has to cook, oldest first. Once an order
    # is marked READY it leaves the board.
    orders = (
        Order.objects
        .filter(status__in=[Order.Status.NEW, Order.Status.PREP])
        .order_by("created_at", "id")
        .prefetch_related("items__menu_item")
    )

    data = []
    for o in orders:
        data.append({
            "id": o.id,
            "zone": o.zone,
            "table_number": o.table_number,
            "status": o.status,
            "created_at": o.created_at.isoformat(),
            "items": [
                {"name": it.menu_item.name, "quantity": it.quantity, "notes": it.notes or ""}
                for it in o.items.all()
            ],
        })

    return JsonResponse(data, safe=False)
