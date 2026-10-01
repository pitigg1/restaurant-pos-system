"""
Tests for the POS app.
Covers models, views, APIs and business logic.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from core.models import User
from pos.models import (
    BusinessConfig, Zone, Table, MenuCategory, MenuItem,
    Order, OrderItem, OrderEvent
)


# =============================================================================
# MODEL TESTS
# =============================================================================

class BusinessConfigModelTest(TestCase):
    """Tests for the BusinessConfig model."""

    def test_get_config_creates_default(self):
        """get_config() should create the default config if none exists."""
        config = BusinessConfig.get_config()
        self.assertIsNotNone(config)
        self.assertEqual(config.pk, 1)

    def test_get_config_returns_existing(self):
        """get_config() should return the existing config."""
        BusinessConfig.objects.create(
            pk=1,
            name="Test Restaurant",
            tip_type=BusinessConfig.TipType.PERCENT,
            tip_value=10
        )
        config = BusinessConfig.get_config()
        self.assertEqual(config.name, "Test Restaurant")
        self.assertEqual(config.tip_type, BusinessConfig.TipType.PERCENT)


class ZoneAndTableModelTest(TestCase):
    """Tests for Zone and Table."""

    def setUp(self):
        self.zone = Zone.objects.create(
            name="Terraza",
            slug="terraza",
            order=1,
            is_active=True
        )

    def test_zone_creation(self):
        """Should create a zone correctly."""
        self.assertEqual(self.zone.name, "Terraza")
        self.assertEqual(str(self.zone), "Terraza")

    def test_table_creation(self):
        """Should create a table correctly."""
        table = Table.objects.create(zone=self.zone, number=5)
        self.assertEqual(table.number, 5)
        self.assertEqual(str(table), "Terraza - Mesa 5")

    def test_table_unique_together(self):
        """Should not allow duplicate tables within the same zone."""
        Table.objects.create(zone=self.zone, number=1)
        with self.assertRaises(Exception):
            Table.objects.create(zone=self.zone, number=1)


class MenuModelTest(TestCase):
    """Tests for MenuCategory and MenuItem."""

    def setUp(self):
        self.category = MenuCategory.objects.create(
            name="Bebidas",
            order=1,
            is_active=True
        )

    def test_category_creation(self):
        """Should create a category correctly."""
        self.assertEqual(self.category.name, "Bebidas")
        self.assertEqual(str(self.category), "Bebidas")

    def test_menu_item_creation(self):
        """Should create a menu item correctly."""
        item = MenuItem.objects.create(
            name="Coca Cola",
            price=Decimal("5000.00"),
            category=self.category,
            available=True
        )
        self.assertEqual(item.name, "Coca Cola")
        self.assertEqual(item.price, Decimal("5000.00"))
        self.assertTrue(item.available)

    def test_menu_item_without_category(self):
        """Should allow items without a category."""
        item = MenuItem.objects.create(
            name="Producto sin categoría",
            price=Decimal("1000.00"),
            available=True
        )
        self.assertIsNone(item.category)


class OrderModelTest(TestCase):
    """Tests for Order, OrderItem and OrderEvent."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='mesero1',
            password='test123',
            role=User.Role.WAITER
        )
        self.zone = Zone.objects.create(name='Kiosco', slug='kiosco')
        self.table = Table.objects.create(zone=self.zone, number=1)
        self.category = MenuCategory.objects.create(name='Comida')
        self.item1 = MenuItem.objects.create(
            name='Hamburguesa',
            price=Decimal('12000.00'),
            category=self.category,
            available=True
        )
        self.item2 = MenuItem.objects.create(
            name='Papas',
            price=Decimal('5000.00'),
            category=self.category,
            available=True
        )

    def test_order_creation(self):
        """Should create an order correctly."""
        order = Order.objects.create(
            zone='kiosco',
            table_number=1,
            waiter=self.user,
            status=Order.Status.NEW
        )
        self.assertEqual(order.status, Order.Status.NEW)
        self.assertFalse(order.is_paid)
        self.assertIsNotNone(order.created_at)

    def test_order_total_calculation(self):
        """Should calculate the total correctly."""
        order = Order.objects.create(
            zone='kiosco',
            table_number=1,
            waiter=self.user
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item1,
            quantity=2
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item2,
            quantity=1
        )
        # 2 * 12000 + 1 * 5000 = 29000
        total = order.total_amount()
        self.assertEqual(total, Decimal('29000.00'))

    def test_order_item_subtotal(self):
        """Should calculate the item subtotal correctly."""
        order = Order.objects.create(
            zone='kiosco',
            table_number=1,
            waiter=self.user
        )
        order_item = OrderItem.objects.create(
            order=order,
            menu_item=self.item1,
            quantity=3
        )
        # 3 * 12000 = 36000
        self.assertEqual(order_item.subtotal(), Decimal('36000.00'))

    def test_order_payment(self):
        """Should mark an order as paid correctly."""
        order = Order.objects.create(
            zone='kiosco',
            table_number=1,
            waiter=self.user
        )
        order.is_paid = True
        order.payment_method = Order.PayMethod.CASH
        order.paid_at = timezone.now()
        order.paid_by = self.user
        order.save()

        self.assertTrue(order.is_paid)
        self.assertEqual(order.payment_method, Order.PayMethod.CASH)
        self.assertIsNotNone(order.paid_at)

    def test_order_with_tip(self):
        """Should handle tips correctly."""
        order = Order.objects.create(
            zone='kiosco',
            table_number=1,
            waiter=self.user,
            has_tip=True,
            tip_amount=6000
        )
        self.assertTrue(order.has_tip)
        self.assertEqual(order.tip_amount, 6000)


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

