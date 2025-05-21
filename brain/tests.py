from django.test import TestCase
from .models import Thought


class ThoughtModelTest(TestCase):
    def test_thought_creation(self):
        thought = Thought.objects.create(title="Test Thought", content="Test Content")
        self.assertEqual(thought.title, "Test Thought")


import json

from polygon.views import define_timeframes
from .models import Thought

# ========================================
# Библиотеки Python
# ========================================
import os
import logging
import datetime
from datetime import timedelta
import calendar
import io
import urllib
import base64

# ========================================
# Сторонние библиотеки
# ========================================
import MetaTrader5 as mt5
import plotly.graph_objects as go
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import talib
import openai
from dotenv import load_dotenv

# ========================================
# Django
# ========================================
from django.shortcuts import render, redirect
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
)
from django.utils import timezone
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

# ========================================
# Локальные модули (src.*)
# ========================================
from src.adviser.new_technical_indicators import (
    fetch_ohlc_data,
    get_new_indicators_data,
)
from src.indicators.technical_indicators import (
    analyze_current_price_with_fibonacci,
    calculate_fibonacci_levels,
    calculate_fibonacci_pivot_points,
    calculate_fibonacci_time_zones,
    calculate_macd,
    calculate_ote,
    calculate_pivot_points,
    calculate_rsi,
    find_nearest_levels,
    is_price_in_ote,
    get_indicators_data,
)
from src.utils.ai_analytic import (
    analyze_with_ai,
    analyze_tech_data_with_ai,
    appeal_to_ai_with_historical_data,
)
from src.utils.mt5_utils import (
    initialize_mt5,
    shutdown_mt5,
    get_historical_account_data,
    get_trade_history,
    get_account_info,
    get_open_positions,
    get_currency_tick,
    open_market_position,
    place_pending_order,
    get_rates_dataframe,
    get_ohlc_extended,
    get_trading_profit_history,
)
from src.utils.investing_calendar import get_investing_calendar
from src.utils.rss_news import get_fxstreet_news

from src.trading.trading import (
    analyze_strategies_for_timeframes,
    prepare_fibonacci_levels,
    prepare_fibonacci_levels_as_fields,
)
from src.indicators.market_structure import (
    calculate_regression_channel,
    create_instrument_structure,
    identify_market_structure,
)
from src.trading.ict_strategy import ict_strategy
from src.trading.smc_strategy import smc_strategy
from src.trading.snr_strategy import snr_strategy
from src.trading.forex_pair import (
    majors,
    metals,
    cryptocurrencies,
    stocks,
    indices,
    commodities,
)
from src.services.market_analysis import get_market_analysis
from brain.optimized.optimized_indicators import generate_plotly_data

# ========================================
# Модели
# ========================================
from polygon.models import Recommendation

# что то
from MetaTrader5 import initialize, history_deals_get, account_info
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


def thought_list(request):
    thoughts = Thought.objects.all()
    return render(request, "brain/thought_list.html", {"thoughts": thoughts})


