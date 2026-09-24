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

    orders = (
        Order.objects
        .exclude(status__in=[Order.Status.CANCELED, Order.Status.DONE])
        .order_by("created_at")
        .prefetch_related("items__menu_item")
    )

    data = []
    for o in orders:
        data.append({
            "id": o.id,
            "zone": o.zone,
            "table_number": o.table_number,
            "status": o.status,
            "items": [
                {"name": it.menu_item.name, "quantity": it.quantity, "notes": it.notes or ""}
                for it in o.items.all()
            ],
        })

    return JsonResponse(data, safe=False)