class AuthenticationTest(TestCase):
    """Tests for login and authentication."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='admin1',
            password='admin123',
            role=User.Role.ADMIN
        )

    def test_login_view_get(self):
        """Should render the login page."""
        response = self.client.get(reverse('pos_login'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        """Should allow login with correct credentials."""
        response = self.client.post(reverse('pos_login'), {
            'username': 'admin1',
            'password': 'admin123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect

    def test_login_failure(self):
        """Should reject login with incorrect credentials."""
        response = self.client.post(reverse('pos_login'), {
            'username': 'admin1',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # Back to login

    def test_logout(self):
        """Should log the user out correctly."""
        self.client.login(username='admin1', password='admin123')
        response = self.client.get(reverse('pos_logout'))
        self.assertEqual(response.status_code, 302)


# =============================================================================
# VIEW TESTS
# =============================================================================

class WaiterViewsTest(TestCase):
    """Tests for waiter views."""

    def setUp(self):
        self.client = Client()
        self.waiter = User.objects.create_user(
            username='mesero1',
            password='test123',
            role=User.Role.WAITER
        )
        self.zone = Zone.objects.create(name='Kiosco', slug='kiosco')
        self.table = Table.objects.create(zone=self.zone, number=1)
        self.client.login(username='mesero1', password='test123')

    def test_waiter_tables_view(self):
        """Should show the tables view for the waiter."""
        response = self.client.get(reverse('waiter_tables'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kiosco')

    def test_waiter_order_view(self):
        """Should show the order view for the waiter."""
        response = self.client.get(
            reverse('waiter_order', kwargs={'zone': 'kiosco', 'table': 1})
        )
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_access(self):
        """Should redirect to login when not authenticated."""
        self.client.logout()
        response = self.client.get(reverse('waiter_tables'))
        self.assertEqual(response.status_code, 302)  # Redirect to login


class KitchenViewsTest(TestCase):
    """Tests for kitchen views."""

    def setUp(self):
        self.client = Client()
        self.kitchen_user = User.objects.create_user(
            username='cocina1',
            password='test123',
            role=User.Role.KITCHEN
        )
        self.client.login(username='cocina1', password='test123')

    def test_kitchen_kds_view(self):
        """Should show the kitchen KDS view."""
        response = self.client.get(reverse('kitchen_kds'))
        self.assertEqual(response.status_code, 200)


# =============================================================================
# REST API TESTS
# =============================================================================

class MenuAPITest(TestCase):
    """Tests for the menu API."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='test',
            password='test123',
            role=User.Role.WAITER
        )
        self.client.login(username='test', password='test123')

        self.category = MenuCategory.objects.create(name='Bebidas')
        self.item1 = MenuItem.objects.create(
            name='Coca Cola',
            price=Decimal('5000.00'),
            category=self.category,
            available=True
        )
        self.item2 = MenuItem.objects.create(
            name='Pepsi',
            price=Decimal('5000.00'),
            category=self.category,
            available=False  # Not available
        )

    def test_api_menu_returns_only_available(self):
        """API should return only available items."""
        response = self.client.get(reverse('api_menu'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Coca Cola')

    def test_api_menu_requires_login(self):
        """API should require authentication."""
        self.client.logout()
        response = self.client.get(reverse('api_menu'))
        self.assertEqual(response.status_code, 302)  # Redirect to login


class OrderAPITest(TestCase):
    """Tests for the orders API."""

    def setUp(self):
        self.client = Client()
        self.waiter = User.objects.create_user(
            username='mesero1',
            password='test123',
            role=User.Role.WAITER
        )
        self.client.login(username='mesero1', password='test123')

        self.zone = Zone.objects.create(name='Kiosco', slug='kiosco')
        self.table = Table.objects.create(zone=self.zone, number=1)
        self.item = MenuItem.objects.create(
            name='Hamburguesa',
            price=Decimal('12000.00'),
            available=True
        )

    def test_create_order_api(self):
        """Should create an order via the API."""
        response = self.client.post(
            reverse('api_create_order'),
            data={
                'zone': 'kiosco',
                'table_number': 1,
                'items': [
                    {'menu_item_id': self.item.id, 'quantity': 2, 'notes': ''}
                ]
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('ok'))
        self.assertIn('order_id', data)

        # Verify it was created in the DB.
        order = Order.objects.get(id=data['order_id'])
        self.assertEqual(order.zone, 'Kiosco')
        self.assertEqual(order.table_number, 1)
        self.assertEqual(order.items.count(), 1)

    def test_create_order_validation(self):
        """Should validate data when creating an order."""
        # No items.
        response = self.client.post(
            reverse('api_create_order'),
            data={'zone': 'kiosco', 'table_number': 1, 'items': []},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_api_active_table_order(self):
        """Should return the active order for a table."""
        # Create order.
        order = Order.objects.create(
            zone='Kiosco',
            table_number=1,
            waiter=self.waiter,
            status=Order.Status.NEW
        )

        response = self.client.get(
            reverse('api_active_table_order', kwargs={'zone': 'kiosco', 'table': 1})
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['order']['id'], order.id)


class PaymentAPITest(TestCase):
    """Tests for the payment API."""

    def setUp(self):
        self.client = Client()
        self.waiter = User.objects.create_user(
            username='mesero1',
            password='test123',
            role=User.Role.WAITER
        )
        self.client.login(username='mesero1', password='test123')

        BusinessConfig.objects.create(
            pk=1,
            tip_type=BusinessConfig.TipType.FIXED,
            tip_value=5000
        )

        self.item = MenuItem.objects.create(
            name='Producto',
            price=Decimal('10000.00'),
            available=True
        )
        self.order = Order.objects.create(
            zone='kiosco',
            table_number=1,
            waiter=self.waiter,
            status=Order.Status.READY
        )
        OrderItem.objects.create(
            order=self.order,
            menu_item=self.item,
            quantity=2
        )

    def test_pay_order_api(self):
        """Should process payment correctly, applying a fixed tip."""
        response = self.client.post(
            reverse('api_pay_order', kwargs={'order_id': self.order.id}),
            data={
                'method': 'CASH',
                'add_tip': True
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('ok'))

        # Verify in the DB.
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.payment_method, Order.PayMethod.CASH)
        self.assertEqual(self.order.tip_amount, 5000)

    def test_pay_invalid_method(self):
        """Should reject an invalid payment method."""
        response = self.client.post(
            reverse('api_pay_order', kwargs={'order_id': self.order.id}),
            data={'payment_method': 'INVALID'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


# =============================================================================
# PERMISSION TESTS
# =============================================================================

class PermissionsTest(TestCase):
    """Tests for role-based access control."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin1',
            password='admin123',
            role=User.Role.ADMIN
        )
        self.waiter = User.objects.create_user(
            username='mesero1',
            password='mesero123',
            role=User.Role.WAITER
        )
        self.kitchen = User.objects.create_user(
            username='cocina1',
            password='cocina123',
            role=User.Role.KITCHEN
        )

    def test_admin_can_access_dashboard(self):
        """Admin should be able to access the dashboard."""
        self.client.login(username='admin1', password='admin123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_waiter_cannot_access_admin_dashboard(self):
        """A waiter should not be able to access the admin dashboard."""
        self.client.login(username='mesero1', password='mesero123')
        response = self.client.get(reverse('admin_dashboard'))
        # Should redirect or return 403.
        self.assertIn(response.status_code, [302, 403])


# =============================================================================
# TABLE LIFECYCLE: charge, then free the table
# =============================================================================

class TableLifecycleTest(TestCase):
    """Paying keeps the table occupied; the waiter frees it once the order is READY."""

    def setUp(self):
        from unittest.mock import patch
        # No receipt printer in tests
        patcher = patch("pos.views.api._print_receipt_usb")
        patcher.start()
        self.addCleanup(patcher.stop)

        self.client = Client()
        self.waiter = User.objects.create_user(username="mesero1", password="test123", role=User.Role.WAITER)
        self.cook = User.objects.create_user(username="cocina1", password="test123", role=User.Role.KITCHEN)
        self.item = MenuItem.objects.create(name="Arepa", price=Decimal("8000"), available=True)
        self.order = Order.objects.create(zone="Kiosco", table_number=1, waiter=self.waiter, status=Order.Status.NEW)
        OrderItem.objects.create(order=self.order, menu_item=self.item, quantity=1)

    def _set_status(self, status):
        self.client.login(username="cocina1", password="test123")
        return self.client.post(
            reverse("api_change_order_status", kwargs={"order_id": self.order.id}),
            data={"status": status}, content_type="application/json",
        )

    def _pay(self):
        self.client.login(username="mesero1", password="test123")
        return self.client.post(
            reverse("api_pay_order", kwargs={"order_id": self.order.id}),
            data={"method": "CASH"}, content_type="application/json",
        )

    def _finish(self):
        self.client.login(username="mesero1", password="test123")
        return self.client.post(
            reverse("api_finish_order", kwargs={"order_id": self.order.id}),
            data={}, content_type="application/json",
        )

    def test_pay_does_not_free_table(self):
        self.assertEqual(self._pay().status_code, 200)
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.status, Order.Status.NEW)

    def test_paid_order_can_still_be_cooked(self):
        self._pay()
        self.assertEqual(self._set_status("PREP").status_code, 200)
        self.assertEqual(self._set_status("READY").status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.READY)

    def test_free_table_requires_ready_and_paid(self):
        self._pay()
        self.assertEqual(self._finish().status_code, 400)  # not READY yet
        self._set_status("READY")
        self.assertEqual(self._finish().status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.DONE)

    def test_free_table_requires_payment(self):
        self._set_status("READY")
        self.assertEqual(self._finish().status_code, 400)

    def test_kitchen_cannot_go_back_to_prep(self):
        self._set_status("READY")
        self.assertEqual(self._set_status("PREP").status_code, 400)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.READY)

    def test_kitchen_board_hides_ready_orders(self):
        later = Order.objects.create(zone="Kiosco", table_number=2, waiter=self.waiter, status=Order.Status.PREP)
        self._set_status("READY")
        res = self.client.get(reverse("kitchen_orders_api"))
        ids = [o["id"] for o in res.json()]
        self.assertEqual(ids, [later.id])

    def test_kitchen_board_is_in_arrival_order(self):
        second = Order.objects.create(zone="Kiosco", table_number=2, waiter=self.waiter, status=Order.Status.PREP)
        self.client.login(username="cocina1", password="test123")
        ids = [o["id"] for o in self.client.get(reverse("kitchen_orders_api")).json()]
        self.assertEqual(ids, [self.order.id, second.id])


class TipTest(TestCase):
    """The waiter decides per charge whether the customer leaves the admin-configured tip."""

    def setUp(self):
        from unittest.mock import patch
        patcher = patch("pos.views.api._print_receipt_usb")
        patcher.start()
        self.addCleanup(patcher.stop)
        BusinessConfig.objects.create(pk=1, tip_type=BusinessConfig.TipType.PERCENT, tip_value=10)
        self.waiter = User.objects.create_user(username="mesero1", password="test123", role=User.Role.WAITER)
        self.client = Client()
        self.client.login(username="mesero1", password="test123")
        item = MenuItem.objects.create(name="Bandeja", price=Decimal("40500"), available=True)
        self.order = Order.objects.create(zone="Kiosco", table_number=1, waiter=self.waiter, status=Order.Status.READY)
        OrderItem.objects.create(order=self.order, menu_item=item, quantity=1)

    def _pay(self, add_tip):
        return self.client.post(
            reverse("api_pay_order", kwargs={"order_id": self.order.id}),
            data={"method": "CASH", "add_tip": add_tip}, content_type="application/json",
        )

    def test_percent_tip_when_customer_accepts(self):
        self.assertEqual(self._pay(True).status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.tip_amount, 4050)  # 10% of 40.500
        self.assertTrue(self.order.has_tip)

    def test_no_tip_when_customer_declines(self):
        self._pay(False)
        self.order.refresh_from_db()
        self.assertEqual(self.order.tip_amount, 0)
        self.assertFalse(self.order.has_tip)

    def test_order_page_exposes_tip_rules_and_active_order_tip(self):
        res = self.client.get(reverse("waiter_order", kwargs={"zone": "kiosco", "table": 1}))
        self.assertContains(res, 'id="tip-type"')
        self.assertContains(res, '"PERCENT"')
        self._pay(True)
        data = self.client.get(reverse("api_active_table_order", kwargs={"zone": "kiosco", "table": 1})).json()
        self.assertEqual(data["order"]["tip_amount"], 4050)


class AdminMenuTest(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_user(username="admin1", password="admin12345", role=User.Role.ADMIN)
        self.client.login(username="admin1", password="admin12345")
        self.cat = MenuCategory.objects.create(name="Bebidas")
        self.item = MenuItem.objects.create(name="Limonada", price=Decimal("5000"), available=True, category=self.cat)

    def test_toggle_available(self):
        url = reverse("admin_menu")
        self.client.post(url, {"action": "toggle_available", "id": self.item.id})
        self.item.refresh_from_db()
        self.assertFalse(self.item.available)
        self.client.post(url, {"action": "toggle_available", "id": self.item.id})
        self.item.refresh_from_db()
        self.assertTrue(self.item.available)

    def test_categories_reorder_and_new_go_last(self):
        url = reverse("admin_menu")
        self.client.post(url, {"action": "create_category", "cat_name": "Entradas"})
        names = lambda: list(MenuCategory.objects.order_by("order", "name").values_list("name", flat=True))
        self.assertEqual(names(), ["Bebidas", "Entradas"])
        entradas = MenuCategory.objects.get(name="Entradas")
        self.client.post(url, {"action": "move_category", "cat_id": entradas.id, "dir": "up"})
        self.assertEqual(names(), ["Entradas", "Bebidas"])
        # Already first: moving up again changes nothing
        self.client.post(url, {"action": "move_category", "cat_id": entradas.id, "dir": "up"})
        self.assertEqual(names(), ["Entradas", "Bebidas"])
        # The waiter's menu follows the same order
        MenuItem.objects.create(name="Empanada", price=Decimal("3000"), available=True, category=entradas)
        cats = [m["category"] for m in self.client.get("/pos/api/menu/").json()]
        self.assertEqual(cats, ["Entradas", "Bebidas"])

    def test_admin_pages_render(self):
        order = Order.objects.create(zone="Kiosco", table_number=1, waiter=User.objects.get(username="admin1"))
        OrderItem.objects.create(order=order, menu_item=self.item, quantity=2)
        waiter = User.objects.create_user(username="m1", password="1234", role=User.Role.WAITER)
        for name, kwargs in [
            ("admin_dashboard", {}), ("admin_menu", {}), ("admin_users", {}),
            ("admin_orders", {}), ("admin_order_detail", {"order_id": order.id}),
            ("admin_waiters", {}), ("admin_waiter_detail", {"user_id": waiter.id}),
            ("admin_user_edit", {"user_id": waiter.id}), ("admin_user_delete", {"user_id": waiter.id}),
            ("admin_qrs", {}), ("admin_config", {}), ("admin_accounts", {}),
        ]:
            res = self.client.get(reverse(name, kwargs=kwargs))
            self.assertEqual(res.status_code, 200, name)


class SalesAnalyticsTest(TestCase):
    """The sales chart groups by the restaurant's local day and only counts paid orders."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin1", password="admin12345", role=User.Role.ADMIN)
        self.client.login(username="admin1", password="admin12345")
        self.item = MenuItem.objects.create(name="Arepa", price=Decimal("10000"), available=True)

    def _order(self, local_dt, paid):
        o = Order.objects.create(zone="Kiosco", table_number=1, waiter=self.admin, is_paid=paid, payment_method="CASH" if paid else "")
        OrderItem.objects.create(order=o, menu_item=self.item, quantity=1)
        Order.objects.filter(id=o.id).update(created_at=local_dt)
        return o

    def test_late_night_order_counts_for_local_day(self):
        from datetime import datetime, time
        today = timezone.localdate()
        tz = timezone.get_current_timezone()
        # 22:30 in Bogotá is already the next day in UTC
        self._order(timezone.make_aware(datetime.combine(today, time(22, 30)), tz), paid=True)
        self._order(timezone.make_aware(datetime.combine(today, time(12, 0)), tz), paid=True)
        self._order(timezone.make_aware(datetime.combine(today, time(13, 0)), tz), paid=False)

        data = self.client.get(reverse("admin_analytics"), {"period": "today"}).json()
        self.assertEqual(data["labels"], [today.strftime("%Y-%m-%d")])
        self.assertEqual(data["totals"], [20000.0])
        self.assertEqual(data["summary"]["paid_total"], 20000.0)
        self.assertEqual(data["summary"]["orders_count"], 3)
        self.assertEqual(data["summary"]["by_method"]["CASH"], 20000.0)