def price_action_chart(request: HttpRequest) -> HttpResponse:
    try:
        # Инициализация MetaTrader 5
        initialize_mt5()

        # Получаем символ из cookie или GET-запроса
        # 1) Определяем symbol, timeframe
        symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
        symbol = request.GET.get("symbol", symbol_from_cookie)

        timeframes = define_timeframes()
        selected_timeframe = request.GET.get("timeframe", "15m")
        timeframe = timeframes.get(selected_timeframe, mt5.TIMEFRAME_M15)
        selected_candles = int(request.GET.get("candles", 5))  # По умолчанию 5 свечей
        candles = selected_candles

        # Получение данных индикаторов
        indicators = get_new_indicators_data(symbol, timeframe, num_values=candles)

        # Вычисление уровней Pivot Points
        pivot_points = calculate_pivot_points(symbol, timeframe, num_values=candles)

        # Анализ стратегий
        ict_data = ict_strategy(symbol, timeframe)
        smc_data = smc_strategy(symbol, timeframe)
        snr_data = snr_strategy(symbol, timeframe)

        # Расчет уровней Фибоначчи
        fib_data = prepare_fibonacci_levels(symbol, timeframe)
        # Создание структуры инструмента
        instrument_structure = create_instrument_structure(symbol, timeframe)
        regression_channel = calculate_regression_channel(symbol, timeframe)
        # Расчет ближайших уровней поддержки и сопротивления
        current_price = instrument_structure.get("current_price")
        nearest_levels = find_nearest_levels(fib_data, current_price)
        fib_analysis = analyze_current_price_with_fibonacci(
            high=instrument_structure["ohlc"][-1]["high"],  # Последний максимум
            low=instrument_structure["ohlc"][-1]["low"],  # Последний минимум
            close=instrument_structure["ohlc"][-1]["close"],  # Цена закрытия
            current_price=instrument_structure["current_price"],  # Текущая цена
            start_time=instrument_structure["ohlc"][0]["time"],  # Начало анализа
            end_time=instrument_structure["ohlc"][-1]["time"],  # Конец анализа
        )
        # Расчет OTE
        ote_analysis = calculate_ote(
            symbol=symbol,
            timeframe=timeframe,
            trend=instrument_structure["trend"],
            bars=500,
            local_bars=128,
        )

        # Проверка, находится ли текущая цена в зоне OTE
        is_in_ote = (
            is_price_in_ote(
                price=instrument_structure["current_price"],
                ote_levels=ote_analysis["ote_levels"],
            )
            if ote_analysis
            else False
        )

        # Приводим Timestamp к строке
        for bar in instrument_structure["ohlc"]:
            bar["time"] = bar["time"].isoformat()

        # Сериализуем вручную
        ohlc_json = json.dumps(instrument_structure["ohlc"])
        indicators_json = json.dumps(indicators)  # Добавляем сериализацию индикаторов
        fibonacci_levels_json = json.dumps(fib_data)  # Сериализация уровней Фибоначчи

        # Подготовка контекста
        logging.info(f"Количество OHLC баров: {len(instrument_structure['ohlc'])}")
        logging.info(f"Количество RSI значений: {len(indicators.get('RSI', []))}")

        context = {
            "symbol": symbol,
            "timeframes": list(timeframes.keys()),
            "selected_timeframe": selected_timeframe,
            "selected_candles": selected_candles,
            "indicators": indicators,
            "indicators_json": indicators_json,  # Добавляем в контекст
            "fibonacci_levels_json": fibonacci_levels_json,  # Передаём сериализованные уровни Фибоначчи
            "pivot_points": pivot_points,
            "ict_strategy": ict_data,
            "smc_strategy": smc_data,
            "snr_strategy": snr_data,
            "fibonacci_levels": fib_data,
            "instrument_structure": instrument_structure,
            "regression_channel": regression_channel,
            "nearest_levels": nearest_levels,  # Добавляем ближайшие уровни
            "fib_analysis": fib_analysis,
            "ote_analysis": ote_analysis,
            "is_in_ote": is_in_ote,
            "ohlc_data": instrument_structure["ohlc"],  # список OHLC
            "ohlc_json": ohlc_json,
        }

        # Возвращаем JSON для AJAX-запросов
        # Проверяем тип запроса
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(context)

        # 5) Обычный HTML-ответ
        response = render(request, "brain/PA-chart.html", context)
        response.set_cookie("selected_timeframe", define_timeframes)
        return response

    except Exception as e:
        logging.info(f"pivot_points: {pivot_points}")
        logging.info(f"fib_data: {fib_data}")
        logging.info(f"ote_analysis: {ote_analysis}")
        logging.info(f"indicators: {indicators}")
        logging.error(f"Ошибка ...: {e}")
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        shutdown_mt5()
