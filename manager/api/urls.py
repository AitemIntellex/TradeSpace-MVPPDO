from django.urls import path
from manager.api.views import (
    FullMarketDataAPIView,
    MarketDataAPIView,
    IndicatorDataAPIView,
)


urlpatterns = [
    path("market-data/", MarketDataAPIView.as_view(), name="market-data"),
    path("indicator-data/", IndicatorDataAPIView.as_view(), name="indicator-data"),
    path(
        "full/market-data/",
        FullMarketDataAPIView.as_view(),
        name="full_market_data_api",
    ),
]
