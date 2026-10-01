"""
Waiter views: the tables screen and a single table's order.
Uses the Zone and Table models from the database.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

from core.models import User
from pos.models import Order, Zone, Table
from .helpers import require_roles, slugify_simple


# -------------------------
# Waiter UI (zones and tables loaded dynamically from the DB)
# -------------------------

@login_required
def waiter_tables(request):
    if not require_roles(request.user, [User.Role.WAITER, User.Role.ADMIN, User.Role.KITCHEN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    active_zones = Zone.objects.filter(is_active=True).prefetch_related("tables")

    # Build a name -> slug map for the active zones
    zone_name_to_slug = {z.name: z.slug for z in active_zones}

    # Open order per table (anything not DONE/CANCELED), newest first so the
    # first match per key wins.
    latest = {}
    rows = (
        Order.objects
        .filter(status__in=[Order.Status.NEW, Order.Status.PREP, Order.Status.READY])
        .order_by("-created_at")
        .values("zone", "table_number", "status", "is_paid", "created_at")
    )

    for r in rows:
        zslug = zone_name_to_slug.get(r["zone"], slugify_simple(r["zone"]))
        key = f"{zslug}:{r['table_number']}"
        if key not in latest:
            latest[key] = r

    zones = []
    total_tables = 0

    for z in active_zones:
        active_tables = z.tables.filter(is_active=True).order_by("number")
        tables = []

        for t in active_tables:
            key = f"{z.slug}:{t.number}"
            o = latest.get(key)
            tables.append({
                "n": t.number,
                "key": key,
                "status": o["status"] if o else "",
                "is_paid": bool(o and o["is_paid"]),
                "since": o["created_at"].isoformat() if o else "",
            })

        zones.append({"name": z.name, "slug": z.slug, "tables": tables})
        total_tables += len(tables)

    return render(request, "waiter_tables.html", {
        "zones": zones,
        "total_tables": total_tables,
    })


@login_required
def waiter_order(request, zone, table):
    if not require_roles(request.user, [User.Role.WAITER, User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    # Look up the zone by slug in the DB
    zone_obj = Zone.objects.filter(slug=zone, is_active=True).first()
    zone_name = zone_obj.name if zone_obj else zone

    return render(request, "waiter_order.html", {
        "zone": zone,
        "zone_name": zone_name,
        "table": table
    })
