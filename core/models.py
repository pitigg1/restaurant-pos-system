from django.contrib.auth.models import AbstractUser
from django.db import models

# Custom user model (see AUTH_USER_MODEL in settings.py), adds a role
# used across the app to route each user to their own screens/permissions.
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        WAITER = "WAITER", "Mesero"
        KITCHEN = "KITCHEN", "Cocina"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.WAITER)
