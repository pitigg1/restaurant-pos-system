"""
Command to seed the menu with sample data.
Usage: python manage.py seed_menu
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from pos.models import MenuCategory, MenuItem


# Sample menu data
MENU_DATA = [
    {
        "category": "Bebidas Frías",
        "order": 1,
        "items": [
            {"name": "Coca Cola", "price": "5000.00"},
            {"name": "Coca Cola Zero", "price": "5000.00"},
            {"name": "Sprite", "price": "5000.00"},
            {"name": "Agua en Botella", "price": "3500.00"},
            {"name": "Jugo Natural Naranja", "price": "6500.00"},
            {"name": "Jugo Natural Mora", "price": "6500.00"},
            {"name": "Limonada Natural", "price": "5500.00"},
            {"name": "Cerveza Poker", "price": "4500.00"},
            {"name": "Cerveza Águila", "price": "4500.00"},
            {"name": "Cerveza Club Colombia", "price": "5500.00"},
        ]
    },
    {
        "category": "Bebidas Calientes",
        "order": 2,
        "items": [
            {"name": "Café Tinto", "price": "2500.00"},
            {"name": "Café con Leche", "price": "4000.00"},
            {"name": "Capuchino", "price": "5000.00"},
            {"name": "Chocolate Caliente", "price": "4500.00"},
            {"name": "Té", "price": "3000.00"},
            {"name": "Aromática", "price": "3000.00"},
        ]
    },
    {
        "category": "Entradas",
        "order": 3,
        "items": [
            {"name": "Empanadas (3 unidades)", "price": "8000.00"},
            {"name": "Patacones con Hogao", "price": "10000.00"},
            {"name": "Deditos de Queso", "price": "12000.00"},
            {"name": "Alitas BBQ (6 unidades)", "price": "18000.00"},
            {"name": "Nachos con Queso", "price": "15000.00"},
            {"name": "Tequeños (5 unidades)", "price": "12000.00"},
        ]
    },
    {
        "category": "Platos Principales",
        "order": 4,
        "items": [
            {"name": "Hamburguesa Clásica", "price": "18000.00"},
            {"name": "Hamburguesa Especial", "price": "22000.00"},
            {"name": "Perro Caliente", "price": "12000.00"},
            {"name": "Salchipapa", "price": "15000.00"},
            {"name": "Pechuga a la Plancha", "price": "25000.00"},
            {"name": "Carne Asada", "price": "28000.00"},
            {"name": "Mojarra Frita", "price": "32000.00"},
            {"name": "Bandeja Paisa", "price": "35000.00"},
            {"name": "Sancocho de Gallina", "price": "20000.00"},
            {"name": "Arroz con Pollo", "price": "22000.00"},
        ]
    },
    {
        "category": "Acompañamientos",
        "order": 5,
        "items": [
            {"name": "Papas Fritas", "price": "8000.00"},
            {"name": "Arroz Blanco", "price": "4000.00"},
            {"name": "Yuca Frita", "price": "7000.00"},
            {"name": "Ensalada Mixta", "price": "8000.00"},
            {"name": "Plátano Maduro", "price": "5000.00"},
            {"name": "Arepa con Queso", "price": "6000.00"},
        ]
    },
    {
        "category": "Postres",
        "order": 6,
        "items": [
            {"name": "Helado de Vainilla", "price": "6000.00"},
            {"name": "Helado de Chocolate", "price": "6000.00"},
            {"name": "Flan de Caramelo", "price": "7000.00"},
            {"name": "Brownie con Helado", "price": "10000.00"},
            {"name": "Tres Leches", "price": "8000.00"},
            {"name": "Cheesecake", "price": "9000.00"},
        ]
    },
    {
        "category": "Especiales del Día",
        "order": 7,
        "items": [
            {"name": "Combo Almuerzo Ejecutivo", "price": "18000.00"},
            {"name": "Combo Familiar (4 personas)", "price": "65000.00"},
            {"name": "Promoción 2x1 Hamburguesas", "price": "18000.00"},
        ]
    },
]


class Command(BaseCommand):
    help = "Crea categorías y items de menú de prueba en la BD"

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Elimina todas las categorías y items antes de crear los nuevos',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING("⚠️  Eliminando menú existente..."))
            MenuItem.objects.all().delete()
            MenuCategory.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("✅ Menú eliminado"))

        total_categories = 0
        total_items = 0

        for category_data in MENU_DATA:
            # Create category
            category, created = MenuCategory.objects.get_or_create(
                name=category_data["category"],
                defaults={
                    "order": category_data["order"],
                    "is_active": True
                }
            )

            action = "creada" if created else "ya existe"
            self.stdout.write(f"  📁 Categoría '{category.name}' — {action}")
            total_categories += 1

            # Create the category's items
            for item_data in category_data["items"]:
                item, item_created = MenuItem.objects.get_or_create(
                    name=item_data["name"],
                    defaults={
                        "price": Decimal(item_data["price"]),
                        "category": category,
                        "available": True
                    }
                )

                if item_created:
                    self.stdout.write(
                        f"    ✓ {item.name} - ${item.price:,.0f}"
                    )
                    total_items += 1
                else:
                    # Already exists: refresh its category and price
                    item.category = category
                    item.price = Decimal(item_data["price"])
                    item.save()
                    self.stdout.write(
                        f"    ⟳ {item.name} - ${item.price:,.0f} (actualizado)"
                    )
                    total_items += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Seed completo: {total_categories} categorías, {total_items} items"
            )
        )
