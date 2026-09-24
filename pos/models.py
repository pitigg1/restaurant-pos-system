from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


# =============================================
# Business config
# =============================================

class BusinessConfig(models.Model):
    """General restaurant settings. Only one row should ever exist."""

    name = models.CharField("Nombre del negocio", max_length=150, default="Mi Restaurante")
    nit = models.CharField("NIT / ID fiscal", max_length=50, blank=True, default="")
    address = models.CharField("Dirección", max_length=250, blank=True, default="")
    phone = models.CharField("Teléfono", max_length=30, blank=True, default="")
    logo = models.ImageField("Logo", upload_to="business/", blank=True, null=True)

    class TipType(models.TextChoices):
        NONE = "NONE", "Sin propina"
        FIXED = "FIXED", "Valor fijo"
        PERCENT = "PERCENT", "Porcentaje"

    tip_type = models.CharField(
        "Tipo de propina",
        max_length=10,
        choices=TipType.choices,
        default=TipType.FIXED,
    )
    tip_value = models.DecimalField(
        "Valor de propina",
        max_digits=10,
        decimal_places=2,
        default=6000,
        help_text="Valor fijo en pesos o porcentaje (ej: 10 = 10%)",
    )

    # Custom display labels for payment methods
    cash_label     = models.CharField("Nombre Efectivo",       max_length=40, default="Efectivo")
    nequi_label    = models.CharField("Nombre Nequi",          max_length=40, default="Nequi")
    transfer_label = models.CharField("Nombre Transferencia",  max_length=40, default="Transferencia")

    class Meta:
        verbose_name = "Configuración del negocio"
        verbose_name_plural = "Configuración del negocio"

    def __str__(self):
        return self.name

    @staticmethod
    def get_config():
        """Gets the config (creates a default one if it doesn't exist)."""
        config, _ = BusinessConfig.objects.get_or_create(pk=1)
        return config


# =============================================
# Zones and tables
# =============================================

class Zone(models.Model):
    """Restaurant zone (e.g. Kiosco, Terraza)."""

    name = models.CharField("Nombre", max_length=100, unique=True)
    slug = models.SlugField("Slug", max_length=100, unique=True)
    order = models.PositiveIntegerField("Orden", default=0, help_text="Para ordenar las zonas")
    is_active = models.BooleanField("Activa", default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Zona"
        verbose_name_plural = "Zonas"

    def __str__(self):
        return self.name


class Table(models.Model):
    """A table within a zone."""

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="tables")
    number = models.PositiveIntegerField("Número de mesa")
    is_active = models.BooleanField("Activa", default=True)

    class Meta:
        unique_together = ("zone", "number")
        ordering = ["zone", "number"]
        verbose_name = "Mesa"
        verbose_name_plural = "Mesas"

    def __str__(self):
        return f"{self.zone.name} - Mesa {self.number}"


# =============================================
# Menu categories
# =============================================

class MenuCategory(models.Model):
    """Menu category (e.g. Bebidas, Platos fuertes)."""

    name = models.CharField("Nombre", max_length=100)
    order = models.PositiveIntegerField("Orden", default=0)
    is_active = models.BooleanField("Activa", default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Categoría de menú"
        verbose_name_plural = "Categorías de menú"

    def __str__(self):
        return self.name


# =============================================
# Menu items
# =============================================

class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
        verbose_name="Categoría",
    )

    class Meta:
        ordering = ["-available", "category__order", "name"]

    def __str__(self):
        return self.name


# =============================================
# Orders
# =============================================

class Order(models.Model):

    # ----------------------
    # ORDER STATUSES
    # ----------------------
    class Status(models.TextChoices):
        NEW = "NEW", "Nuevo"
        PREP = "PREP", "En preparación"
        READY = "READY", "Listo"
        DONE = "DONE", "Finalizado"
        CANCELED = "CANCELED", "Cancelado"

    # ----------------------
    # PAYMENT METHODS
    # ----------------------
    class PayMethod(models.TextChoices):
        CASH = "CASH", "Efectivo"
        NEQUI = "NEQUI", "Nequi"
        TRANSFER = "TRANSFER", "Transferencia"

    # ----------------------
    # ORDER DATA
    # ----------------------
    zone = models.CharField(max_length=60)      # e.g. "Kiosco"
    table_number = models.IntegerField()        # e.g. 1..N within that zone

    waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW
    )

    # ----------------------
    # PAYMENT TRACKING
    # ----------------------
    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(
        max_length=20,
        choices=PayMethod.choices,
        blank=True,
        default=""
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="paid_orders"
    )

    # ----------------------
    # DATES
    # ----------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tip_amount = models.PositiveIntegerField(default=0)   # 0 if no tip was added
    has_tip = models.BooleanField(default=False)

    # ----------------------
    # ORDER TOTAL
    # ----------------------
    def total_amount(self):
        return sum((item.subtotal() for item in self.items.all()), Decimal("0.00"))

    def __str__(self):
        return f"Pedido #{self.id} - {self.zone} Mesa {self.table_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name="items",
        on_delete=models.CASCADE
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)

    def subtotal(self):
        if not self.menu_item:
            return Decimal("0.00")
        return (self.menu_item.price * self.quantity)

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"


class OrderEvent(models.Model):
    """
    Order event history:
    - created, edited, sent to kitchen, canceled, ready
    """
    order = models.ForeignKey(
        Order,
        related_name="events",
        on_delete=models.CASCADE
    )
    event = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"{self.event} - Pedido #{self.order.id}"
