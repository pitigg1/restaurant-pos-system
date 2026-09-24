"""
Admin views: dashboard, waiters, menu, orders, users, cash accounts, QR codes.
"""
from io import BytesIO
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views.decorators.http import require_GET

import qrcode

from core.models import User
from pos.models import MenuItem, MenuCategory, Order, OrderItem, OrderEvent, BusinessConfig, Zone, Table
from pos.forms import AdminUserCreateForm, AdminUserEditForm, AdminUserPasswordForm
from pos.utils_qr import build_base_url, generate_staff_qrs
from .helpers import (
    require_roles, _admin_only, _parse_period, _order_total,
    _get_local_ip, _ws_send_table_status,
)


# -------------------------
# Dashboard
# -------------------------

@login_required
def admin_dashboard(request):
    if not require_roles(request.user, [User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    period, start, end = _parse_period(request)

    orders_qs = (
        Order.objects
        .exclude(status=Order.Status.CANCELED)
        .select_related("waiter")
        .prefetch_related("items__menu_item")
        .order_by("-created_at")
        .filter(created_at__date__gte=start, created_at__date__lte=end)
    )

    paid_qs = orders_qs.filter(is_paid=True)

    total_sold = Decimal("0.00")
    by_method = {
        "CASH": Decimal("0.00"),
        "NEQUI": Decimal("0.00"),
        "TRANSFER": Decimal("0.00"),
        "UNKNOWN": Decimal("0.00"),
    }

    for o in paid_qs:
        tot = o.total_amount()
        total_sold += tot

        m = (o.payment_method or "").strip().upper()
        if m not in by_method:
            m = "UNKNOWN"
        by_method[m] += tot

    tips_total = paid_qs.aggregate(s=Sum("tip_amount"))["s"] or 0

    tips_by_waiter = (
        paid_qs.filter(tip_amount__gt=0)
        .values("waiter__username")
        .annotate(total=Sum("tip_amount"))
        .order_by("-total")
    )

    recent_orders = orders_qs[:10]
    orders_count = orders_qs.count()
    avg_ticket = (total_sold / orders_count) if orders_count > 0 else Decimal("0.00")

    return render(request, "admin_dashboard.html", {
        "orders_count": orders_count,
        "total_amount": total_sold,
        "avg_ticket": avg_ticket,
        "by_method": by_method,
        "recent_orders": recent_orders,
        "period": period,
        "start": start,
        "end": end,
        "tips_total": tips_total,
        "tips_by_waiter": tips_by_waiter,
    })


# -------------------------
# Waiters
# -------------------------

@login_required
def admin_waiters(request):
    gate = _admin_only(request)
    if gate:
        return gate

    period, start, end = _parse_period(request)

    orders_qs = (
        Order.objects
        .exclude(status=Order.Status.CANCELED)
        .select_related("waiter")
        .prefetch_related("items__menu_item")
        .order_by("-created_at")
        .filter(created_at__date__gte=start, created_at__date__lte=end)
    )

    waiters = User.objects.filter(role=User.Role.WAITER).order_by("username")

    stats = {}
    for w in waiters:
        stats[w.id] = {
            "waiter": w,
            "orders_count": 0,
            "total_amount": Decimal("0.00"),
            "paid_count": 0,
            "paid_total": Decimal("0.00"),
            "tips_total": Decimal("0.00"),
        }

    for o in orders_qs:
        if not o.waiter_id or o.waiter_id not in stats:
            continue

        tot = Decimal(str(_order_total(o)))

        stats[o.waiter_id]["orders_count"] += 1
        stats[o.waiter_id]["total_amount"] += tot

        if o.is_paid:
            stats[o.waiter_id]["paid_count"] += 1
            stats[o.waiter_id]["paid_total"] += tot
            stats[o.waiter_id]["tips_total"] += Decimal(str(getattr(o, "tip_amount", 0) or 0))

    rows = [stats[w.id] for w in waiters]

    return render(request, "admin_waiters.html", {
        "rows": rows,
        "period": period,
        "start": start,
        "end": end,
    })


@login_required
def admin_waiter_detail(request, user_id):
    gate = _admin_only(request)
    if gate:
        return gate

    waiter = get_object_or_404(User, id=user_id)
    period, start, end = _parse_period(request)

    orders_qs = (
        Order.objects
        .filter(waiter_id=user_id, created_at__date__gte=start, created_at__date__lte=end)
        .exclude(status=Order.Status.CANCELED)
        .prefetch_related("items__menu_item")
        .order_by("-created_at")
    )

    orders_list = list(orders_qs[:200])

    count = orders_qs.count()
    total = sum(_order_total(o) for o in orders_list)
    avg = (total / len(orders_list)) if orders_list else 0.0

    return render(request, "admin_waiter_detail.html", {
        "waiter": waiter,
        "period": period, "start": start, "end": end,
        "orders": orders_list,
        "orders_count": count,
        "total_amount": total,
        "avg_ticket": avg,
    })


# -------------------------
# Menu
# -------------------------

@login_required
def admin_menu(request):
    gate = _admin_only(request)
    if gate:
        return gate

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "create_category":
            cat_name = (request.POST.get("cat_name") or "").strip()
            if cat_name:
                MenuCategory.objects.create(name=cat_name)
            return redirect("admin_menu")

        if action == "delete_category":
            cat_id = request.POST.get("cat_id")
            if cat_id and cat_id.isdigit():
                MenuCategory.objects.filter(id=int(cat_id)).delete()
            return redirect("admin_menu")

        if action == "bulk_delete":
            ids = request.POST.getlist("ids[]")
            valid_ids = [int(i) for i in ids if i.isdigit()]
            if valid_ids:
                MenuItem.objects.filter(id__in=valid_ids).delete()
            return redirect("admin_menu")

        payload = request.POST
        item_id = payload.get("id")
        name = (payload.get("name") or "").strip()
        price = payload.get("price")
        available = payload.get("available") == "on"
        cat_id = payload.get("category_id")

        category_id = int(cat_id) if cat_id and cat_id.isdigit() else None

        if name and price:
            if item_id:
                m = get_object_or_404(MenuItem, id=int(item_id))
                m.name = name
                m.price = price
                m.available = available
                m.category_id = category_id
                m.save()
            else:
                MenuItem.objects.create(
                    name=name, price=price, available=available, category_id=category_id
                )

        return redirect("admin_menu")

    categories = MenuCategory.objects.filter(is_active=True).order_by("order", "name")
    items = MenuItem.objects.select_related("category").order_by("-available", "category__order", "name")
    return render(request, "admin_menu.html", {"items": items, "categories": categories})


# -------------------------
# Analytics API
# -------------------------

@login_required
def admin_analytics(request):
    if not require_roles(request.user, [User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    today = timezone.localdate()
    period, start_d, end_d = _parse_period(request)

    orders = (
        Order.objects
        .exclude(status=Order.Status.CANCELED)
        .filter(created_at__date__gte=start_d, created_at__date__lte=end_d)
        .prefetch_related("items__menu_item")
    )

    totals_by_day = {}
    for o in orders:
        d = o.created_at.date()
        if hasattr(o, "total_amount"):
            val = o.total_amount()
            totals_by_day[d] = totals_by_day.get(d, Decimal("0.00")) + val
        else:
            totals_by_day[d] = totals_by_day.get(d, Decimal("0.00")) + Decimal(str(_order_total(o)))

    labels, totals = [], []
    dcur = start_d
    while dcur <= end_d:
        labels.append(dcur.strftime("%Y-%m-%d"))
        totals.append(float(totals_by_day.get(dcur, Decimal("0.00"))))
        dcur += timedelta(days=1)

    if not labels:
        labels = [today.strftime("%Y-%m-%d")]
        totals = [0.0]

    return JsonResponse({"labels": labels, "totals": totals})


# -------------------------
# Orders (Admin)
# -------------------------

@login_required
def admin_orders(request):
    gate = _admin_only(request)
    if gate:
        return gate

    period, start, end = _parse_period(request)
    q = (request.GET.get("q") or "").strip()
    tip_filter = (request.GET.get("tip") or "").strip()

    orders = (
        Order.objects
        .filter(created_at__date__gte=start, created_at__date__lte=end)
        .exclude(status=Order.Status.CANCELED)
        .select_related("waiter")
        .prefetch_related("items__menu_item")
        .order_by("-created_at")
    )

    if q:
        orders = orders.filter(
            Q(waiter__username__icontains=q) |
            Q(zone__icontains=q) |
            Q(table_number__icontains=q) |
            Q(status__icontains=q)
        )

    if tip_filter == "1":
        orders = orders.filter(tip_amount__gt=0)
    elif tip_filter == "0":
        orders = orders.filter(tip_amount=0)

    rows = []
    for o in orders[:200]:
        rows.append({
            "order": o,
            "total": _order_total(o),
            "count_items": sum(i.quantity for i in o.items.all()),
            "is_paid": o.is_paid,
            "payment_method": o.payment_method,
            "has_tip": getattr(o, "has_tip", False),
            "tip_amount": getattr(o, "tip_amount", 0),
        })

    return render(request, "admin_orders.html", {
        "period": period, "start": start, "end": end,
        "q": q,
        "tip": tip_filter,
        "rows": rows,
    })


@login_required
def admin_order_detail(request, order_id):
    gate = _admin_only(request)
    if gate:
        return gate

    period, start, end = _parse_period(request)
    q = (request.GET.get("q") or "").strip()

    order = get_object_or_404(
        Order.objects.select_related("waiter").prefetch_related("items__menu_item"),
        id=order_id
    )

    menu = MenuItem.objects.all().order_by("-available", "name")

    qty_map = {it.menu_item_id: int(it.quantity) for it in order.items.all() if it.menu_item_id}

    menu_rows = [{"item": m, "qty": qty_map.get(m.id, 0)} for m in menu]

    total = _order_total(order)

    return render(request, "admin_order_detail.html", {
        "order": order,
        "menu_rows": menu_rows,
        "total": total,
        "period": period,
        "start": start,
        "end": end,
        "q": q,
    })


@login_required
def admin_order_update_items(request, order_id):
    gate = _admin_only(request)
    if gate:
        return gate

    order = get_object_or_404(Order, id=order_id)

    if request.method != "POST":
        return redirect("admin_order_detail", order_id=order.id)

    existing = {it.menu_item_id: it for it in order.items.all()}
    changed = False

    for k, v in request.POST.items():
        if not k.startswith("item_"):
            continue

        try:
            menu_id = int(k.split("_", 1)[1])
            qty = int((v or "0").strip())
        except Exception:
            continue

        if qty < 0:
            qty = 0

        if qty == 0:
            if menu_id in existing:
                existing[menu_id].delete()
                changed = True
            continue

        if menu_id in existing:
            if existing[menu_id].quantity != qty:
                existing[menu_id].quantity = qty
                existing[menu_id].save(update_fields=["quantity"])
                changed = True
        else:
            OrderItem.objects.create(order=order, menu_item_id=menu_id, quantity=qty)
            changed = True

    if changed:
        try:
            OrderEvent.objects.create(order=order, event="edited", user=request.user)
        except Exception:
            pass
        _ws_send_table_status(order)

    params = {}
    for key in ["period", "start", "end", "q"]:
        val = (request.POST.get(key) or "").strip()
        if val:
            params[key] = val

    url = reverse("admin_order_detail", kwargs={"order_id": order.id})
    if params:
        url = f"{url}?{urlencode(params)}"

    return redirect(url)


# -------------------------
# Users
# -------------------------

@login_required
def admin_users(request):
    gate = _admin_only(request)
    if gate:
        return gate

    q = (request.GET.get("q") or "").strip()
    role = (request.GET.get("role") or "").strip()

    users = User.objects.all().order_by("username")
    if q:
        users = users.filter(username__icontains=q)
    if role:
        users = users.filter(role=role)

    if request.method == "POST":
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario creado.")
            return redirect("admin_users")
    else:
        form = AdminUserCreateForm(initial={"is_active": True, "role": User.Role.WAITER})

    return render(request, "admin_users.html", {
        "users": users[:200],
        "q": q,
        "role_filter": role,
        "form": form,
    })


@login_required
def admin_user_edit(request, user_id):
    gate = _admin_only(request)
    if gate:
        return gate

    u = get_object_or_404(User, id=user_id)
    is_self = (request.user.id == u.id)

    if request.method == "POST":
        action = request.POST.get("action") or ""

        if action == "save_profile":
            form = AdminUserEditForm(request.POST, instance=u)
            pwd_form = AdminUserPasswordForm(target_role=u.role)
            if form.is_valid():
                form.save()
                messages.success(request, "Usuario actualizado.")
                return redirect("admin_user_edit", user_id=u.id)

        elif action == "reset_password":
            form = AdminUserEditForm(instance=u)
            pwd_form = AdminUserPasswordForm(request.POST, target_role=u.role)
            if pwd_form.is_valid():
                u.set_password(pwd_form.cleaned_data["password1"])
                u.save()
                messages.success(request, "Contraseña actualizada.")
                return redirect("admin_user_edit", user_id=u.id)

        else:
            form = AdminUserEditForm(instance=u)
            pwd_form = AdminUserPasswordForm(target_role=u.role)

    else:
        form = AdminUserEditForm(instance=u)
        pwd_form = AdminUserPasswordForm(target_role=u.role)

    return render(request, "admin_user_edit.html", {
        "uobj": u,
        "form": form,
        "pwd_form": pwd_form,
        "is_self": is_self,
    })


@login_required
def admin_user_delete(request, user_id):
    gate = _admin_only(request)
    if gate:
        return gate

    user_to_delete = get_object_or_404(User, id=user_id)

    if user_to_delete.id == request.user.id:
        messages.error(request, "No puedes eliminar tu propio usuario.")
        return redirect("admin_users")

    if user_to_delete.is_superuser:
        messages.error(request, "No se puede eliminar un superusuario desde el panel.")
        return redirect("admin_users")

    if getattr(user_to_delete, "role", None) == User.Role.ADMIN:
        admins_count = User.objects.filter(role=User.Role.ADMIN).count()
        if admins_count <= 1:
            messages.error(request, "No puedes eliminar el último administrador.")
            return redirect("admin_users")

    if request.method == "POST":
        username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f"Usuario '{username}' eliminado.")
        return redirect("admin_users")

    return render(request, "admin_user_delete_confirm.html", {
        "u": user_to_delete
    })


# -------------------------
# Cash accounts (payment totals report)
# -------------------------

@login_required
def admin_accounts(request):
    gate = _admin_only(request)
    if gate:
        return gate

    period, start, end = _parse_period(request)

    paid_orders = (
        Order.objects
        .filter(is_paid=True, created_at__date__gte=start, created_at__date__lte=end)
        .exclude(status=Order.Status.CANCELED)
        .prefetch_related("items__menu_item")
    )

    totals = {"CASH": 0.0, "NEQUI": 0.0, "TRANSFER": 0.0}
    count = {"CASH": 0, "NEQUI": 0, "TRANSFER": 0}

    for o in paid_orders:
        m = (o.payment_method or "").upper()
        if m in totals:
            totals[m] += _order_total(o)
            count[m] += 1

    grand_total = sum(totals.values())

    return render(request, "admin_accounts.html", {
        "period": period, "start": start, "end": end,
        "totals": totals,
        "count": count,
        "grand_total": grand_total,
    })


# -------------------------
# QR
# -------------------------

@login_required
def admin_qrs(request):
    if not require_roles(request.user, [User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    qr_port = 8000
    ip = _get_local_ip()
    base_url = f"http://{ip}:{qr_port}"

    qr_urls = {
        "waiter": base_url + reverse("waiter_tables"),
        "kitchen": base_url + reverse("kitchen_kds"),
        "admin": base_url + reverse("admin_dashboard"),
    }

    return render(request, "admin_qrs.html", {
        "base_url": base_url,
        "qr_urls": qr_urls,
    })


@login_required
def admin_regenerate_qrs(request):
    if not require_roles(request.user, [User.Role.ADMIN]):
        messages.error(request, "No autorizado.")
        return redirect("admin_dashboard")

    base_url = build_base_url(request=request)
    generate_staff_qrs(base_url)

    messages.success(request, f"✅ QRs actualizados para: {base_url}")
    return redirect("admin_dashboard")


@login_required
@require_GET
def admin_qr_png(request):
    """
    /pos/admin/qrs/png/?url=http://IP:8000/pos/waiter/tables/
    Returns a PNG with a QR code for that url.
    """
    if not require_roles(request.user, [User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    url = (request.GET.get("url") or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return JsonResponse({"detail": "URL inválida"}, status=400)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    resp = HttpResponse(buf.getvalue(), content_type="image/png")
    resp["Cache-Control"] = "no-store"
    return resp


# -------------------------
# Business config
# -------------------------

@login_required
def admin_config(request):
    if not require_roles(request.user, [User.Role.ADMIN]):
        return JsonResponse({"detail": "No autorizado"}, status=403)

    config = BusinessConfig.get_config()

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "save_business":
            name = request.POST.get("name", "").strip()
            if name:
                config.name = name
            config.tip_type = request.POST.get("tip_type", config.tip_type)
            tip_val = request.POST.get("tip_value", "").strip()
            if tip_val:
                try:
                    config.tip_value = Decimal(tip_val)
                except Exception:
                    pass
            if "logo" in request.FILES:
                config.logo = request.FILES["logo"]
            config.save()
            messages.success(request, "Datos del negocio actualizados.")

        elif action == "save_payments":
            config.cash_label     = request.POST.get("cash_label", "Efectivo").strip() or "Efectivo"
            config.nequi_label    = request.POST.get("nequi_label", "Nequi").strip() or "Nequi"
            config.transfer_label = request.POST.get("transfer_label", "Transferencia").strip() or "Transferencia"
            config.save()
            messages.success(request, "Métodos de pago actualizados.")

        elif action == "save_zone":
            from django.utils.text import slugify
            zone_id     = request.POST.get("zone_id", "").strip()
            zone_name   = request.POST.get("zone_name", "").strip()
            table_count = max(0, int(request.POST.get("table_count", 0) or 0))

            if zone_name:
                slug = slugify(zone_name)
                if zone_id:
                    zone = get_object_or_404(Zone, pk=zone_id)
                    zone.name = zone_name
                    zone.slug = slug
                    zone.save()
                else:
                    zone, _ = Zone.objects.get_or_create(slug=slug, defaults={"name": zone_name})
                    zone.name = zone_name
                    zone.save()

                # Make sure tables 1..table_count exist
                for n in range(1, table_count + 1):
                    Table.objects.get_or_create(zone=zone, number=n, defaults={"is_active": True})
                # Deactivate any extra tables
                zone.tables.filter(number__gt=table_count).update(is_active=False)
                zone.tables.filter(number__lte=table_count).update(is_active=True)

                messages.success(request, f"Área '{zone_name}' guardada.")

        elif action == "delete_zone":
            zone_id = request.POST.get("zone_id", "").strip()
            if zone_id:
                zone = get_object_or_404(Zone, pk=zone_id)
                zone.delete()
                messages.success(request, "Área eliminada.")

        return redirect("admin_config")

    zones = Zone.objects.prefetch_related("tables").order_by("order", "name")
    zone_data = [
        {"zone": z, "table_count": z.tables.filter(is_active=True).count()}
        for z in zones
    ]

    return render(request, "admin_config.html", {
        "config": config,
        "zone_data": zone_data,
    })
