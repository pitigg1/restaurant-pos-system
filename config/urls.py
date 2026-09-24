# Root URL configuration for the whole project.
from django.contrib import admin
from django.urls import path, include
from pos.views import home

urlpatterns = [
    path("admin/", admin.site.urls),      # Django built-in admin
    path("", home, name="home"),          # Root redirect handled by pos
    path("pos/", include("pos.urls")),    # All app routes live under /pos/
]