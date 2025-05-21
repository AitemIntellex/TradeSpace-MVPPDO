# TradeSpace_v5/brain/urls.py
from django.urls import path
from . import views
from .api import get_data


urlpatterns = [
    path("thoughts/", views.thought_list, name="thought_list"),
    path("api/data", get_data, name="get_data"),
    path("pachart/", views.price_action_chart, name="price_action_chart"),
]
