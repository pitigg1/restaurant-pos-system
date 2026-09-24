"""
Paquete de vistas pos.views.
Re-exporta todas las vistas para que urls.py funcione sin cambios.
"""

# Auth
from .auth import login_view, logout_view, home

# Waiter
from .waiter import waiter_tables, waiter_order

# Kitchen
from .kitchen import kitchen_kds, kitchen_orders_api

# Admin
from .admin_views import (
    admin_dashboard,
    admin_waiters,
    admin_waiter_detail,
    admin_menu,
    admin_analytics,
    admin_orders,
    admin_order_detail,
    admin_order_update_items,
    admin_users,
    admin_user_edit,
    admin_user_delete,
    admin_accounts,
    admin_qrs,
    admin_regenerate_qrs,
    admin_qr_png,
    admin_config,
)

# API
from .api import (
    api_menu,
    api_active_table_order,
    api_create_order,
    api_edit_order,
    api_cancel_order,
    api_change_order_status,
    api_finish_order,
    api_pay_order,
    api_admin_order_detail,
)
