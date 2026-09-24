from django.contrib import admin
from .models import (
    BusinessConfig, Zone, Table, MenuCategory,
    MenuItem, Order, OrderItem, OrderEvent,
)


# =============================================
# Business config
# =============================================

@admin.register(BusinessConfig)
class BusinessConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "nit", "phone", "tip_type", "tip_value")
    fieldsets = (
        ("Información del negocio", {
            "fields": ("name", "nit", "address", "phone", "logo"),
        }),
        ("Propina", {
            "fields": ("tip_type", "tip_value"),
        }),
    )

    def has_add_permission(self, request):
        # Only a single config row is allowed to exist.
        return not BusinessConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# =============================================
# Zones and tables
# =============================================

class TableInline(admin.TabularInline):
    model = Table
    extra = 1


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_active", "table_count")
    list_filter = ("is_active",)
    list_editable = ("order", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [TableInline]

    @admin.display(description="Mesas")
    def table_count(self, obj):
        return obj.tables.count()


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("id", "zone", "number", "is_active")
    list_filter = ("zone", "is_active")
    list_editable = ("is_active",)


# =============================================
# Menu categories and items
# =============================================

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active", "item_count")
    list_editable = ("order", "is_active")

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.items.count()


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "category", "available")
    list_filter = ("available", "category")
    search_fields = ("name",)
    ordering = ("name",)


# =============================================
# Orders
# =============================================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "table_number", "waiter", "status", "total_amount_display", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "table_number", "waiter__username")
    ordering = ("-created_at",)
    inlines = [OrderItemInline]

    @admin.display(description="Total")
    def total_amount_display(self, obj: Order):
        try:
            return obj.total_amount()
        except Exception:
            return 0


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "menu_item", "quantity")
    list_filter = ("menu_item",)
    search_fields = ("order__id", "menu_item__name")


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "event", "user", "created_at")
    list_filter = ("event", "created_at")
    search_fields = ("order__id", "event", "user__username")
    ordering = ("-created_at",)
