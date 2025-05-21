# config/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("polygon.urls")),
    path("manager/", include("manager.api.urls")),
    path("brain/", include("brain.urls")),
    path("chart/", include("chart.urls")),
]
