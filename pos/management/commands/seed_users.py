"""
Command to create sample users for the POS system.
Usage: python manage.py seed_users
"""
from django.core.management.base import BaseCommand
from core.models import User


# Sample users
USERS_DATA = [
    # Admins
    {
        "username": "admin",
        "password": "admin123",
        "role": User.Role.ADMIN,
        "first_name": "Admin",
        "last_name": "Principal",
        "email": "admin@hamacas.com",
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "username": "gerente",
        "password": "gerente123",
        "role": User.Role.ADMIN,
        "first_name": "María",
        "last_name": "Rodríguez",
        "email": "gerente@hamacas.com",
        "is_staff": True,
    },

    # Waiters
    {
        "username": "mesero1",
        "password": "mesero123",
        "role": User.Role.WAITER,
        "first_name": "Carlos",
        "last_name": "Gómez",
        "email": "carlos@hamacas.com",
    },
    {
        "username": "mesero2",
        "password": "mesero123",
        "role": User.Role.WAITER,
        "first_name": "Ana",
        "last_name": "Martínez",
        "email": "ana@hamacas.com",
    },
    {
        "username": "mesero3",
        "password": "mesero123",
        "role": User.Role.WAITER,
        "first_name": "Luis",
        "last_name": "Pérez",
        "email": "luis@hamacas.com",
    },
    {
        "username": "mesero4",
        "password": "mesero123",
        "role": User.Role.WAITER,
        "first_name": "Laura",
        "last_name": "Sánchez",
        "email": "laura@hamacas.com",
    },

    # Kitchen staff
    {
        "username": "cocina1",
        "password": "cocina123",
        "role": User.Role.KITCHEN,
        "first_name": "Pedro",
        "last_name": "Torres",
        "email": "pedro@hamacas.com",
    },
    {
        "username": "cocina2",
        "password": "cocina123",
        "role": User.Role.KITCHEN,
        "first_name": "Diana",
        "last_name": "López",
        "email": "diana@hamacas.com",
    },
    {
        "username": "chef",
        "password": "chef123",
        "role": User.Role.KITCHEN,
        "first_name": "Jorge",
        "last_name": "Ramírez",
        "email": "chef@hamacas.com",
    },
]


class Command(BaseCommand):
    help = "Crea usuarios de prueba para el sistema POS (admin, meseros, cocina)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Elimina todos los usuarios antes de crear los nuevos (CUIDADO)',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Actualiza usuarios existentes con los datos de prueba',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(
                self.style.WARNING("⚠️  ¡ADVERTENCIA! Eliminando usuarios existentes...")
            )
            # Superusers are kept so we don't lock ourselves out
            deleted = User.objects.filter(is_superuser=False).delete()
            self.stdout.write(
                self.style.SUCCESS(f"✅ Usuarios eliminados: {deleted[0]}")
            )

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for user_data in USERS_DATA:
            username = user_data.pop("username")
            password = user_data.pop("password")

            # Check whether the user already exists
            user_exists = User.objects.filter(username=username).exists()

            if user_exists:
                if options['update']:
                    # Update the existing user
                    user = User.objects.get(username=username)
                    user.set_password(password)
                    for key, value in user_data.items():
                        setattr(user, key, value)
                    user.save()

                    self.stdout.write(
                        f"  ⟳ Usuario '{username}' ({user_data['role']}) — actualizado"
                    )
                    updated_count += 1
                else:
                    # Skip existing user
                    self.stdout.write(
                        f"  ⊘ Usuario '{username}' — ya existe (usa --update para actualizar)"
                    )
                    skipped_count += 1
            else:
                # Create new user
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    **user_data
                )

                role_emoji = {
                    User.Role.ADMIN: "👑",
                    User.Role.WAITER: "🍽️",
                    User.Role.KITCHEN: "👨‍🍳"
                }.get(user_data['role'], "👤")

                self.stdout.write(
                    f"  {role_emoji} Usuario '{username}' ({user_data['role']}) — creado"
                )
                created_count += 1

        # Final summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(
            self.style.SUCCESS(f"✅ Seed completo:")
        )
        self.stdout.write(f"  • Creados: {created_count}")
        self.stdout.write(f"  • Actualizados: {updated_count}")
        self.stdout.write(f"  • Omitidos: {skipped_count}")
        self.stdout.write("="*60)

        # Sample credentials info
        self.stdout.write("\n📋 CREDENCIALES DE PRUEBA:")
        self.stdout.write("-"*60)
        self.stdout.write("👑 ADMIN:")
        self.stdout.write("   • admin / admin123")
        self.stdout.write("   • gerente / gerente123")
        self.stdout.write("\n🍽️  MESEROS:")
        self.stdout.write("   • mesero1 / mesero123")
        self.stdout.write("   • mesero2 / mesero123")
        self.stdout.write("   • mesero3 / mesero123")
        self.stdout.write("   • mesero4 / mesero123")
        self.stdout.write("\n👨‍🍳 COCINA:")
        self.stdout.write("   • cocina1 / cocina123")
        self.stdout.write("   • cocina2 / cocina123")
        self.stdout.write("   • chef / chef123")
        self.stdout.write("-"*60)
