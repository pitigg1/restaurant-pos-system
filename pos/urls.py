# All routes for the pos app, grouped by role/feature.
from django.urls import path
from pos import views

urlpatterns = [
    path("", views.home, name="pos_home"),

    path("login/", views.login_view, name="pos_login"),
    path("logout/", views.logout_view, name="pos_logout"),

    # Waiter
    path("waiter/tables/", views.waiter_tables, name="waiter_tables"),
    path("waiter/order/<slug:zone>/<int:table>/", views.waiter_order, name="waiter_order"),

    # Kitchen
    path("kitchen/kds/", views.kitchen_kds, name="kitchen_kds"),

    # Admin (custom)
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/waiters/", views.admin_waiters, name="admin_waiters"),
    path("admin/waiters/<int:user_id>/", views.admin_waiter_detail, name="admin_waiter_detail"),
    path("admin/menu/", views.admin_menu, name="admin_menu"),
    path("admin/orders/", views.admin_orders, name="admin_orders"),
    path("admin/orders/<int:order_id>/", views.admin_order_detail, name="admin_order_detail"),
    path("admin/orders/<int:order_id>/update-items/", views.admin_order_update_items, name="admin_order_update_items"),

    # Menu / orders APIs (waiter/kitchen/admin)
    path("api/menu/", views.api_menu, name="api_menu"),
    path("api/orders/active/<slug:zone>/<int:table>/", views.api_active_table_order, name="api_active_table_order"),
    path("api/orders/create/", views.api_create_order, name="api_create_order"),
    path("api/orders/<int:order_id>/edit/", views.api_edit_order, name="api_edit_order"),
    path("api/orders/<int:order_id>/cancel/", views.api_cancel_order, name="api_cancel_order"),
    path("api/orders/<int:order_id>/status/", views.api_change_order_status, name="api_change_order_status"),
    path("api/orders/<int:order_id>/finish/", views.api_finish_order, name="api_finish_order"),

    # Kitchen API
    path("api/kitchen/orders/", views.kitchen_orders_api, name="kitchen_orders_api"),

    # Admin analytics API
    path("api/admin/analytics/", views.admin_analytics, name="admin_analytics"),
    path("api/admin/order/<int:order_id>/", views.api_admin_order_detail, name="api_admin_order_detail"),

    path("admin/users/", views.admin_users, name="admin_users"),
    path("admin/users/<int:user_id>/", views.admin_user_edit, name="admin_user_edit"),
    path("admin/users/<int:user_id>/delete/", views.admin_user_delete, name="admin_user_delete"),

    # Payment (waiter/admin)
    path("api/orders/<int:order_id>/pay/", views.api_pay_order, name="api_pay_order"),

    # Admin accounts (cash reports)
    path("admin/accounts/", views.admin_accounts, name="admin_accounts"),

    path("admin/qrs/", views.admin_qrs, name="admin_qrs"),
    path("admin/qrs/regenerate/", views.admin_regenerate_qrs, name="admin_regenerate_qrs"),
    path("admin/qrs/png/", views.admin_qr_png, name="admin_qr_png"),

    path("admin/config/", views.admin_config, name="admin_config"),
]
