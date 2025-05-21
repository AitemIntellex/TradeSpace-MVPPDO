from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "fundamental-analysis/", views.fundamental_analysis, name="fundamental_analysis"
    ),
    path("ai-analysis/", views.ai_analysis, name="ai_analysis"),
    path(
        "recommendations/", views.recommendations_list, name="recommendations_list"
    ),  # Исправленный вызов функции
    path("test/", views.test_view, name="test"),
    path("profile-info/", views.test_view, name="profile-info"),
    path("statistics/", views.statistics_view, name="statistics"),
    path("trade-history/", views.trade_history, name="trade_history"),
    path("trade-calculator/", views.trade_calculator, name="trade_calculator"),
    path("trade/", views.trade, name="trade"),
    path("logout/", views.logout_view, name="logout"),
    # Страницы тех анализа
    path("technical-analysis/", views.technical_analysis, name="technical_analysis"),
    path(
        "technical-analysis/general/",
        views.technical_analysis_general,
        name="technical_analysis_general",
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
]
