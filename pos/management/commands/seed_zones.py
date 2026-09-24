"""
Command to migrate the hardcoded zones into the database.
Usage: python manage.py seed_zones
"""
from django.core.management.base import BaseCommand
from pos.models import Zone, Table, BusinessConfig


# Original zones from the hardcoded ZONE_DEFS
ZONE_DEFS = [
    ("Guaduas", 3),
    ("Kiosco", 6),
    ("Pericos", 5),
    ("Rotonda", 3),
    ("Afuera kiosco", 4),
    ("Hamacas Lorenza", 3),
    ("Al frente tienda", 6),
]


def slugify_simple(s: str) -> str:
    return (
        (s or "")
        .strip()
        .lower()
        .replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        .replace("ñ", "n")
        .replace(" ", "-")
    )


class Command(BaseCommand):
    help = "Crea las zonas y mesas iniciales en la BD (migra desde ZONE_DEFS hardcodeado)"

    def handle(self, *args, **options):
        # Create BusinessConfig if it doesn't exist
        config, created = BusinessConfig.objects.get_or_create(
            pk=1,
            defaults={
                "name": "Las Hamacas",
                "tip_type": BusinessConfig.TipType.FIXED,
                "tip_value": 6000,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ BusinessConfig creado: {config.name}"))
        else:
            self.stdout.write(f"ℹ️  BusinessConfig ya existe: {config.name}")

        # Create zones and tables
        for idx, (name, table_count) in enumerate(ZONE_DEFS):
            slug = slugify_simple(name)
            zone, created = Zone.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "order": idx}
            )
            action = "creada" if created else "ya existe"
            self.stdout.write(f"  Zona '{name}' ({slug}) — {action}")

            for n in range(1, table_count + 1):
                _, t_created = Table.objects.get_or_create(
                    zone=zone,
                    number=n,
                )
                if t_created:
                    self.stdout.write(f"    Mesa {n} — creada")

        total_zones = Zone.objects.count()
        total_tables = Table.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Seed completo: {total_zones} zonas, {total_tables} mesas"
        ))
