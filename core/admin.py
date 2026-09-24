from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Extends Django's built-in UserAdmin to also expose the custom "role" field.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Rol", {"fields": ("role",)}),)
