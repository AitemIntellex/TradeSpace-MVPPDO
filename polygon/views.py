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
from brain.optimized.optimized_indicators import get_indicators_data_history
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
from .models import Recommendation

# что то
from MetaTrader5 import initialize, history_deals_get, account_info
from plotly.subplots import make_subplots

import json
from django.http import JsonResponse
from src.utils.mt5_utils import get_currency_tick

logger = logging.getLogger(__name__)


@csrf_exempt
def update_database(request):
    if request.method == "POST":
        # Логика обновления базы данных
        try:
            # Пример обновления данных
            get_currency_tick()
            return JsonResponse({"status": "success", "message": "Данные обновлены."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse(
        {"status": "error", "message": "Некорректный запрос."}, status=400
    )


from datetime import datetime, timedelta


def fetch_economic_news(request):
    try:
        # Получаем все события из экономического календаря
        events = get_investing_calendar()

        if not events:
            return JsonResponse({"events": []}, safe=False)

        # Текущее время
        now = datetime.now()

        # Обратный отсчет (в минутах)
        countdown_minutes = 120

        # Сортируем события по времени
        sorted_events = sorted(
            events,
            key=lambda x: datetime.strptime(x["time"], "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            ),
        )

        # Добавляем обратный отсчет в события
        updated_events = []
        for event in sorted_events:
            event_time = datetime.strptime(event["time"], "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            time_delta = (event_time - now).total_seconds() / 60  # Разница в минутах

            if (
                0 <= time_delta <= countdown_minutes
            ):  # Фильтруем события в пределах 180 минут
                event["countdown"] = (
                    f"{int(time_delta)} мин."  # Добавляем обратный отсчет
                )
                updated_events.append(event)

        return JsonResponse({"events": updated_events}, safe=False)

    except Exception as e:
        # Обработка ошибок
        return JsonResponse({"error": str(e)}, status=500)


def home(request):
    # Инициализация контекста с символами для выбора

    context = {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
    }
    # Объединяем все списки
    all_symbols = majors + metals + cryptocurrencies + stocks + indices + commodities
    context["all_symbols"] = all_symbols

    try:
        # Инициализируем MetaTrader 5
        initialize_mt5()

        try:
            # Получаем информацию об аккаунте и открытые позиции
            account_info = get_account_info()
            open_positions = get_open_positions()
            context.update(account_info)
            context["open_positions"] = open_positions

            # Получаем валютную пару из cookie
            symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")

            # Получаем валютную пару из GET-запроса или используем значение из cookie
            symbol = request.GET.get("symbol", symbol_from_cookie)
            if not mt5.symbol_select(symbol, True):
                raise Exception(f"Не удалось выбрать символ {symbol} для анализа.")

            selected_pair_tick = get_currency_tick(symbol)
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для символа {symbol}.")

            # Получение стоимости тика
            # tick_value = symbol.tick_value
            # context["tick_value"] = tick_value  # Передаем в контекст для шаблона
            context["selected_pair"] = symbol  # Для отображения выбранного символа

            context.update(
                {
                    "selected_pair_tick": selected_pair_tick,
                    "selected_pair": symbol,
                }
            )

            # Получаем историю баланса и капитала за последние 30 дней для графиков
            today = datetime.now()
            start_date = today - timedelta(days=30)

            balance_history = []
            equity_history = []
            date_labels = []
            profit_history = []

            for i in range(30):
                date = start_date + timedelta(days=i)
                balance_history.append(account_info["balance"])  # Получаем баланс
                equity_history.append(account_info["equity"])  # Получаем капитал
                profit_history.append(
                    get_trading_profit_history()[i]
                )  # История прибыли
                date_labels.append(date.strftime("%d-%m-%Y"))

            context.update(
                {
                    "balance_history": balance_history,
                    "equity_history": equity_history,
                    "profit_history": profit_history,
                    "date_labels": date_labels,
                    "last_updated": timezone.now(),
                }
            )

            # Данные для таблиц
            history = get_trade_history()
            recent_trades = history[-10:]

            profits = [deal["profit"] for deal in recent_trades]
            dates = [datetime.fromtimestamp(deal["time"]) for deal in recent_trades]
            symbols = [deal["symbol"] for deal in recent_trades]

            combined_data = zip(dates, symbols, profits)
            context.update(
                {
                    "recent_trades": combined_data,
                    "error": None,
                }
            )

            # Логика для графика "Прибыль/убыток по дням недели"
            days_of_week = {day: 0 for day in calendar.day_name}
            for date, profit in zip(dates, profits):
                day_name = calendar.day_name[date.weekday()]
                days_of_week[day_name] += profit

            labels = list(days_of_week.keys())
            data = list(days_of_week.values())

            filtered_profits = [profit for profit in profits if profit != 0]
            filtered_combined_data = [
                (date, symbol, profit)
                for date, symbol, profit in zip(dates, symbols, profits)
                if profit != 0  # Исключаем строки с прибылью/убытком 0
            ]

            context.update(
                {
                    "labels": list(days_of_week.keys()),  # Дни недели
                    "data": [
                        days_of_week[day] for day in days_of_week
                    ],  # Значения прибыли/убытка
                }
            )

            # Логика для фильтрации истории по датам
            start_date_str = request.GET.get("start_date")
            end_date_str = request.GET.get("end_date")

            start_date = (
                datetime.strptime(start_date_str, "%Y-%m-%d")
                if start_date_str
                else None
            )
            end_date = (
                datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else None
            )

            history = get_trade_history(start_date, end_date)
            profits = [deal["profit"] for deal in history]
            dates = [datetime.fromtimestamp(deal["time"]) for deal in history]
            symbols = [deal["symbol"] for deal in history]

            combined_data = zip(dates, symbols, profits)

            # Группировка по дням недели
            days_of_week = {day: 0 for day in calendar.day_name}
            for date, profit in zip(dates, profits):
                day_name = calendar.day_name[date.weekday()]
                days_of_week[day_name] += profit

            labels = list(days_of_week.keys())
            data = list(days_of_week.values())

            filtered_profits = [profit for profit in profits if profit != 0]
            filtered_combined_data = [
                (date, symbol, profit)
                for date, symbol, profit in zip(dates, symbols, profits)
                if profit != 0
            ]

            context.update(
                {
                    "days_of_week": days_of_week,
                    "combined_data": filtered_combined_data,
                    "profits": filtered_profits,
                    "dates": [date.strftime("%Y-%m-%d %H:%M:%S") for date in dates],
                    "symbols": symbols,
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "labels": labels,  # Добавляем labels
                    "data": data,  # Добавляем data
                    "error": None,
                }
            )

        finally:
            shutdown_mt5()

    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в home: {e}")

    return render(request, "home.html", context)


def fundamental_analysis(request):
    # Получаем валютную пару из cookie
    symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")

    # Получаем валютную пару из GET-запроса или используем значение из cookie
    symbol = request.GET.get("symbol", symbol_from_cookie)
    # Страница фундаментального анализа
    context = {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
    }
    # Объединяем все списки
    all_symbols = majors + metals + cryptocurrencies + stocks + indices + commodities
    context["all_symbols"] = all_symbols

    try:
        # Получаем экономический календарь и новости
        context["economic_calendar"] = get_investing_calendar()
        context["rss_news"] = get_fxstreet_news()

    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в fundamental_analysis: {e}")

    return render(request, "fundamental_analysis.html", context)


def technical_analysis(request):
    # Страница технического анализа
    # Получаем валютную пару из cookie

    open_positions = get_open_positions()
    symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")

    # Получаем валютную пару из GET-запроса или используем значение из cookie
    symbol = request.GET.get("symbol", symbol_from_cookie)
    num_values = request.GET.get("num_values", "1")
    # Преобразуем в int, если нужно
    try:
        num_values_int = int(num_values)
    except ValueError:
        num_values_int = 1
    timeframes = define_timeframes()
    ict_ote_levels_by_timeframe = {}
    for label, tf in timeframes.items():
        ict_data = ict_strategy(symbol, tf)
        ote_levels = ict_data.get("ote_levels", {})
        # Убедимся, что результат всегда словарь
        ict_ote_levels_by_timeframe[label] = (
            ote_levels if isinstance(ote_levels, dict) else {}
        )
        logging.info(f"OTE levels for {label}: {ict_ote_levels_by_timeframe[label]}")

    # Словарь для хранения данных Pivot Points по таймфреймам
    pivot_points_by_timeframe = {}

    for timeframe_label, timeframe_value in timeframes.items():
        pivot_points = calculate_pivot_points(symbol, timeframe_value, num_values_int)
        pivot_points_by_timeframe[timeframe_label] = pivot_points

    context = {
        "pivot_points_by_timeframe": pivot_points_by_timeframe,
        "selected_pair": symbol,
    }

    strategies_process_by_timeframe = {}
    for label, tf in timeframes.items():
        ict_result = ict_strategy(symbol, tf)  # Вызов стратегии ICT
        smc_result = smc_strategy(symbol, tf)  # Вызов стратегии SMC
        snr_result = snr_strategy(symbol, tf)  # Вызов стратегии SNR

        # Создаем структуру данных для текущего таймфрейма
        strategies_process_by_timeframe[label] = {
            "ICT": {
                "signal": ict_result.get("signal", "no_signal"),
                "trend": ict_result.get("trend", "-"),
                "fvg_zones": ict_result.get("fvg_zones", "-"),
                "support": ict_result.get("support", "-"),
                "resistance": ict_result.get("resistance", "-"),
                "fib_levels": ict_result.get("fib_levels", {}),
            },
            "SMC": {
                "signal": smc_result.get("signal", "no_signal"),
                "trend": smc_result.get("trend", "-"),
                "support": smc_result.get("support", "-"),
                "resistance": smc_result.get("resistance", "-"),
                "fvg_zones": smc_result.get("fvg_zones", "-"),
            },
            "SNR": {
                "signal": snr_result.get("signal", "no_signal"),
                "trend": snr_result.get("trend", "-"),
                "support": snr_result.get("support", "-"),
                "resistance": snr_result.get("resistance", "-"),
            },
        }

        # Логируем для отладки
        logging.info(f"Analysis for {label}: {strategies_process_by_timeframe[label]}")

    context = {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
        "selected_pair": symbol,
        "num_values": num_values,  # Для отображения текущего выбора
        "ict_ote_levels_by_timeframe": ict_ote_levels_by_timeframe,
        "strategies_process_by_timeframe": strategies_process_by_timeframe,
    }
    # Объединяем все списки
    all_symbols = majors + metals + cryptocurrencies + stocks + indices + commodities
    context["all_symbols"] = all_symbols

    try:
        initialize_mt5()  # Инициализируем MetaTrader 5
        try:
            # Получаем тик выбранной валютной пары
            selected_pair_tick = get_currency_tick(symbol)
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для символа {symbol}.")

            context["selected_pair_tick"] = selected_pair_tick

            # Анализ стратегий и регрессионного канала для всех таймфреймов
            (
                indicators_by_timeframe,
                ict_strategies_by_timeframe,
                smc_strategies_by_timeframe,
                snr_strategies_by_timeframe,
            ) = analyze_strategies_for_timeframes(symbol, timeframes, num_values_int)

            # Получаем последние 3 значения индикаторов для отображения трендов
            indicators_summary = {}
            for timeframe, indicators in indicators_by_timeframe.items():
                indicators_summary[timeframe] = {
                    "rsi": indicators.get("rsi", [])[-3:],
                    "macd": indicators.get("macd", [])[-3:],
                    "signal": indicators.get("signal", [])[-3:],
                    "upper_band": indicators.get("upper_band", [])[-3:],
                    "lower_band": indicators.get("lower_band", [])[-3:],
                    "atr": indicators.get("atr", [])[-3:],
                    "stochastic": {
                        "K": indicators.get("stochastic_k", [])[-3:],
                        "D": indicators.get("stochastic_d", [])[-3:],
                    },
                    "fibonacci_levels": indicators.get("fibonacci_levels"),
                    "regression_channel": indicators.get("regression_channel"),
                    "vwap": indicators.get("vwap", [])[-3:],
                    "cci": indicators.get("cci", [])[-3:],
                    "mfi": indicators.get("mfi", [])[-3:],
                }

            regression_channel_by_timeframe = {}
            for label, timeframe in timeframes.items():
                regression_result = calculate_regression_channel(symbol, timeframe)
                if regression_result:
                    regression_channel_by_timeframe[label] = regression_result
                else:
                    logging.warning(
                        f"Регрессионный анализ не выполнен для {symbol} на таймфрейме {label}"
                    )

            # Обновляем контекст для передачи в шаблон
            strategies = [
                {"name": "ICT Strategy", "data": ict_strategies_by_timeframe},
                {"name": "SMC Strategy", "data": smc_strategies_by_timeframe},
                {"name": "SNR Strategy", "data": snr_strategies_by_timeframe},
            ]
            ote_levels_by_timeframe = {}
            market_structure_by_timeframe = {}
            for label, tf in timeframes.items():
                ote_levels_by_timeframe[label] = prepare_fibonacci_levels(symbol, tf)
            for label, tf in timeframes.items():
                market_structure = identify_market_structure(symbol, tf)
                if market_structure:
                    market_structure_by_timeframe[label] = {
                        "trend": market_structure["trend"],
                        "support": market_structure["support"],
                        "resistance": market_structure["resistance"],
                        "atr": market_structure.get("atr", "Нет данных"),
                    }
                else:
                    market_structure_by_timeframe[label] = {
                        "trend": "Нет данных",
                        "support": "Нет данных",
                        "resistance": "Нет данных",
                        "atr": "Нет данных",
                    }

            context.update(
                {
                    "symbol": symbol,
                    "timeframes": timeframes,
                    "indicators_by_timeframe": indicators_by_timeframe,
                    "ict_strategies_by_timeframe": ict_strategies_by_timeframe,
                    "smc_strategies_by_timeframe": smc_strategies_by_timeframe,
                    "snr_strategies_by_timeframe": snr_strategies_by_timeframe,
                    "regression_channel_by_timeframe": regression_channel_by_timeframe,
                    "ote_levels_by_timeframe": ote_levels_by_timeframe,
                    "market_structure_by_timeframe": market_structure_by_timeframe,
                }
            )
            flat_indicators_summary = []
            for timeframe, indicators in indicators_summary.items():
                for indicator, values in indicators.items():
                    flat_indicators_summary.append(
                        {
                            "timeframe": timeframe,
                            "indicator": indicator,
                            "values": values,
                        }
                    )
            context["flat_indicators_summary"] = flat_indicators_summary

        finally:
            shutdown_mt5()  # Отключаем MetaTrader 5

    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в technical_analysis: {e}")

    indicators_list = ["rsi", "sma", "mfi", "macd", "signal"]
    context["indicators_list"] = indicators_list
    return render(request, "technical_analysis.html", context)


def technical_analysis_general(request):
    symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")

    # Получаем валютную пару из GET-запроса или используем значение из cookie
    symbol = request.GET.get("symbol", symbol_from_cookie)
    timeframes = {
        "1H": mt5.TIMEFRAME_H1,
        "4H": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }

    try:
        # Структура рынка
        market_structure = {
            tf: identify_market_structure(symbol, tf) for tf in timeframes.values()
        }

        # Индикаторы
        indicators_by_timeframe = {
            tf: get_indicators_data(symbol, tf) for tf in timeframes.values()
        }

        # Стратегии
        strategies_by_timeframe = analyze_strategies_for_timeframes(symbol, timeframes)

    except Exception as e:
        logging.error(f"Ошибка анализа: {e}")
        market_structure = {}
        indicators_by_timeframe = {}
        strategies_by_timeframe = {}

    tech_analysis_context = {
        "symbol": symbol,
        "market_structure": market_structure,
        "indicators_by_timeframe": indicators_by_timeframe,
        "strategies_by_timeframe": strategies_by_timeframe,
    }

    return render(
        request,
        "technical_analysis/technical_analysis_general.html",
        tech_analysis_context,
    )


def get_cached_indicators(symbol, timeframe):
    """
    Получение индикаторов с использованием кэша.
    """
    cache_key = f"indicators_{symbol}_{timeframe}"
    data = cache.get(cache_key)
    if not data:
        data = get_indicators_data(symbol, timeframe)
        cache.set(cache_key, data, timeout=300)  # Кэшируем данные на 5 минут
    return data


def get_color_for_trend(trend_value: str) -> str:
    """
    Возвращает цвет подложки (светофор) в зависимости от тренда.
    Пример:
      - "uptrend" или "strong_uptrend"  -> зеленый
      - "downtrend" или "strong_downtrend" -> красный
      - "range" или "flat" -> желтый
      - Иначе -> серый
    """
    if "uptrend" in trend_value or trend_value == "up":
        return "green"
    elif "downtrend" in trend_value or trend_value == "down":
        return "red"
    elif "range" in trend_value or trend_value == "flat":
        return "yellow"
    return "lightgray"  # нет данных или иной вариант


def get_trend_color(trend):
    if trend == "uptrend" or trend == "strong_uptrend":
        return "#d4f7dc"  # Зеленый
    elif trend == "downtrend" or trend == "strong_downtrend":
        return "#f7d4d4"  # Красный
    elif trend == "range":
        return "#ffffcc"  # Желтый
    return "#f0f0f0"  # Серый как значение по умолчанию


def technical_analysis_indicators(request):
    """
    Обобщённая страница для вывода технических индикаторов и структуры рынка
    по всем таймфреймам одновременно (или выборочно).
    """
    open_positions = get_open_positions()  # Если нужно

    # 1) Получаем текущий символ (из GET, потом cookie, иначе XAUUSD)
    symbol = request.GET.get("symbol", request.COOKIES.get("selected_pair", "XAUUSD"))

    # 2) Определяем, сколько баров подгружаем (по умолчанию 1)
    try:
        num_values_int = int(request.GET.get("num_values", "1"))
    except ValueError:
        num_values_int = 1

    # 3) Какие таймфреймы обрабатываем?
    requested_tf = request.GET.get("timeframe", "ALL")
    all_timeframes = define_timeframes()  # Например, {"M1": "M1", "M5": "M5", ...}
    if requested_tf.upper() != "ALL" and requested_tf in all_timeframes:
        timeframes = {requested_tf: all_timeframes[requested_tf]}
    else:
        timeframes = all_timeframes

    # 4) Сколько последних значений (recent_count) для индикаторов показать?
    try:
        recent_count = int(request.GET.get("recent_count", "3"))
    except ValueError:
        recent_count = 3

    # Базовый контекст
    context = {
        "selected_pair": symbol,
        "num_values": num_values_int,
        "requested_timeframe": requested_tf,
        "recent_count": recent_count,
    }

    # 5) Подготовка словарей-накопителей
    structure_by_timeframe = {}
    indicators_by_timeframe = {}
    pivot_points_by_timeframe = {}
    market_structure_by_timeframe = {}
    fibonacci_by_timeframe = {}

    # Словари со значениями по умолчанию
    default_structure = {
        "trend": "Нет данных",
        "support": None,
        "resistance": None,
    }
    default_indicators = {
        "atr": [],
        "mfi": [],
        "cci": [],
        "stochastic_k": [],
        "stochastic_d": [],
        "sma": [],
        "macd": [],
        "signal": [],
        "rsi": [],
        "ohlc": [],
        "pivot": [],
        "pp_resistance": [],
        "pp_support": [],
        "upper_band": [],
        "lower_band": [],
        "vwap": [],
        # и т.д., если есть ещё
    }
    default_pivot_points = [
        {
            "pivot": None,
            "pp_resistance": [None] * 3,
            "pp_support": [None] * 3,
        }
    ]
    default_fibonacci = {
        "fib_levels": {},
        "fib_ranges": {},
        "local_high": None,
        "local_low": None,
        "absolute_high": None,
        "absolute_low": None,
        "trend": None,
    }

    # 6) Подключаемся к MT5 и собираем данные
    try:
        initialize_mt5()
        try:
            # Проверяем тик для выбранного символа
            selected_pair_tick = get_currency_tick(symbol)
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для символа {symbol}.")
            context["selected_pair_tick"] = selected_pair_tick

            # Цикл по таймфреймам
            for label, tf in timeframes.items():
                # 6.1) Структура инструмента (support/resistance/trend)
                instrument_data = create_instrument_structure(
                    symbol, tf, bars=num_values_int
                )
                if not instrument_data:
                    instrument_data = dict(default_structure)

                instrument_data["trend_color"] = get_color_for_trend(
                    instrument_data.get("trend", "Нет данных")
                )

                # 6.2) Индикаторы
                ind_data = get_indicators_data(symbol, tf, num_values=num_values_int)
                if not ind_data:
                    ind_data = dict(default_indicators)

                # Урезаем списки индикаторов до recent_count (если нужно)
                for key, val in ind_data.items():
                    if isinstance(val, list) and len(val) > recent_count:
                        ind_data[key] = val[-recent_count:]

                # 6.3) Pivot Points
                pivot_points = calculate_pivot_points(symbol, tf, num_values_int)
                if not pivot_points:
                    pivot_points = default_pivot_points

                # 6.4) Фибоначчи
                fib_for_tf = calculate_fibonacci_levels(
                    symbol, tf, bars=500, local_bars=100
                )
                if not fib_for_tf:
                    fib_for_tf = dict(default_fibonacci)

                # 6.5) Маркет структура (абсолютные / локальные экстремумы)
                ms = identify_market_structure(symbol, tf)
                if not ms:
                    ms = dict(default_structure)

                ms["trend_color"] = get_color_for_trend(ms.get("trend", "Нет данных"))
                # Добавим экстремумы (если identify_market_structure их возвращает)
                ms["absolute_high"] = ms.get("absolute_high", None)
                ms["absolute_low"] = ms.get("absolute_low", None)
                ms["local_high"] = ms.get("local_high", None)
                ms["local_low"] = ms.get("local_low", None)

                # Сохраняем данные в словари
                structure_by_timeframe[label] = instrument_data
                indicators_by_timeframe[label] = ind_data
                pivot_points_by_timeframe[label] = pivot_points
                fibonacci_by_timeframe[label] = fib_for_tf
                market_structure_by_timeframe[label] = ms

        finally:
            shutdown_mt5()

    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в technical_analysis_indicators: {e}")

    # 7) Дополняем контекст
    context.update(
        {
            "structure_by_timeframe": structure_by_timeframe,
            "indicators_by_timeframe": indicators_by_timeframe,
            "pivot_points_by_timeframe": pivot_points_by_timeframe,
            "market_structure_by_timeframe": market_structure_by_timeframe,
            "fibonacci_by_timeframe": fibonacci_by_timeframe,
        }
    )

    # 8) Формируем итоговый merged_data_by_timeframe — удобная структура «всё в одном»
    merged_data_by_timeframe = []
    for timeframe in indicators_by_timeframe:
        # Берём подготовленные данные
        ind = indicators_by_timeframe.get(timeframe, {})
        instr = structure_by_timeframe.get(timeframe, {})
        ms = market_structure_by_timeframe.get(timeframe, {})
        fib = fibonacci_by_timeframe.get(timeframe, {})

        # Пример дополнительных вычислений
        fib_pivot_levels = {}
        if fib:
            fib_pivot_levels = (
                calculate_fibonacci_pivot_points(
                    fib.get("local_high", 0),
                    fib.get("local_low", 0),
                    fib.get("absolute_high", 0),
                )
                or {}
            )

        nearest_levels = {}
        if fib_pivot_levels and "current_price" in fib:
            nearest_levels = (
                find_nearest_levels(fib_pivot_levels, fib["current_price"]) or {}
            )

        time_zones = {}
        if fib.get("start_time") and fib.get("end_time"):
            time_zones = (
                calculate_fibonacci_time_zones(fib["start_time"], fib["end_time"]) or {}
            )

        # Собираем в единый dict
        ote_data = calculate_ote(symbol, tf, trend="up")
        fibonacci_data = fibonacci_by_timeframe.get(tf, {})
        merged_data_by_timeframe.append(
            {
                "timeframe": timeframe,
                "indicators": ind,
                "structure": instr,  # create_instrument_structure
                "market_structure": ms,  # identify_market_structure
                "fibonacci": fib,  # calculate_fibonacci_levels
                "fib_pivot_levels": fib_pivot_levels,
                "nearest_levels": nearest_levels,
                "time_zones": time_zones,
                "ote": ote_data,  # Добавляем данные OTE
            }
        )

    context["merged_data_by_timeframe"] = merged_data_by_timeframe

    # 9) Рендеринг шаблона
    return render(
        request, "technical_analysis/technical_analysis_indicators.html", context
    )


# API endpoint for AJAX calls
def api_instrument_structure(request):
    symbol = request.GET.get("symbol")
    timeframe = request.GET.get("timeframe")

    if not symbol or not timeframe:
        return JsonResponse({"error": "Invalid parameters"}, status=400)

    data = create_instrument_structure(symbol, timeframe)

    # Проверяем, возвращает ли create_instrument_structure словарь
    if not isinstance(data, dict):
        return JsonResponse({"error": "Data format invalid"}, status=500)

    # Если все же не словарь, разрешаем сериализацию, но с safe=False
    return JsonResponse(data, safe=False)


def technical_analysis_strategies(request: HttpRequest) -> HttpResponse:
    """
    Вьюха для отображения стратегий и индикаторов технического анализа.
    """
    try:
        # Инициализация MetaTrader 5
        initialize_mt5()

        # Получаем символ из cookie или GET-запроса
        symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
        symbol = request.GET.get("symbol", symbol_from_cookie)

        # Определяем все таймфреймы
        timeframes = (
            define_timeframes()
        )  # {'1m': mt5.TIMEFRAME_M1, '5m': mt5.TIMEFRAME_M5, ...}

        # Получаем выбранный таймфрейм из GET-запроса или используем 15m по умолчанию
        timeframe_label = request.GET.get("timeframe", "15m")
        timeframe = timeframes.get(timeframe_label, mt5.TIMEFRAME_M5)

        # Сохраняем выбранный таймфрейм в cookie (опционально)
        response = render(
            request,
            "technical_analysis/technical_analysis_strategies.html",
            context={
                "symbol": symbol,
                "timeframes": timeframes,
                "timeframe_label": timeframe_label,
                # Добавляем остальные данные, как в текущем коде
            },
        )

        # Количество свечей для анализа
        candles = int(request.GET.get("candles", 5))  # По умолчанию 5 свечей

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

        # Подготовка контекста
        context = {
            "symbol": symbol,
            "timeframe_label": timeframe_label,
            "candles": candles,
            "indicators": indicators,
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
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(context)

        # Рендерим HTML-шаблон
        response.set_cookie("selected_timeframe", timeframe_label)
        return render(
            request, "technical_analysis/technical_analysis_strategies.html", context
        )

    except Exception as e:
        logging.error(f"Ошибка в technical_analysis_strategies: {e}")

        return JsonResponse({"error": str(e)}, status=500)
        return response

    finally:
        # Завершаем сессию MetaTrader 5
        shutdown_mt5()


def technical_analysis_tas(request: HttpRequest) -> HttpResponse:

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

        # Подготовка контекста
        context = {
            "symbol": symbol,
            "timeframes": list(timeframes.keys()),
            "selected_timeframe": selected_timeframe,
            "selected_candles": selected_candles,
            "indicators": indicators,
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
        response = render(request, "technical_analysis/tas1.html", context)
        response.set_cookie("selected_timeframe", define_timeframes)
        return response

    except Exception as e:
        logging.error(f"Ошибка ...: {e}")
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        shutdown_mt5()


def technical_analysis_tass(request: HttpRequest) -> HttpResponse:
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

        # Подготовка контекста
        context = {
            "symbol": symbol,
            "timeframes": list(timeframes.keys()),
            "selected_timeframe": selected_timeframe,
            "selected_candles": selected_candles,
            "indicators": indicators,
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
        response = render(request, "technical_analysis/tas2.html", context)
        response.set_cookie("selected_timeframe", define_timeframes)
        return response

    except Exception as e:
        logging.error(f"Ошибка ...: {e}")
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        shutdown_mt5()


def focused_technical_analysis(request: HttpRequest) -> HttpResponse:
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
        response = render(request, "technical_analysis/focused_tas.html", context)
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


def price_action_with_indicators(request: HttpRequest) -> HttpResponse:
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
        response = render(request, "technical_analysis/price-action.html", context)
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


def technical_analysis_all_timeframes(request: HttpRequest) -> HttpResponse:
    """
    Вьюха для отображения индикаторов и стратегий по всем таймфреймам.
    """
    try:
        # Инициализация MetaTrader 5
        initialize_mt5()

        # Получаем символ из cookie или GET-запроса
        symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
        symbol = request.GET.get("symbol", symbol_from_cookie)

        # Определяем все таймфреймы
        timeframes = define_timeframes()

        # Количество свечей для анализа (можно задать общее значение или разные для таймфреймов)
        candles = int(request.GET.get("candles", 5))  # По умолчанию 5 свечей

        # Подготовка данных для каждого таймфрейма
        analysis_data = {}
        for label, tf in timeframes.items():
            try:
                # Получение данных индикаторов
                indicators = get_new_indicators_data(symbol, tf, num_values=candles)

                # Вычисление уровней Pivot Points
                pivot_points = calculate_pivot_points(symbol, tf, num_values=candles)

                # Анализ стратегий
                ict_data = ict_strategy(symbol, tf)
                smc_data = smc_strategy(symbol, tf)
                snr_data = snr_strategy(symbol, tf)

                # Расчет уровней Фибоначчи
                fib_data = prepare_fibonacci_levels(symbol, tf)
                # Создание структуры инструмента
                instrument_structure = create_instrument_structure(symbol, tf)
                regression_channel = calculate_regression_channel(symbol, tf)

                # Расчет ближайших уровней поддержки и сопротивления
                current_price = instrument_structure.get("current_price")
                nearest_levels = find_nearest_levels(fib_data, current_price)
                fib_analysis = analyze_current_price_with_fibonacci(
                    high=instrument_structure["ohlc"][-1]["high"],  # Последний максимум
                    low=instrument_structure["ohlc"][-1]["low"],  # Последний минимум
                    close=instrument_structure["ohlc"][-1]["close"],  # Цена закрытия
                    current_price=instrument_structure["current_price"],  # Текущая цена
                    start_time=instrument_structure["ohlc"][0][
                        "time"
                    ],  # Начало анализа
                    end_time=instrument_structure["ohlc"][-1]["time"],  # Конец анализа
                )
                # Расчет OTE
                ote_analysis = calculate_ote(
                    symbol=symbol,
                    timeframe=tf,
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

                # Сохранение данных для текущего таймфрейма
                analysis_data[label] = {
                    "indicators": indicators,
                    "pivot_points": pivot_points,
                    "ict_strategy": ict_data,
                    "smc_strategy": smc_data,
                    "snr_strategy": snr_data,
                    "fibonacci_levels": fib_data,
                    "instrument_structure": instrument_structure,
                    "regression_channel": regression_channel,
                    "nearest_levels": nearest_levels,
                    "fib_analysis": fib_analysis,
                    "ote_analysis": ote_analysis,
                    "is_in_ote": is_in_ote,
                }
            except Exception as e:
                logging.error(f"Ошибка обработки таймфрейма {label}: {e}")

        # Подготовка контекста
        context = {
            "symbol": symbol,
            "timeframes": analysis_data,
        }

        # Возвращаем JSON для AJAX-запросов
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(context)

        # Рендерим HTML-шаблон
        return render(
            request,
            "technical_analysis/technical_analysis_all_timeframes.html",
            context,
        )

    except Exception as e:
        logging.error(f"Ошибка в technical_analysis_all_timeframes: {e}")
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        # Завершаем сессию MetaTrader 5
        shutdown_mt5()


def technical_analysis_smc(request):

    try:
        initialize_mt5()

        # **1) Получаем символ, ТФ и количество свечей (строго по структуре)**
        symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
        symbol = request.GET.get("symbol", symbol_from_cookie)

        timeframes = define_timeframes()
        selected_timeframe = request.GET.get("timeframe", "15m")
        timeframe = timeframes.get(selected_timeframe, mt5.TIMEFRAME_M15)
        selected_candles = int(request.GET.get("candles", 5))  # По умолчанию 5 свечей
        candles = selected_candles

        # **2) Получаем данные (индикаторы, уровни, структуры)**
        indicators = get_new_indicators_data(symbol, timeframe, num_values=candles)
        pivot_points = calculate_pivot_points(symbol, timeframe, num_values=candles)
        fib_data = prepare_fibonacci_levels(symbol, timeframe)
        instrument_structure = create_instrument_structure(symbol, timeframe)
        regression_channel = calculate_regression_channel(symbol, timeframe)
        nearest_levels = find_nearest_levels(
            fib_data, instrument_structure["current_price"]
        )

        price_indicators = {
            k: v
            for k, v in indicators.items()
            if k in ["sma", "upper_band", "lower_band", "vwap"]
        }
        oscillator_indicators = {
            k: v
            for k, v in indicators.items()
            if k in ["rsi", "macd", "stochastic_k", "stochastic_d", "cci", "mfi"]
        }

        # **3) Формируем JSON для графика**
        for bar in instrument_structure["ohlc"]:
            bar["time"] = bar["time"].isoformat()  # Приводим timestamp к строке

        context = {
            "symbol": symbol,
            "timeframes": list(timeframes.keys()),
            "selected_timeframe": selected_timeframe,
            "selected_candles": selected_candles,
            "ohlc_data": instrument_structure["ohlc"],
            "price_indicators": price_indicators,
            "oscillator_indicators": oscillator_indicators,
            "indicators": indicators,
            "pivot_points": pivot_points,
            "fibonacci_levels": fib_data,
            "nearest_levels": nearest_levels,
            "regression_channel": regression_channel,
        }

        # **4) Если AJAX-запрос — отдаём JSON**
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(context)

        # **5) Обычный HTML-рендер**
        return render(
            request, "technical_analysis/technical_analysis_smc.html", context
        )

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        shutdown_mt5()


def technical_analysis_ict(request: HttpRequest) -> HttpResponse:
    """
    Вьюха для отображения стратегий и индикаторов технического анализа.
    """
    try:
        # Инициализация MetaTrader 5
        initialize_mt5()

        # Получаем символ из cookie или GET-запроса
        symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
        symbol = request.GET.get("symbol", symbol_from_cookie)

        # Определяем таймфрейм
        timeframes = define_timeframes()
        timeframe_label = request.GET.get("timeframe", "1h").lower()
        timeframe = timeframes.get(timeframe_label)
        if not timeframe:
            raise ValueError(f"Некорректный таймфрейм: {timeframe_label}")

        # Количество свечей для анализа
        candles = int(request.GET.get("candles", 5))  # По умолчанию 5 свечей

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

        # Подготовка контекста
        context = {
            "symbol": symbol,
            "timeframe_label": timeframe_label,
            "candles": candles,
            "indicators": indicators,
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
        }

        # Возвращаем JSON для AJAX-запросов
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(context)

        # Рендерим HTML-шаблон
        return render(
            request, "technical_analysis/technical_analysis_ict.html", context
        )

    except Exception as e:
        logging.error(f"Ошибка в technical_analysis_strategies: {e}")
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        # Завершаем сессию MetaTrader 5
        shutdown_mt5()


def technical_analysis_snr(request: HttpRequest) -> HttpResponse:

    try:
        # Инициализация MetaTrader 5
        initialize_mt5()

        # Получаем символ из cookie или GET-запроса
        symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
        symbol = request.GET.get("symbol", symbol_from_cookie)

        selected_timeframe = request.GET.get("timeframe", "15m").lower()

        timeframes = define_timeframes()
        timeframe = timeframes.get(selected_timeframe, mt5.TIMEFRAME_M15)

        print(f"🛠 DEBUG: Таймфрейм {selected_timeframe} -> {timeframe}")

        # Проверяем, что `timeframe` стал `int`, а не строкой!
        assert isinstance(timeframe, int), f"❌ Ошибка: {timeframe} не int"
        selected_candles = int(request.GET.get("candles", 5))  # По умолчанию 5 свечей
        candles = selected_candles

        # 🔥 Интеграция маркет-анализа (запускаем его вместе с остальным анализом)
        market_analysis = get_market_analysis(
            symbol, [selected_timeframe], num_values=candles
        )

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

        # Подготовка контекста (добавляем маркет-анализ)
        context = {
            "symbol": symbol,
            "timeframes": list(timeframes.keys()),
            "selected_timeframe": selected_timeframe,
            "selected_candles": selected_candles,
            "indicators": indicators,
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
            "market_analysis": market_analysis,  # 🔥 Добавляем маркет-анализ
        }

        # Возвращаем JSON для AJAX-запросов
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(context)

        # HTML-ответ
        response = render(
            request, "technical_analysis/technical_analysis_snr.html", context
        )
        response.set_cookie("selected_timeframe", selected_timeframe)
        return response

    except Exception as e:
        logging.error(f"Ошибка ...: {e}")
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        shutdown_mt5()

def get_historical_indicators(symbol, timeframe, count=5):
    ohlc_data = fetch_ohlc_data(symbol, timeframe, count)
    if not ohlc_data:
        return {"error": f"Нет данных по {symbol} на {timeframe}"}

    indicators_history = get_indicators_data_history(symbol, "M15", count=5)
    indicators["ohlc"] = ohlc_data  # У тебя fetch_ohlc_data уже возвращает список
    return indicators


# Страница AI анализа
# def ai_analysis(request):
#     # Получаем валютную пару из cookie
#     symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")

#     # Получаем валютную пару из GET-запроса или используем значение из cookie
#     symbol = request.GET.get("symbol", symbol_from_cookie)
#     timeframes = define_timeframes()
#     context = {
#         "majors": majors,
#         "metals": metals,
#         "cryptocurrencies": cryptocurrencies,
#         "stocks": stocks,
#         "indices": indices,
#         "commodities": commodities,
#     }
#     # Объединяем все списки
#     all_symbols = majors + metals + cryptocurrencies + stocks + indices + commodities
#     context["all_symbols"] = all_symbols

#     try:
#         initialize_mt5()  # Инициализируем MetaTrader 5
#         try:
#             # Получаем информацию об аккаунте и открытые позиции
#             account_info, open_positions = get_account_and_positions()
#             context.update(account_info)
#             context["open_positions"] = open_positions

#             # Получаем тик выбранной валютной пары
#             context["last_updated"] = timezone.now()
#             selected_pair_tick = get_currency_tick(symbol)
#             if selected_pair_tick is None:
#                 raise Exception(f"Не удалось получить тик для символа {symbol}.")
#             tick_value = selected_pair_tick.get(
#                 "tick_value", 0
#             )  # Добавляем стоимость тика
#             context["tick_value"] = tick_value

#             # Получаем тик выбранной валютной пары
#             selected_pair_tick = get_currency_tick(symbol)
#             if selected_pair_tick is None:
#                 raise Exception(f"Не удалось получить тик для символа {symbol}.")

#             context["selected_pair_tick"] = selected_pair_tick

#             # Выполнение анализа индикаторов для AI анализа
#             (
#                 indicators_by_timeframe,
#                 ict_strategies,
#                 smc_strategies_by_timeframe,
#                 snr_strategies_by_timeframe,
#             ) = analyze_strategies_for_timeframes(symbol, timeframes)

#             # Обновляем контекст для шаблона
#             context.update(
#                 {
#                     "indicators_by_timeframe": indicators_by_timeframe,
#                 }
#             )

#             # --- Обработка открытия позиции или установки отложенного ордера ---
#             if request.method == "POST" and "open_position" in request.POST:
#                 try:
#                     volume = float(request.POST.get("volume", 0.01))
#                     direction = request.POST.get("direction", "buy")
#                     take_profit = float(request.POST.get("take_profit", 0))
#                     stop_loss = float(request.POST.get("stop_loss", 0))
#                     result = open_market_position(
#                         symbol, volume, direction, take_profit, stop_loss
#                     )
#                     if result:
#                         messages.success(
#                             request, f"Позиция по {symbol} успешно открыта."
#                         )
#                     else:
#                         messages.error(
#                             request, f"Ошибка при открытии позиции по {symbol}."
#                         )
#                 except Exception as e:
#                     logging.error(f"Ошибка при открытии позиции по {symbol}: {e}")
#                     messages.error(request, f"Не удалось открыть позицию по {symbol}.")

#             if request.method == "POST" and "place_pending_order" in request.POST:
#                 try:
#                     volume = float(request.POST.get("volume", 0.01))
#                     order_type = request.POST.get("order_type", "buy_limit")
#                     price = float(request.POST.get("price", 0))
#                     take_profit = float(request.POST.get("take_profit", 0))
#                     stop_loss = float(request.POST.get("stop_loss", 0))
#                     result = place_pending_order(
#                         symbol, volume, order_type, price, take_profit, stop_loss
#                     )
#                     if result:
#                         messages.success(
#                             request, f"Отложенный ордер по {symbol} успешно установлен."
#                         )
#                     else:
#                         messages.error(
#                             request,
#                             f"Ошибка при установке отложенного ордера по {symbol}.",
#                         )
#                 except Exception as e:
#                     logging.error(
#                         f"Ошибка при установке отложенного ордера по {symbol}: {e}"
#                     )
#                     messages.error(
#                         request, f"Не удалось установить отложенный ордер по {symbol}."
#                     )

#             # Выполнение анализа с помощью AI, если запрос поступил
#             if request.method == "POST" and "analyze_x3" in request.POST:
#                 # Логика для анализа x3
#                 result = analyze_with_ai_x3(symbol)
#                 context["x3_analysis"] = result

#             if request.method == "POST" and "analyze_with_history" in request.POST:
#                 # Логика для анализа с историей
#                 result = appeal_to_ai_with_historical_data(symbol)
#                 context["historical_analysis"] = result

#             if request.method == "POST" and "analyze_with_ai" in request.POST:
#                 # Собираем индикаторы для всех таймфреймов
#                 indicators_summary = {}
#                 for timeframe, indicators in indicators_by_timeframe.items():
#                     indicators_summary[timeframe] = {
#                         "rsi": indicators.get("rsi"),
#                         "macd": indicators.get("macd"),
#                         "signal": indicators.get("signal"),
#                         "upper_band": indicators.get("upper_band"),
#                         "lower_band": indicators.get("lower_band"),
#                         "atr": indicators.get("atr"),
#                         "stochastic": {
#                             "K": indicators.get("stochastic_k"),
#                             "D": indicators.get("stochastic_d"),
#                         },
#                         "fibonacci_levels": indicators.get("fibonacci_levels"),
#                         "regression_channel": indicators.get("regression_channel"),
#                         "vwap": indicators.get("vwap"),
#                         "cci": indicators.get("cci"),
#                         "mfi": indicators.get("mfi"),
#                     }

#                 # Формируем данные для отправки в OpenAI
#                 result = {
#                     "symbol": symbol,
#                     "current_price": selected_pair_tick.get("bid")
#                     or selected_pair_tick.get("ask"),
#                     "indicators_summary": indicators_summary,  # Все данные по таймфреймам
#                     "economic_calendar": get_investing_calendar(),
#                     "news": get_fxstreet_news(),
#                     "strategies": {
#                         "ICT": ict_strategies,
#                         "SNR": snr_strategies_by_timeframe,
#                         "SMC": smc_strategies_by_timeframe,
#                     },
#                 }

#                 try:
#                     # Выполняем анализ с использованием OpenAI
#                     ai_analysis = analyze_with_ai(
#                         result, get_investing_calendar(), get_fxstreet_news()
#                     )
#                     context["ai_analysis"] = ai_analysis
#                 except Exception as e:
#                     logging.error(f"Ошибка при выполнении анализа с AI: {e}")
#                     messages.error(request, "Не удалось выполнить анализ с AI.")

#             if request.method == "POST" and "news_overview" in request.POST:
#                 calendar_events = get_investing_calendar()
#                 news_items = get_fxstreet_news()
#                 messages_to_openai = [
#                     {"role": "system", "content": "Ты аналитик по фундаментальному анализу. Дай обзор ключевых новостей и событий, и укажи, на какой валютной паре стоит сосредоточить внимание для торговли сегодня."},
#                     {"role": "user", "content": f"Календарь: {calendar_events}\nНовости: {news_items}"},
#                 ]
#                 response = openai.ChatCompletion.create(model="gpt-4o", messages=messages_to_openai)
#                 analysis = response["choices"][0]["message"]["content"].strip()
#                 context["news_analysis"] = analysis
#                 # Вместо символа задаем явное значение, например "Новости экономики"
#                 recommendation = Recommendation(symbol="Новости экономики", analysis=analysis)
#                 recommendation.save()


#             if request.method == "POST" and "deep_tech_analyst" in request.POST:
#                 indicators_history = get_indicators_data_history(symbol, "M15", count=20)

#                 messages_to_openai = [
#                     {"role": "system", "content": "Ты технический аналитик. Анализируй рынок по индикаторам и свечам."},
#                     {"role": "user", "content": f"История индикаторов и свечей:\n{indicators_history}"},
#                 ]
#                 response = openai.ChatCompletion.create(model="gpt-4o", messages=messages_to_openai)
#                 context["deep_tech_analysis"] = response["choices"][0]["message"]["content"]


#         finally:
#             shutdown_mt5()  # Отключаем MetaTrader 5

#     except Exception as e:
#         context["error"] = str(e)
#         logging.error(f"Ошибка в ai_analysis: {e}")

#     return render(request, "ai_analysis.html", context)

from django.shortcuts import render
from django.contrib import messages
from django.utils import timezone
from django.core.cache import cache
import logging
import openai
from src.utils.mt5_utils import get_currency_tick, initialize_mt5, shutdown_mt5, get_account_and_positions, open_market_position, place_pending_order
from src.utils.investing_calendar import get_investing_calendar
from src.utils.rss_news import get_fxstreet_news
from src.trading.trading import analyze_strategies_for_timeframes
from src.trading.forex_pair import majors, metals, cryptocurrencies, stocks, indices, commodities
from polygon.models import Recommendation

def ai_analysis(request):
    # Получаем валютную пару из cookie или GET-запроса
    symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
    symbol = request.GET.get("symbol", symbol_from_cookie)

    # Кэширование результата для ускорения
    cache_key = f"ai_analysis_{symbol}"
    cached_data = cache.get(cache_key)
    if cached_data and request.method != "POST":
        return render(request, "ai_analysis.html", cached_data)

    timeframes = define_timeframes()
    context = {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
        "selected_pair": symbol,
    }
    all_symbols = majors + metals + cryptocurrencies + stocks + indices + commodities
    context["all_symbols"] = all_symbols

    try:
        initialize_mt5()  # Инициализируем MetaTrader 5
        try:
            # Получаем информацию об аккаунте и открытые позиции
            account_info, open_positions = get_account_and_positions()
            context.update(account_info)
            context["open_positions"] = open_positions

            # Получаем тик выбранной валютной пары (один раз)
            selected_pair_tick = get_currency_tick(symbol)
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для символа {symbol}.")
            context["tick_value"] = selected_pair_tick.get("tick_value", 0)
            context["selected_pair_tick"] = selected_pair_tick
            context["last_updated"] = timezone.now()

            # Выполнение анализа индикаторов для AI анализа
            (
                indicators_by_timeframe,
                ict_strategies,
                smc_strategies_by_timeframe,
                snr_strategies_by_timeframe,
            ) = analyze_strategies_for_timeframes(symbol, timeframes)
            context["indicators_by_timeframe"] = indicators_by_timeframe

            # Обработка POST-запросов
            if request.method == "POST":
                if "open_position" in request.POST:
                    try:
                        volume = float(request.POST.get("volume", 0.01))
                        direction = request.POST.get("direction", "buy")
                        take_profit = float(request.POST.get("take_profit", 0))
                        stop_loss = float(request.POST.get("stop_loss", 0))
                        result = open_market_position(symbol, volume, direction, take_profit, stop_loss)
                        if result:
                            messages.success(request, f"Позиция по {symbol} успешно открыта.")
                        else:
                            messages.error(request, f"Ошибка при открытии позиции по {symbol}.")
                    except Exception as e:
                        logging.error(f"Ошибка при открытии позиции по {symbol}: {e}")
                        messages.error(request, f"Не удалось открыть позицию по {symbol}: {str(e)}")

                elif "place_pending_order" in request.POST:
                    try:
                        volume = float(request.POST.get("volume", 0.01))
                        order_type = request.POST.get("order_type", "buy_limit")
                        price = float(request.POST.get("price", 0))
                        take_profit = float(request.POST.get("take_profit", 0))
                        stop_loss = float(request.POST.get("stop_loss", 0))
                        result = place_pending_order(symbol, volume, order_type, price, take_profit, stop_loss)
                        if result:
                            messages.success(request, f"Отложенный ордер по {symbol} успешно установлен.")
                        else:
                            messages.error(request, f"Ошибка при установке отложенного ордера по {symbol}.")
                    except Exception as e:
                        logging.error(f"Ошибка при установке отложенного ордера по {symbol}: {e}")
                        messages.error(request, f"Не удалось установить отложенный ордер по {symbol}: {str(e)}")

                elif "analyze_x3" in request.POST:
                    try:
                        from . import analyze_with_ai_x3  # Локальный импорт для избежания циклических зависимостей
                        result = analyze_with_ai_x3(request)
                        context["x3_analysis"] = result.json().get("analysis") if result.status_code == 200 else "Ошибка анализа x3"
                    except Exception as e:
                        logging.error(f"Ошибка в analyze_with_ai_x3: {e}")
                        context["x3_analysis"] = f"Ошибка: {str(e)}"

                elif "analyze_with_history" in request.POST:
                    try:
                        from . import appeal_to_ai_with_historical_data  # Локальный импорт
                        result = appeal_to_ai_with_historical_data(request)
                        context["historical_analysis"] = result.json().get("analysis") if result.status_code == 200 else "Ошибка анализа с историей"
                    except Exception as e:
                        logging.error(f"Ошибка в appeal_to_ai_with_historical_data: {e}")
                        context["historical_analysis"] = f"Ошибка: {str(e)}"

                elif "analyze_with_ai" in request.POST:
                    indicators_summary = {
                        timeframe: {
                            "rsi": indicators.get("rsi"),
                            "macd": indicators.get("macd"),
                            "signal": indicators.get("signal"),
                            "upper_band": indicators.get("upper_band"),
                            "lower_band": indicators.get("lower_band"),
                            "atr": indicators.get("atr"),
                            "stochastic": {
                                "K": indicators.get("stochastic_k"),
                                "D": indicators.get("stochastic_d"),
                            },
                            "fibonacci_levels": indicators.get("fibonacci_levels"),
                            "regression_channel": indicators.get("regression_channel"),
                            "vwap": indicators.get("vwap"),
                            "cci": indicators.get("cci"),
                            "mfi": indicators.get("mfi"),
                        } for timeframe, indicators in indicators_by_timeframe.items()
                    }

                    result = {
                        "symbol": symbol,
                        "current_price": selected_pair_tick.get("bid") or selected_pair_tick.get("ask"),
                        "indicators_summary": indicators_summary,
                        "economic_calendar": get_investing_calendar(),
                        "news": get_fxstreet_news(),
                        "strategies": {
                            "ICT": ict_strategies,
                            "SNR": snr_strategies_by_timeframe,
                            "SMC": smc_strategies_by_timeframe,
                        },
                    }

                    try:
                        from src.utils.ai_analytic import analyze_with_ai
                        ai_analysis_result = analyze_with_ai(result, get_investing_calendar(), get_fxstreet_news())
                        context["ai_analysis"] = ai_analysis_result
                    except Exception as e:
                        logging.error(f"Ошибка при выполнении анализа с AI: {e}")
                        messages.error(request, "Не удалось выполнить анализ с AI.")

                elif "news_overview" in request.POST:
                    calendar_events = get_investing_calendar()
                    news_items = get_fxstreet_news()
                    messages_to_openai = [
                        {"role": "system", "content": "Ты аналитик по фундаментальному анализу. Дай обзор ключевых новостей и событий, и укажи, на какой валютной паре стоит сосредоточить внимание для торговли сегодня."},
                        {"role": "user", "content": f"Календарь: {calendar_events}\nНовости: {news_items}"},
                    ]
                    response = openai.ChatCompletion.create(model="gpt-4o", messages=messages_to_openai)
                    analysis = response["choices"][0]["message"]["content"].strip()
                    context["news_analysis"] = analysis
                    recommendation = Recommendation(symbol="Новости экономики", analysis=analysis)
                    recommendation.save()

                elif "deep_tech_analyst" in request.POST:
                    from brain.optimized.optimized_indicators import get_indicators_data_history
                    indicators_history = get_indicators_data_history(symbol, "M15", count=20)
                    messages_to_openai = [
                        {"role": "system", "content": "Ты технический аналитик. Анализируй рынок по индикаторам и свечам."},
                        {"role": "user", "content": f"История индикаторов и свечей:\n{indicators_history}"},
                    ]
                    response = openai.ChatCompletion.create(model="gpt-4o", messages=messages_to_openai)
                    context["deep_tech_analysis"] = response["choices"][0]["message"]["content"]

            # Сохраняем контекст в кэш после обработки
            cache.set(cache_key, context, timeout=300)  # 5 минут

        finally:
            shutdown_mt5()  # Отключаем MetaTrader 5

    except Exception as e:
        error_msg = f"Ошибка при анализе {symbol}: {str(e)}"
        logging.error(error_msg)
        messages.error(request, error_msg)
        context["error"] = error_msg

    return render(request, "ai_analysis.html", context)

from django.http import JsonResponse
import json
import logging
from src.utils.mt5_utils import get_currency_tick, initialize_mt5, shutdown_mt5, get_rates_dataframe
from src.utils.ai_analytic import analyze_with_ai
from src.utils.investing_calendar import get_investing_calendar
from src.utils.rss_news import get_fxstreet_news
from polygon.models import Recommendation

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Определение analyze_with_ai_x3
def analyze_with_ai_x3(request):
    if request.method != "POST":
        return JsonResponse({"error": "Ожидается POST-запрос"}, status=400)

    try:
        symbol = request.POST.get("symbol", request.COOKIES.get("selected_pair", "XAUUSD"))
        timeframes = define_timeframes()

        initialize_mt5()
        try:
            tick = get_currency_tick(symbol)
            if not tick:
                raise Exception(f"Не удалось получить тик для {symbol}")
            current_price = tick.get("bid") or tick.get("ask")

            indicators_summary = {}
            for label, tf in timeframes.items():
                indicators = get_indicators_data(symbol, tf, num_values=3)
                indicators_summary[label] = {
                    "rsi": indicators.get("rsi", [])[-3:],
                    "macd": indicators.get("macd", [])[-3:],
                    "signal": indicators.get("signal", [])[-3:],
                    "upper_band": indicators.get("upper_band", [])[-3:],
                    "lower_band": indicators.get("lower_band", [])[-3:],
                    "atr": indicators.get("atr", [])[-3:],
                    "stochastic": {
                        "K": indicators.get("stochastic_k", [])[-3:],
                        "D": indicators.get("stochastic_d", [])[-3:],
                    },
                    "fibonacci_levels": indicators.get("fibonacci_levels", {}),
                    "regression_channel": indicators.get("regression_channel", {}),
                    "vwap": indicators.get("vwap", [])[-3:],
                    "cci": indicators.get("cci", [])[-3:],
                    "mfi": indicators.get("mfi", [])[-3:],
                }

            ohlc_data = get_rates_dataframe(symbol, mt5.TIMEFRAME_M15, period=10)
            ohlc_dict = ohlc_data.to_dict("records") if ohlc_data is not None else []

            economic_calendar = get_investing_calendar()
            news = get_fxstreet_news()

            result = {
                "symbol": symbol,
                "current_price": current_price,
                "indicators_summary": indicators_summary,
                "ohlc_data": ohlc_dict,
                "economic_calendar": economic_calendar,
                "news": news,
            }

            ai_analysis = analyze_with_ai(result, economic_calendar, news)
            recommendation = Recommendation(symbol=symbol, analysis=ai_analysis)
            recommendation.save()

            return JsonResponse({"analysis": ai_analysis})

        finally:
            shutdown_mt5()

    except Exception as e:
        logging.error(f"Ошибка в analyze_with_ai_x3: {e}")
        return JsonResponse({"error": str(e)}, status=500)

# def analyze_with_ai_x3(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "Ожидается POST-запрос"}, status=400)

#     try:
#         symbol = request.POST.get("symbol", request.COOKIES.get("selected_pair", "XAUUSD"))
#         timeframes = define_timeframes()

#         initialize_mt5()
#         try:
#             # Получаем текущую цену
#             tick = get_currency_tick(symbol)
#             if not tick:
#                 raise Exception(f"Не удалось получить тик для {symbol}")
#             current_price = tick.get("bid") or tick.get("ask")

#             # Получаем последние 3 значения индикаторов по всем таймфреймам
#             indicators_summary = {}
#             for label, tf in timeframes.items():
#                 indicators = get_indicators_data(symbol, tf, num_values=3)
#                 indicators_summary[label] = {
#                     "rsi": indicators.get("rsi", [])[-3:],
#                     "macd": indicators.get("macd", [])[-3:],
#                     "signal": indicators.get("signal", [])[-3:],
#                     "upper_band": indicators.get("upper_band", [])[-3:],
#                     "lower_band": indicators.get("lower_band", [])[-3:],
#                     "atr": indicators.get("atr", [])[-3:],
#                     "stochastic": {
#                         "K": indicators.get("stochastic_k", [])[-3:],
#                         "D": indicators.get("stochastic_d", [])[-3:],
#                     },
#                     "fibonacci_levels": indicators.get("fibonacci_levels", {}),
#                     "regression_channel": indicators.get("regression_channel", {}),
#                     "vwap": indicators.get("vwap", [])[-3:],
#                     "cci": indicators.get("cci", [])[-3:],
#                     "mfi": indicators.get("mfi", [])[-3:],
#                 }

#             # Получаем OHLC для последних 10 баров (например, на таймфрейме M15)
#             ohlc_data = get_rates_dataframe(symbol, mt5.TIMEFRAME_M15, period=10)
#             ohlc_dict = ohlc_data.to_dict("records") if ohlc_data is not None else []

#             # Получаем новости и календарь
#             economic_calendar = get_investing_calendar()
#             news = get_fxstreet_news()

#             # Формируем данные для OpenAI
#             result = {
#                 "symbol": symbol,
#                 "current_price": current_price,
#                 "indicators_summary": indicators_summary,
#                 "ohlc_data": ohlc_dict,
#                 "economic_calendar": economic_calendar,
#                 "news": news,
#             }

#             # Выполняем анализ
#             ai_analysis = analyze_with_ai(result, economic_calendar, news)

#             # Сохраняем рекомендацию
#             recommendation = Recommendation(symbol=symbol, analysis=ai_analysis)
#             recommendation.save()

#             return JsonResponse({"analysis": ai_analysis})

#         finally:
#             shutdown_mt5()

#     except Exception as e:
#         logging.error(f"Ошибка в analyze_with_ai_x3: {e}")
#         return JsonResponse({"error": str(e)}, status=500)

def analyze_with_historical_data(request):
    try:
        initialize_mt5()

        symbol = request.GET.get("symbol", "XAUUSD")
        timeframe = request.GET.get("timeframe", "D1")
        num_candles = int(request.GET.get("candles", 50))

        timeframe_mapping = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "H1": mt5.TIMEFRAME_H1,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
        }
        if timeframe not in timeframe_mapping:
            raise ValueError(f"Некорректный таймфрейм: {timeframe}")
        mapped_timeframe = timeframe_mapping[timeframe]

        tick_data = get_currency_tick(symbol)
        if tick_data is None:
            raise ValueError(f"Не удалось получить тик для символа {symbol}.")
        current_price = tick_data.get("bid") or tick_data.get("ask")

        ohlc_data = get_rates_dataframe(symbol, mapped_timeframe, num_candles)
        if ohlc_data.empty:
            raise ValueError(f"Нет данных для {symbol} и таймфрейма {timeframe}.")

        response_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": current_price,
            "ohlc_data": ohlc_data.to_dict("records"),
        }
        return JsonResponse(response_data, safe=False)

    except Exception as e:
        logging.error(f"Ошибка в analyze_with_historical_data: {e}")
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        shutdown_mt5()


# Страница торговли
def trade(request):
    context = {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
    }

    if request.method == "POST":
        # Логика открытия позиций, установки ордеров и уведомлений
        pass

    return render(request, "trade.html", context)


def dashboard(request):
    # Начальный контекст с категориями инструментов
    context = {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
    }

    # Получаем выбранный символ из GET параметра или используем значение по умолчанию
    symbol = request.GET.get("symbol", "EURUSD")
    context["symbol"] = symbol

    timeframes = define_timeframes()  # Получаем список таймфреймов для анализа

    try:
        initialize_mt5()  # Инициализируем MetaTrader 5
        try:
            # Получаем информацию об аккаунте и открытые позиции
            account_info, open_positions = get_account_and_positions()
            context.update(account_info)
            context["open_positions"] = open_positions

            # Получаем экономический календарь и новости
            context["economic_calendar"] = get_investing_calendar()
            context["rss_news"] = get_fxstreet_news()
            context["last_updated"] = timezone.now()

            # Получаем тик выбранной валютной пары
            selected_pair_tick = get_currency_tick(symbol)
            context.update(
                {
                    "selected_pair_tick": selected_pair_tick,
                    "selected_pair": symbol,
                }
            )

            # Анализ стратегий и регрессионного канала для всех таймфреймов
            (
                indicators_by_timeframe,
                ict_strategies_by_timeframe,
                smc_strategies_by_timeframe,
                snr_strategies_by_timeframe,
            ) = analyze_strategies_for_timeframes(symbol, timeframes)

            regression_channel_by_timeframe = {}
            for label, timeframe in timeframes.items():
                regression_result = calculate_regression_channel(symbol, timeframe)
                if regression_result:
                    regression_channel_by_timeframe[label] = regression_result
                else:
                    logging.warning(
                        f"Регрессионный анализ не выполнен для {symbol} на таймфрейме {label}"
                    )

            # Обновляем контекст для передачи в шаблон
            context.update(
                {
                    "indicators_by_timeframe": indicators_by_timeframe,
                    "ict_strategies_by_timeframe": ict_strategies_by_timeframe,
                    "smc_strategies_by_timeframe": smc_strategies_by_timeframe,
                    "snr_strategies_by_timeframe": snr_strategies_by_timeframe,
                    "regression_channel_by_timeframe": regression_channel_by_timeframe,
                }
            )

            # Если был отправлен запрос на глубокий анализ с AI
            if request.method == "POST" and "analyze_with_ai" in request.POST:
                indicators = indicators_by_timeframe.get("15m", {})
                context["indicators"] = indicators

                try:
                    # Формируем результат анализа для отправки в OpenAI
                    result = {
                        "symbol": symbol,
                        "current_price": selected_pair_tick.get("bid")
                        or selected_pair_tick.get("ask"),
                        "rsi": indicators.get("rsi"),
                        "macd": indicators.get("macd"),
                        "signal": indicators.get("signal"),
                        "upper_band": indicators.get("upper_band"),
                        "lower_band": indicators.get("lower_band"),
                        "atr": indicators.get("atr"),
                        "stochastic": {
                            "K": indicators.get("stochastic_k"),
                            "D": indicators.get("stochastic_d"),
                        },
                        "fibonacci_levels": indicators.get("fibonacci_levels"),
                        "regression_channel": indicators.get("regression_channel"),
                        "vwap": indicators.get("vwap"),
                        "cci": indicators.get("cci"),
                        "mfi": indicators.get("mfi"),
                    }

                    # Логируем отсутствующие значения
                    for key, value in result.items():
                        if value is None:
                            logging.warning(
                                f"Отсутствуют данные для {key} в символе {symbol}"
                            )

                    # Выполняем анализ с использованием OpenAI
                    ai_analysis = analyze_with_ai(
                        result, context["economic_calendar"], context["rss_news"]
                    )
                    context["ai_analysis"] = ai_analysis
                except Exception as e:
                    logging.error(f"Ошибка при выполнении анализа с AI: {e}")
                    messages.error(request, "Не удалось выполнить анализ с AI.")

            # --- Обработка открытия позиции или установки отложенного ордера ---
            if request.method == "POST" and "open_position" in request.POST:
                try:
                    symbol = request.POST.get("symbol", "EURUSD")
                    volume = float(request.POST.get("volume", 0.01))
                    order_type = request.POST.get("direction", "buy")
                    take_profit = float(request.POST.get("take_profit", 0))
                    stop_loss = float(request.POST.get("stop_loss", 0))
                    result = open_market_position(
                        symbol, volume, order_type, take_profit, stop_loss
                    )
                    if result:
                        messages.success(
                            request, f"Позиция по {symbol} успешно открыта."
                        )
                    else:
                        messages.error(
                            request, f"Ошибка при открытии позиции по {symbol}."
                        )
                except Exception as e:
                    logging.error(f"Ошибка при открытии позиции по {symbol}: {e}")
                    messages.error(request, f"Не удалось открыть позицию по {symbol}.")

            if request.method == "POST" and "place_pending_order" in request.POST:
                try:
                    symbol = request.POST.get("symbol", "EURUSD")
                    volume = float(request.POST.get("volume", 0.01))
                    order_type = request.POST.get("order_type", "buy_limit")
                    price = float(request.POST.get("price", 0))
                    take_profit = float(request.POST.get("take_profit", 0))
                    stop_loss = float(request.POST.get("stop_loss", 0))
                    result = place_pending_order(
                        symbol, volume, order_type, price, take_profit, stop_loss
                    )
                    if result:
                        messages.success(
                            request, f"Отложенный ордер по {symbol} успешно установлен."
                        )
                    else:
                        messages.error(
                            request,
                            f"Ошибка при установке отложенного ордера по {symbol}.",
                        )
                except Exception as e:
                    logging.error(
                        f"Ошибка при установке отложенного ордера по {symbol}: {e}"
                    )
                    messages.error(
                        request, f"Не удалось установить отложенный ордер по {symbol}."
                    )

        finally:
            shutdown_mt5()  # Отключаем MetaTrader 5

    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в dashboard: {e}")

    return render(request, "dashboard.html", context)


# --- Дополнительные функции ---
def handle_message(request, success, success_message, error_message):
    """Универсальная функция для отправки сообщений о статусе операций"""
    if success:
        messages.success(request, success_message)
    else:
        messages.error(request, error_message)


def define_timeframes():
    """Определение всех таймфреймов для анализа"""
    return {
        "1m": mt5.TIMEFRAME_M1,
        "3m": mt5.TIMEFRAME_M3,
        "5m": mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15,
        "30m": mt5.TIMEFRAME_M30,
        "1h": mt5.TIMEFRAME_H1,
        "4h": mt5.TIMEFRAME_H4,
        "1d": mt5.TIMEFRAME_D1,
        "1w": mt5.TIMEFRAME_W1,
    }


def get_account_and_positions():
    """Получение информации о счете и открытых позициях"""
    account_info = get_account_info()
    open_positions = get_open_positions()
    return account_info, open_positions


def run_strategy(symbol, timeframe, strategy_function, strategy_name):
    """Запуск стратегии и логирование"""
    try:
        result = strategy_function(symbol, timeframe)

        return result
    except Exception as e:
        # logging.error(f"Ошибка в стратегии {strategy_name} для {timeframe}: {e}")
        return {}


def recommendations_list(request):
    open_positions = get_open_positions()
    recommendations = Recommendation.objects.all().order_by("-created_at")

    # Логирование данных
    if not recommendations.exists():
        logging.error("Нет рекомендаций в базе данных")
    else:
        logging.info(f"Количество рекомендаций: {recommendations.count()}")
        for rec in recommendations:
            logging.info(f"Recommendation: {rec.symbol}, {rec.analysis[:50]}...")
    # Пагинация: 15 рекомендаций на страницу
    paginator = Paginator(recommendations, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "recommendations": recommendations,
        "page_obj": page_obj,  # Передаем объект страницы в контекст
    }

    return render(request, "recommendations_list.html", context)


def test_view(request):
    return render(request, "test.html")


def profile_info_view(request):
    return render(request, "rofile-information.html")


def statistics_view(request):
    try:
        account_info = get_account_info()
        # Получение данных для графиков
        balance_history = [account_info["balance"] for _ in range(14)]
        date_labels = [
            (datetime.now() - timedelta(days=i)).strftime("%d-%m-%Y") for i in range(14)
        ]
        context = {
            "balance_history": balance_history,
            "date_labels": date_labels,
        }
    except Exception as e:
        context = {"error": str(e)}
    return render(request, "statistics.html", context)


def trade_history(request):
    try:
        positions = get_open_positions()
        context = {"positions": positions}
    except Exception as e:
        context = {"error": str(e)}
    return render(request, "trade_history.html", context)


def trade_calculator(request):
    if request.method == "POST":
        # Получаем данные из формы
        volume = float(request.POST.get("volume"))
        entry_price = float(request.POST.get("entry_price"))
        stop_loss = float(request.POST.get("stop_loss"))
        take_profit = float(request.POST.get("take_profit"))
        # Расчет риска
        risk = abs(entry_price - stop_loss) * volume
        reward = abs(take_profit - entry_price) * volume
        context = {"risk": risk, "reward": reward}
    else:
        context = {}
    return render(request, "trade_calculator.html", context)


def trade(request):
    if request.method == "POST":
        symbol = request.POST.get("symbol")
        volume = float(request.POST.get("volume"))
        direction = request.POST.get("direction")  # "buy" or "sell"
        result = open_market_position(symbol, volume, direction)
        messages.success(request, "Позиция открыта!" if result else "Ошибка!")
    return render(request, "trade.html")


def get_symbol_data(request):
    symbol = request.GET.get("symbol")
    if not symbol:
        return JsonResponse({"error": "Символ не указан"}, status=400)

    try:
        data = get_currency_tick(symbol)  # Из mt5_utils.py
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_historical_data(request):
    symbol = request.GET.get("symbol")
    if not symbol:
        return JsonResponse({"error": "Символ не указан"}, status=400)
    try:
        data = get_historical_account_data()  # Используем функцию из mt5_utils.py
        return JsonResponse(
            {"dates": [d["date"] for d in data], "prices": [d["balance"] for d in data]}
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_statistics_data(request):
    symbol = request.GET.get("symbol")
    if not symbol:
        return JsonResponse({"error": "Символ не указан"}, status=400)
    try:
        data = get_trading_profit_history()  # Используем функцию из mt5_utils.py
        statistics = [
            {"date": str(i), "profit": p, "loss": l}
            for i, (p, l) in enumerate(zip(data, data))
        ]
        return JsonResponse(statistics, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def statistics_view(request):
    # Подключение к MetaTrader
    initialize()

    # Все операции
    deals = history_deals_get()
    all_deals = [{"profit": deal.profit, "date": deal.time} for deal in deals]

    # Данные для графика
    profits = [deal["profit"] for deal in all_deals]
    dates = [deal["date"] for deal in all_deals]

    # Баланс и капитал
    account_data = account_info()
    balance = account_data.balance
    equity = account_data.equity

    return render(
        request,
        "statistics.html",
        {
            "profits": profits,
            "dates": dates,
            "balance": balance,
            "equity": equity,
        },
    )


def profit_loss_history(request):
    try:
        # Получение параметров из GET-запроса
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        # Конвертация строковых дат в формат datetime
        start_date = (
            datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
        )
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else None

        # Получение данных
        history = get_trade_history(start_date, end_date)

        # Преобразование данных для шаблона
        profits = [deal["profit"] for deal in history]
        dates = [datetime.fromtimestamp(deal["time"]) for deal in history]
        symbols = [deal["symbol"] for deal in history]

        # Объединённый список
        combined_data = zip(dates, symbols, profits)

        # Группировка по дням недели
        days_of_week = {
            day: 0 for day in calendar.day_name
        }  # {'Monday': 0, 'Tuesday': 0, ...}
        for date, profit in zip(dates, profits):
            day_name = calendar.day_name[date.weekday()]
            days_of_week[day_name] += profit

        print("Данные для графика по дням недели:", days_of_week)
        labels = list(days_of_week.keys())
        data = list(days_of_week.values())

        filtered_profits = [profit for profit in profits if profit != 0]
        filtered_combined_data = [
            (date, symbol, profit)
            for date, symbol, profit in zip(dates, symbols, profits)
            if profit != 0  # Исключаем строки с прибылью/убытком 0
        ]

        context = {
            "days_of_week": days_of_week,
            "combined_data": filtered_combined_data,
            "profits": filtered_profits,
            "dates": [date.strftime("%Y-%m-%d %H:%M:%S") for date in dates],
            "symbols": symbols,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "labels": labels,  # Добавляем labels
            "data": data,  # Добавляем data
            "error": None,
        }
    except Exception as e:
        context = {
            "days_of_week": {},
            "combined_data": [],
            "profits": [],
            "dates": [],
            "symbols": [],
            "start_date": None,
            "end_date": None,
            "labels": [],
            "data": [],
            "error": str(e),
        }

    return render(request, "statistics.html", context)


def get_dashboard_indicators(symbol, timeframe, trend="up", num_values=1):
    """
    Получение всех индикаторов для дашборда.
    """
    try:
        # Преобразование num_values в int
        num_values = (
            int(num_values)
            if isinstance(num_values, str) and num_values.isdigit()
            else num_values
        )

        # Получение индикаторов
        indicators = get_indicators_data(symbol, timeframe, trend, num_values)

        # Проверяем, есть ли данные
        if not indicators or not indicators.get("ohlc"):
            raise ValueError(
                f"Не удалось получить данные индикаторов для {symbol} на {timeframe}."
            )

        # Формируем данные для дашборда
        dashboard_data = {
            "symbol": symbol,
            "timeframe": timeframe,
            "indicators": {
                "MACD": indicators.get("macd", [None]),
                "RSI": indicators.get("rsi", [None]),
                "ATR": indicators.get("atr", [None]),
                "Pivot": indicators.get("pivot", []),
                "Pivot Resistance": indicators.get("pp_resistance", []),
                "Pivot Support": indicators.get("pp_support", []),
                "Bollinger Bands": {
                    "SMA": indicators.get("sma", [None]),
                    "Upper Band": indicators.get("upper_band", [None]),
                    "Lower Band": indicators.get("lower_band", [None]),
                },
                "VWAP": indicators.get("vwap", [None]),
                "CCI": indicators.get("cci", [None]),
                "MFI": indicators.get("mfi", [None]),
                "Stochastic": {
                    "K": indicators.get("stochastic_k", [None]),
                    "D": indicators.get("stochastic_d", [None]),
                },
                "Fibonacci Levels": indicators.get("fib_levels", {}),
            },
        }
        return dashboard_data

    except ValueError as ve:
        logging.warning(f"Проблема с данными: {ve}")
        return {"error": str(ve)}

    except Exception as e:
        logging.exception(f"Ошибка при сборе данных для дашборда: {e}")
        return {"error": str(e)}


def instrument_analysis(request):
    """
    Обобщённая страница для вывода технических индикаторов и структуры рынка
    по всем таймфреймам одновременно (или выборочно).
    """
    open_positions = get_open_positions()  # Если нужно

    # 1) Получаем текущий символ (из GET, потом cookie, иначе XAUUSD)
    symbol = request.GET.get("symbol", request.COOKIES.get("selected_pair", "XAUUSD"))

    # 2) Определяем, сколько баров подгружаем (по умолчанию 1)
    try:
        num_values_int = int(request.GET.get("num_values", "1"))
    except ValueError:
        num_values_int = 1

    # 3) Какие таймфреймы обрабатываем?
    requested_tf = request.GET.get("timeframe", "ALL")
    all_timeframes = define_timeframes()  # Например, {"M1": "M1", "M5": "M5", ...}
    if requested_tf.upper() != "ALL" and requested_tf in all_timeframes:
        timeframes = {requested_tf: all_timeframes[requested_tf]}
    else:
        timeframes = all_timeframes

    # 4) Сколько последних значений (recent_count) для индикаторов показать?
    try:
        recent_count = int(request.GET.get("recent_count", "3"))
    except ValueError:
        recent_count = 3

    # Базовый контекст
    context = {
        "selected_pair": symbol,
        "num_values": num_values_int,
        "requested_timeframe": requested_tf,
        "recent_count": recent_count,
    }

    # 5) Подготовка словарей-накопителей
    structure_by_timeframe = {}
    indicators_by_timeframe = {}
    pivot_points_by_timeframe = {}
    market_structure_by_timeframe = {}
    fibonacci_by_timeframe = {}

    # Словари со значениями по умолчанию
    default_structure = {
        "trend": "Нет данных",
        "support": None,
        "resistance": None,
    }
    default_indicators = {
        "atr": [],
        "mfi": [],
        "cci": [],
        "stochastic_k": [],
        "stochastic_d": [],
        "sma": [],
        "macd": [],
        "signal": [],
        "rsi": [],
        "ohlc": [],
        "pivot": [],
        "pp_resistance": [],
        "pp_support": [],
        "upper_band": [],
        "lower_band": [],
        "vwap": [],
        # и т.д., если есть ещё
    }
    default_pivot_points = [
        {
            "pivot": None,
            "pp_resistance": [None] * 3,
            "pp_support": [None] * 3,
        }
    ]
    default_fibonacci = {
        "fib_levels": {},
        "fib_ranges": {},
        "local_high": None,
        "local_low": None,
        "absolute_high": None,
        "absolute_low": None,
        "trend": None,
    }

    # 6) Подключаемся к MT5 и собираем данные
    try:
        initialize_mt5()
        try:
            # Проверяем тик для выбранного символа
            selected_pair_tick = get_currency_tick(symbol)
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для символа {symbol}.")
            context["selected_pair_tick"] = selected_pair_tick

            # Цикл по таймфреймам
            for label, tf in timeframes.items():
                # 6.1) Структура инструмента (support/resistance/trend)
                instrument_data = create_instrument_structure(
                    symbol, tf, bars=num_values_int
                )
                if not instrument_data:
                    instrument_data = dict(default_structure)

                instrument_data["trend_color"] = get_color_for_trend(
                    instrument_data.get("trend", "Нет данных")
                )

                # 6.2) Индикаторы
                ind_data = get_indicators_data(symbol, tf, num_values=num_values_int)
                if not ind_data:
                    ind_data = dict(default_indicators)

                # Урезаем списки индикаторов до recent_count (если нужно)
                for key, val in ind_data.items():
                    if isinstance(val, list) and len(val) > recent_count:
                        ind_data[key] = val[-recent_count:]

                # 6.3) Pivot Points
                pivot_points = calculate_pivot_points(symbol, tf, num_values_int)
                if not pivot_points:
                    pivot_points = default_pivot_points

                # 6.4) Фибоначчи
                fib_for_tf = calculate_fibonacci_levels(
                    symbol, tf, bars=500, local_bars=100
                )
                if not fib_for_tf:
                    fib_for_tf = dict(default_fibonacci)

                # 6.5) Маркет структура (абсолютные / локальные экстремумы)
                ms = identify_market_structure(symbol, tf)
                if not ms:
                    ms = dict(default_structure)

                ms["trend_color"] = get_color_for_trend(ms.get("trend", "Нет данных"))
                # Добавим экстремумы (если identify_market_structure их возвращает)
                ms["absolute_high"] = ms.get("absolute_high", None)
                ms["absolute_low"] = ms.get("absolute_low", None)
                ms["local_high"] = ms.get("local_high", None)
                ms["local_low"] = ms.get("local_low", None)

                # Сохраняем данные в словари
                structure_by_timeframe[label] = instrument_data
                indicators_by_timeframe[label] = ind_data
                pivot_points_by_timeframe[label] = pivot_points
                fibonacci_by_timeframe[label] = fib_for_tf
                market_structure_by_timeframe[label] = ms

        finally:
            shutdown_mt5()

    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в technical_analysis_indicators: {e}")

    # 7) Дополняем контекст
    context.update(
        {
            "structure_by_timeframe": structure_by_timeframe,
            "indicators_by_timeframe": indicators_by_timeframe,
            "pivot_points_by_timeframe": pivot_points_by_timeframe,
            "market_structure_by_timeframe": market_structure_by_timeframe,
            "fibonacci_by_timeframe": fibonacci_by_timeframe,
        }
    )

    # 8) Формируем итоговый merged_data_by_timeframe — удобная структура «всё в одном»
    merged_data_by_timeframe = []
    for timeframe in indicators_by_timeframe:
        # Берём подготовленные данные
        ind = indicators_by_timeframe.get(timeframe, {})
        instr = structure_by_timeframe.get(timeframe, {})
        ms = market_structure_by_timeframe.get(timeframe, {})
        fib = fibonacci_by_timeframe.get(timeframe, {})

        # Пример дополнительных вычислений
        fib_pivot_levels = {}
        if fib:
            fib_pivot_levels = (
                calculate_fibonacci_pivot_points(
                    fib.get("local_high", 0),
                    fib.get("local_low", 0),
                    fib.get("absolute_high", 0),
                )
                or {}
            )

        nearest_levels = {}
        if fib_pivot_levels and "current_price" in fib:
            nearest_levels = (
                find_nearest_levels(fib_pivot_levels, fib["current_price"]) or {}
            )

        time_zones = {}
        if fib.get("start_time") and fib.get("end_time"):
            time_zones = (
                calculate_fibonacci_time_zones(fib["start_time"], fib["end_time"]) or {}
            )

        # Собираем в единый dict
        ote_data = calculate_ote(symbol, tf, trend="up")
        fibonacci_data = fibonacci_by_timeframe.get(tf, {})
        merged_data_by_timeframe.append(
            {
                "timeframe": timeframe,
                "indicators": ind,
                "structure": instr,  # create_instrument_structure
                "market_structure": ms,  # identify_market_structure
                "fibonacci": fib,  # calculate_fibonacci_levels
                "fib_pivot_levels": fib_pivot_levels,
                "nearest_levels": nearest_levels,
                "time_zones": time_zones,
                "ote": ote_data,  # Добавляем данные OTE
            }
        )

    context["merged_data_by_timeframe"] = merged_data_by_timeframe

    return render(request, "technical_analysis/instrument_analysis.html", context)


# НАЧИНАЮТСЯ ПОКАЗЫ ТРЕНДОВ ПО ИНДИКАТОРНЫМ ПОКАЗАТЕЛЯМ
def calculate_stochastic_trend(k, d):
    if k > d:
        return "uptrend"
    elif k < d:
        return "downtrend"
    return "range"


######## ######## ####### ##########
########## ### ##########


def trade_chart(request):
    """Генерация графика для веб-интерфейса"""
    open_positions = get_open_positions()
    symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")

    # Получаем валютную пару из GET-запроса или используем значение из cookie
    symbol = request.GET.get("symbol", symbol_from_cookie)
    timeframes = define_timeframes()
    # The above Python code is retrieving a timeframe value from a GET request parameter named
    # "timeframe". If the parameter is not provided in the request, it defaults to "15m".
    selected_timeframe = request.GET.get("timeframe", "15m")

    # Преобразуем в числовой код таймфрейма (например, mt5.TIMEFRAME_M15)
    timeframe = timeframes.get(selected_timeframe, mt5.TIMEFRAME_M15)

    # Получаем исторические данные (OHLC)
    df = fetch_ohlc_data(symbol, timeframe, 100)
    if df is None or df.empty:
        return JsonResponse({"error": "Нет данных"}, status=400)

    print("✅ DEBUG: Полученные данные")
    print(df.head())  # Проверяем, передаются ли данные

    # Генерация графика свечей
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Свечи",
        )
    )

    # Добавляем ключевые уровни
    market_structure = identify_market_structure(symbol, timeframe)
    if market_structure:
        fig.add_hline(
            y=market_structure["support"],
            line=dict(color="blue", width=1),
            name="Support",
        )
        fig.add_hline(
            y=market_structure["resistance"],
            line=dict(color="red", width=1),
            name="Resistance",
        )

    # Уровни Фибоначчи
    fib_levels = calculate_fibonacci_levels(symbol, timeframe)
    if fib_levels:
        for level, price in fib_levels["fib_levels"].items():
            fig.add_hline(
                y=price,
                line=dict(color="gold", width=1, dash="dot"),
                name=f"Fibo {level}",
            )

    # Индикаторы (RSI и MACD)
    rsi = calculate_rsi(symbol, timeframe)
    macd, signal = calculate_macd(symbol, timeframe)

    # Создаём JSON-ответ
    response_data = {
        "graph": fig.to_json(),
        "rsi": list(rsi),
        "macd": list(macd),
        "signal": list(signal),
    }
    return JsonResponse(response_data)


def trade_chart_page(request):
    """Рендеринг HTML страницы"""
    # return render(request, "technical_analysis/plotly_chart.html")


### ### ###        ###    ###
### ### ####       #####  ###
### ### #####      ##########
### ### #####      ### ######
### ### ####       ###   ####
### ### ###        ###    ###


# Список таймфреймов, доступных для выбора
AVAILABLE_TIMEFRAMES = ["M1", "M5", "M15", "H1", "D1", "W1"]


def plotly_chart_view(request: HttpRequest) -> HttpResponse:
    """
    Представление для страницы с интерактивным графиком Plotly.
    Если выбран параметр timeframe="all", генерируются графики для всех доступных таймфреймов.
    В противном случае генерируется график для выбранного таймфрейма.
    Страница содержит три секции:
      - Японские свечи (с возможной линией SMA)
      - Осцилляторы (RSI, MACD и MACD Signal)
      - Элементы масштабирования (Range Slider)
    """
    symbol = request.GET.get("symbol", "EURUSD")
    selected_timeframe = request.GET.get("timeframe", "M15")
    try:
        # Параметр формы называется "candles" (согласно HTML) – используем его,
        # если его нет, то по умолчанию 50
        num_candles = int(request.GET.get("candles", 50))
    except ValueError:
        num_candles = 50

    # Если выбран "all", то формируем список таймфреймов, иначе только один
    if selected_timeframe.lower() == "all":
        timeframes = AVAILABLE_TIMEFRAMES
    else:
        timeframes = [selected_timeframe]

    charts = {}
    for tf in timeframes:
        try:
            # Генерируем агрегированные данные для данного таймфрейма
            data = generate_plotly_data(symbol, tf, num_candles)
        except Exception as e:
            logger.error(f"Ошибка при генерации данных для {tf}: {e}")
            charts[tf] = f"Ошибка при генерации данных для {tf}."
            continue

        ohlc = data.get("ohlc")
        if ohlc is None:
            logger.error(f"Нет данных для построения графика для {symbol} {tf}")
            charts[tf] = f"Нет данных для построения графика для {tf}."
            continue

        # Если получены данные в виде DataFrame, преобразуем в список словарей
        if isinstance(ohlc, pd.DataFrame):
            if ohlc.empty:
                logger.error(f"Пустой DataFrame для OHLC {symbol} {tf}")
                charts[tf] = f"Нет данных для построения графика для {tf}."
                continue
            ohlc = ohlc.round(5).to_dict(orient="records")

        try:
            dates = [item["time"] for item in ohlc]
            open_prices = [item["open"] for item in ohlc]
            high_prices = [item["high"] for item in ohlc]
            low_prices = [item["low"] for item in ohlc]
            close_prices = [item["close"] for item in ohlc]
        except Exception as e:
            logger.error(f"Ошибка при обработке OHLC данных для {symbol} {tf}: {e}")
            charts[tf] = f"Ошибка при обработке данных для {tf}."
            continue

        # Получаем осцилляторы (RSI, MACD, MACD Signal)
        rsi = data.get("rsi", [])
        macd = data.get("macd", [])
        macd_signal = data.get("macd_signal", [])

        # Создаем фигуру с субплотами: верхняя строка — свечи, нижняя — осцилляторы
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3],
            subplot_titles=(f"Японские свечи ({tf})", "Осцилляторы"),
        )

        # Секция 1: Японские свечи
        candle = go.Candlestick(
            x=dates,
            open=open_prices,
            high=high_prices,
            low=low_prices,
            close=close_prices,
            name="Candlestick",
        )
        fig.add_trace(candle, row=1, col=1)

        # Добавляем SMA, если данные есть
        moving_average_data = data.get("moving_average", [])
        if moving_average_data:
            if isinstance(moving_average_data, pd.DataFrame):
                moving_average_data = moving_average_data.round(5).to_dict(
                    orient="records"
                )
            ma_dates = [item["time"] for item in moving_average_data]
            ma_values = [item["moving_average"] for item in moving_average_data]
            ma_line = go.Scatter(
                x=ma_dates,
                y=ma_values,
                mode="lines",
                line=dict(color="blue", width=1),
                name="SMA",
            )
            fig.add_trace(ma_line, row=1, col=1)

        # Секция 2: Осцилляторы
        if rsi:
            rsi_trace = go.Scatter(
                x=dates[-len(rsi) :],
                y=rsi,
                mode="lines",
                line=dict(color="orange", width=1),
                name="RSI",
            )
            fig.add_trace(rsi_trace, row=2, col=1)
        if macd and macd_signal:
            macd_trace = go.Scatter(
                x=dates[-len(macd) :],
                y=macd,
                mode="lines",
                line=dict(color="green", width=1),
                name="MACD",
            )
            macd_signal_trace = go.Scatter(
                x=dates[-len(macd_signal) :],
                y=macd_signal,
                mode="lines",
                line=dict(color="red", width=1),
                name="MACD Signal",
            )
            fig.add_trace(macd_trace, row=2, col=1)
            fig.add_trace(macd_signal_trace, row=2, col=1)

        # Секция 3: Масштабирование – включаем Range Slider
        fig.update_layout(
            xaxis=dict(
                rangeselector=dict(
                    buttons=list(
                        [
                            dict(count=1, label="1d", step="day", stepmode="backward"),
                            dict(count=7, label="1w", step="day", stepmode="backward"),
                            dict(
                                count=1, label="1m", step="month", stepmode="backward"
                            ),
                            dict(step="all"),
                        ]
                    )
                ),
                rangeslider=dict(visible=True),
                type="date",
            ),
            margin=dict(l=40, r=40, t=40, b=40),
            height=700,
            title=f"График для {symbol} {tf} (последних {num_candles} баров)",
        )

        # Преобразуем фигуру в HTML
        plot_div = fig.to_html(full_html=False)
        charts[tf] = plot_div

    # Передаем в шаблон:
    context = {
        "charts": charts,
        "selected_timeframe": selected_timeframe,
        "selected_candles": num_candles,
        "timeframes": ["all"] + AVAILABLE_TIMEFRAMES,
        "symbol": symbol,
    }
    return render(request, "technical_analysis/plotly_chart.html", context)


def logout_user_properly(request):
    logout(request)
    request.session.flush()


def logout_view(request):
    logout_user_properly(request)
    return redirect("login")
