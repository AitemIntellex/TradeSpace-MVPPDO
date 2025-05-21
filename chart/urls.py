# TradeSpace_v5/chart/urls.py
from django.urls import path
from .views import ChartDataView

urlpatterns = [
    path("api/data/", ChartDataView.as_view(), name="chart-data"),
]
