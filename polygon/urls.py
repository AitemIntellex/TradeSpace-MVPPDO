# TradeSpace_v5/polygon/urls.py
from django.urls import path
from . import views
from .views import (
    fetch_economic_news,
    # market_analysis_view,
    update_database,
    technical_analysis_all_timeframes,
    analyze_with_ai_x3, analyze_with_historical_data
)


urlpatterns = [
    path("", views.home, name="home"),
    path(
        "fundamental-analysis/", views.fundamental_analysis, name="fundamental_analysis"
    ),
    path("ai-analysis/", views.ai_analysis, name="ai_analysis"),
    path("analyze_with_ai_x3/", views.analyze_with_ai_x3, name="analyze_with_ai_x3"),
    path(
        "recommendations/", views.recommendations_list, name="recommendations_list"
    ),  # Исправленный вызов функции
    path("test/", views.test_view, name="test"),
    path("profile-info/", views.test_view, name="profile-info"),
    path("statistics/", views.profit_loss_history, name="statistics"),
    path("trade-history/", views.trade_history, name="trade_history"),
    path("trade-calculator/", views.trade_calculator, name="trade_calculator"),
    path("trade/", views.trade, name="trade"),
    path("logout/", views.logout_view, name="logout"),
    path("get_symbol_data/", views.get_symbol_data, name="get_symbol_data"),
    path("get_historical_data/", views.get_historical_data, name="get_historical_data"),
    path("profit-history/", views.profit_loss_history, name="profit_history"),
    path("fetch-economic-news/", fetch_economic_news, name="fetch_economic_news"),
    # тех анализ
    path("technical-analysis/", views.technical_analysis, name="technical_analysis"),
    path(
        "technical-analysis/general/",
        views.technical_analysis_general,
        name="technical_analysis_general",
    ),
    path(
        "ts/all-tf/",
        views.technical_analysis_all_timeframes,
        name="technical_analysis_all_timeframes",
    ),
    path(
        "technical-analysis/indicators/",
        views.technical_analysis_indicators,
        name="technical_analysis_indicators",
    ),
    path(
        "technical-analysis/strategies/",
        views.technical_analysis_strategies,
        name="technical_analysis_strategies",
    ),
    path(
        "technical-analysis/tas/1",
        views.technical_analysis_tas,
        name="technical_analysis_tas",
    ),
    path(
        "technical-analysis/tas/2",
        views.technical_analysis_tass,
        name="technical_analysis_tass",
    ),
    path(
        "technical-analysis/tas/3",
        views.focused_technical_analysis,
        name="focused_technical_analysis",
    ),
    path(
        "technical-analysis/strategies/smc/",
        views.technical_analysis_smc,
        name="technical_analysis_smc",
    ),
    path(
        "technical-analysis/strategies/ict/",
        views.technical_analysis_ict,
        name="technical_analysis_ict",
    ),
    path(
        "technical-analysis/strategies/snr/",
        views.technical_analysis_snr,
        name="technical_analysis_snr",
    ),
    path("update-database/", update_database, name="update-database"),
    path(
        "technical-analysis/instrument-analysis/",
        views.instrument_analysis,
        name="instrument_analysis",
    ),
    path(
        "analyze-with-historical-data/",
        views.analyze_with_historical_data,
        name="analyze_with_historical_data",
    ),
    # PRICE ACTION
    path(
        "price-action/",
        views.price_action_with_indicators,
        name="price_action_with_indicators",
    ),
    path("trade-chart/", views.trade_chart, name="trade_chart"),
    path("trade-chart-page/", views.trade_chart_page, name="trade_chart_page"),
    # path("market-analysis/", market_analysis_view, name="market_analysis"),
    path(
        "technical-analysis/trade_chart/",
        views.plotly_chart_view,
        name="plotly_chart_view",
    ),

    path('analyze_with_ai_x3/', analyze_with_ai_x3, name='analyze_with_ai_x3'),
    path('analyze_with_historical_data/', analyze_with_historical_data, name='analyze_with_historical_data'),
]
