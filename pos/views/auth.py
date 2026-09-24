"""
Authentication and home-redirect views.
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from core.models import User


# -------------------------
# Auth / Home
# -------------------------

def login_view(request):
    if request.method == "GET":
        return render(request, "login.html")

    username = request.POST.get("username", "")
    password = request.POST.get("password", "")
    user = authenticate(request, username=username, password=password)

    if user is None:
        return render(request, "login.html", {"error": "Credenciales incorrectas"})

    login(request, user)
    return redirect("pos_home")


@login_required
def logout_view(request):
    logout(request)
    return redirect("pos_login")


@login_required
def home(request):
    # Sends each logged-in user straight to their role's screen.
    u = request.user
    if u.is_superuser or getattr(u, "role", None) == User.Role.ADMIN:
        return redirect("admin_dashboard")
    if getattr(u, "role", None) == User.Role.KITCHEN:
        return redirect("kitchen_kds")
    return redirect("waiter_tables")
