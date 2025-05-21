# TradeSpace_v5/polygon/views.py <-- только представления для страниц с AI. (Файл является тестовым)
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
from polygon.models import Recommendation

# что то
from MetaTrader5 import initialize, history_deals_get, account_info
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)

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

def get_historical_indicators(symbol, timeframe, count=5):
    ohlc_data = fetch_ohlc_data(symbol, timeframe, count)
    if not ohlc_data:
        return {"error": f"Нет данных по {symbol} на {timeframe}"}

    indicators_history = get_indicators_data_history(symbol, "M15", count=5)
    indicators["ohlc"] = ohlc_data  # У тебя fetch_ohlc_data уже возвращает список
    return indicators


# Страница AI анализа
def ai_analysis(request):
    # Получаем валютную пару из cookie
    symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")

    # Получаем валютную пару из GET-запроса или используем значение из cookie
    symbol = request.GET.get("symbol", symbol_from_cookie)
    timeframes = define_timeframes()
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
        initialize_mt5()  # Инициализируем MetaTrader 5
        try:
            # Получаем информацию об аккаунте и открытые позиции
            account_info, open_positions = get_account_and_positions()
            context.update(account_info)
            context["open_positions"] = open_positions

            # Получаем тик выбранной валютной пары
            context["last_updated"] = timezone.now()
            selected_pair_tick = get_currency_tick(symbol)
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для символа {symbol}.")
            tick_value = selected_pair_tick.get(
                "tick_value", 0
            )  # Добавляем стоимость тика
            context["tick_value"] = tick_value

            # Получаем тик выбранной валютной пары
            selected_pair_tick = get_currency_tick(symbol)
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для символа {symbol}.")

            context["selected_pair_tick"] = selected_pair_tick

            # Выполнение анализа индикаторов для AI анализа
            (
                indicators_by_timeframe,
                ict_strategies,
                smc_strategies_by_timeframe,
                snr_strategies_by_timeframe,
            ) = analyze_strategies_for_timeframes(symbol, timeframes)

            # Обновляем контекст для шаблона
            context.update(
                {
                    "indicators_by_timeframe": indicators_by_timeframe,
                }
            )

            # --- Обработка открытия позиции или установки отложенного ордера ---
            if request.method == "POST" and "open_position" in request.POST:
                try:
                    volume = float(request.POST.get("volume", 0.01))
                    direction = request.POST.get("direction", "buy")
                    take_profit = float(request.POST.get("take_profit", 0))
                    stop_loss = float(request.POST.get("stop_loss", 0))
                    result = open_market_position(
                        symbol, volume, direction, take_profit, stop_loss
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

            # Выполнение анализа с помощью AI, если запрос поступил
            if request.method == "POST" and "analyze_x3" in request.POST:
                # Логика для анализа x3
                result = analyze_with_ai_x3(symbol)
                context["x3_analysis"] = result

            if request.method == "POST" and "analyze_with_history" in request.POST:
                # Логика для анализа с историей
                result = appeal_to_ai_with_historical_data(symbol)
                context["historical_analysis"] = result

            if request.method == "POST" and "analyze_with_ai" in request.POST:
                # Собираем индикаторы для всех таймфреймов
                indicators_summary = {}
                for timeframe, indicators in indicators_by_timeframe.items():
                    indicators_summary[timeframe] = {
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

                # Формируем данные для отправки в OpenAI
                result = {
                    "symbol": symbol,
                    "current_price": selected_pair_tick.get("bid")
                    or selected_pair_tick.get("ask"),
                    "indicators_summary": indicators_summary,  # Все данные по таймфреймам
                    "economic_calendar": get_investing_calendar(),
                    "news": get_fxstreet_news(),
                    "strategies": {
                        "ICT": ict_strategies,
                        "SNR": snr_strategies_by_timeframe,
                        "SMC": smc_strategies_by_timeframe,
                    },
                }

                try:
                    # Выполняем анализ с использованием OpenAI
                    ai_analysis = analyze_with_ai(
                        result, get_investing_calendar(), get_fxstreet_news()
                    )
                    context["ai_analysis"] = ai_analysis
                except Exception as e:
                    logging.error(f"Ошибка при выполнении анализа с AI: {e}")
                    messages.error(request, "Не удалось выполнить анализ с AI.")

            if request.method == "POST" and "news_overview" in request.POST:
                calendar_events = get_investing_calendar()
                news_items = get_fxstreet_news()
                messages_to_openai = [
                    {"role": "system", "content": "Ты аналитик по фундаментальному анализу. Дай обзор ключевых новостей и событий, и укажи, на какой валютной паре стоит сосредоточить внимание для торговли сегодня."},
                    {"role": "user", "content": f"Календарь: {calendar_events}\nНовости: {news_items}"},
                ]
                response = openai.ChatCompletion.create(model="gpt-4o", messages=messages_to_openai)
                context["news_analysis"] = response["choices"][0]["message"]["content"]

            if request.method == "POST" and "deep_tech_analyst" in request.POST:
                indicators_history = get_indicators_data_history(symbol, "M15", count=20)

                messages_to_openai = [
                    {"role": "system", "content": "Ты технический аналитик. Анализируй рынок по индикаторам и свечам."},
                    {"role": "user", "content": f"История индикаторов и свечей:\n{indicators_history}"},
                ]
                response = openai.ChatCompletion.create(model="gpt-4o-mini", messages=messages_to_openai)
                context["deep_tech_analysis"] = response["choices"][0]["message"]["content"]


        finally:
            shutdown_mt5()  # Отключаем MetaTrader 5

    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в ai_analysis: {e}")

    return render(request, "ai_analysis.html", context)


import json
from django.http import JsonResponse
from src.utils.mt5_utils import get_currency_tick


def analyze_with_ai_x3(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            logging.info(f"Полученные данные от клиента: {data}")
            symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
            symbol = request.GET.get("symbol", symbol_from_cookie)

            # Получаем текущую цену
            symbol_tick = get_currency_tick(symbol)
            current_price = symbol_tick.get("bid") or symbol_tick.get("ask")

            timeframes = define_timeframes()
            indicators_summary = {}
            for label, tf in timeframes.items():
                indicators = get_indicators_data(symbol, tf, num_values=3)
                logging.info(f"Индикаторы для таймфрейма {label}: {indicators}")
                indicators_summary[label] = indicators

            # Получение новостей и экономического календаря
            economic_calendar = get_investing_calendar()
            news = get_fxstreet_news()

            # Формируем результат
            result = {
                "symbol": symbol,
                "current_price": current_price,
                "indicators_summary": indicators_summary,
                "economic_calendar": economic_calendar,  # Добавлен календарь
                "news": news,  # Добавлены новости
            }

            logging.info(f"Подготовленные данные для анализа: {result}")

            # Анализ с использованием AI
            ai_analysis = analyze_tech_data_with_ai(result)
            return JsonResponse({"analysis": ai_analysis})
        except Exception as e:
            logging.error(f"Ошибка при выполнении анализа с AI x3: {e}")
            return JsonResponse({"error": "Не удалось выполнить анализ."}, status=500)
    return JsonResponse({"error": "Некорректный запрос."}, status=400)


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
