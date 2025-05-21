from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout
from django.http import JsonResponse

import logging
import datetime, os
import pandas as pd
import matplotlib
import openai

from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.utils.mt5_utils import (
    initialize_mt5,
    shutdown_mt5,
    get_account_info,
    get_open_positions,
    get_currency_tick,
    open_market_position,
    place_pending_order,
    get_rates_dataframe,
    get_trading_profit_history,
)
from src.utils.investing_calendar import get_investing_calendar
from src.utils.rss_news import get_fxstreet_news
from src.utils.ai_analytic import analyze_with_ai
from src.trading.forex_pair import (
    majors,
    metals,
    cryptocurrencies,
    stocks,
    indices,
    commodities,
    all_symbols,
)
from src.trading.trading import (
    get_indicators_data,
    smc_strategy,
    ict_strategy,
    snr_strategy,
    analyze_strategies_for_timeframes,
    calculate_regression_channel,
)
from webapp.models import Recommendation

import MetaTrader5 as mt5
import talib
import matplotlib.pyplot as plt
import io
import urllib, base64

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Можно изменить уровень при необходимости
    format="%(asctime)s - %(levelname)s - %(message)s",
)

matplotlib.use("Agg")

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


# ==========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================


def define_timeframes():
    """Определение всех таймфреймов для анализа"""
    return {
        "1m": mt5.TIMEFRAME_M1,
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


def handle_message(request, success, success_message, error_message):
    """Универсальная функция для отправки сообщений о статусе операций"""
    if success:
        messages.success(request, success_message)
    else:
        messages.error(request, error_message)


# ==========================
# ВЫХОД И ПРОФИЛЬ
# ==========================


def logout_view(request):
    # Сбрасываем данные пользователя и выходим
    logout(request)
    request.session.flush()
    return redirect("login")


def profile_info_view(request):
    return render(request, "rofile-information.html")


# ==========================
# ОСНОВНЫЕ СТРАНИЦЫ: HOME, FUNDAMENTAL, TECHNICAL, AI
# ==========================


def home(request):
    # Подготовка контекста с символами
    context = {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
    }
    all_s = majors + metals + cryptocurrencies + stocks + indices + commodities
    context["all_symbols"] = all_s

    symbol = request.GET.get("symbol", "EURUSD")

    try:
        initialize_mt5()
        try:
            # Информация о счете и позициях
            account_info = get_account_info()
            open_positions = get_open_positions()
            context.update(account_info)
            context["open_positions"] = open_positions

            # Тик выбранной пары
            if not mt5.symbol_select(symbol, True):
                raise Exception(f"Не удалось выбрать символ {symbol} для анализа.")

            selected_pair_tick = get_currency_tick(symbol)
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для {symbol}.")

            context.update(
                {
                    "selected_pair_tick": selected_pair_tick,
                    "selected_pair": symbol,
                }
            )

            # История баланса за 30 дней (пока статическая)
            today = datetime.now()
            start_date = today - timedelta(days=30)

            balance_history = []
            equity_history = []
            profit_history = []
            date_labels = []

            for i in range(30):
                date = start_date + timedelta(days=i)
                balance_history.append(account_info["balance"])
                equity_history.append(account_info["equity"])
                profit_history.append(get_trading_profit_history())
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

        finally:
            shutdown_mt5()

    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в home: {e}")

    return render(request, "home.html", context)


def fundamental_analysis(request):
    context = {}
    try:
        context["economic_calendar"] = get_investing_calendar()
        context["rss_news"] = get_fxstreet_news()
    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в fundamental_analysis: {e}")

    return render(request, "fundamental_analysis.html", context)


def technical_analysis(request):
    symbol = request.GET.get("symbol", "EURUSD")
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
    all_s = majors + metals + cryptocurrencies + stocks + indices + commodities
    context["all_symbols"] = all_s

    try:
        initialize_mt5()
        try:
            selected_pair_tick = get_currency_tick(symbol)
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для {symbol}.")

            context["selected_pair_tick"] = selected_pair_tick

            (
                indicators_by_timeframe,
                ict_strategies_by_timeframe,
                smc_strategies_by_timeframe,
                snr_strategies_by_timeframe,
            ) = analyze_strategies_for_timeframes(symbol, timeframes)

            regression_channel_by_timeframe = {}
            for label, tf in timeframes.items():
                regression_result = calculate_regression_channel(symbol, tf)
                if regression_result:
                    regression_channel_by_timeframe[label] = regression_result
                else:
                    logging.warning(f"Нет регрессии для {symbol} {label}")

            strategies = [
                {"name": "ICT Strategy", "data": ict_strategies_by_timeframe},
                {"name": "SMC Strategy", "data": smc_strategies_by_timeframe},
                {"name": "SNR Strategy", "data": snr_strategies_by_timeframe},
            ]

            context.update(
                {
                    "indicators_by_timeframe": indicators_by_timeframe,
                    "strategies": strategies,
                    "regression_channel_by_timeframe": regression_channel_by_timeframe,
                }
            )

        finally:
            shutdown_mt5()
    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в technical_analysis: {e}")

    return render(request, "technical_analysis.html", context)


def ai_analysis(request):
    symbol = request.GET.get("symbol", "EURUSD")
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
    all_s = majors + metals + cryptocurrencies + stocks + indices + commodities
    context["all_symbols"] = all_s

    try:
        initialize_mt5()
        try:
            account_info, open_positions = get_account_and_positions()
            context.update(account_info)
            context["open_positions"] = open_positions

            selected_pair_tick = get_currency_tick(symbol)
            context["last_updated"] = timezone.now()
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для {symbol}.")

            context["selected_pair_tick"] = selected_pair_tick

            (
                indicators_by_timeframe,
                ict_strategies,
                smc_strategies_by_timeframe,
                snr_strategies_by_timeframe,
            ) = analyze_strategies_for_timeframes(symbol, timeframes)

            context["indicators_by_timeframe"] = indicators_by_timeframe

            # Обработка POST запросов (открытие позиции, отложенных ордеров)
            if request.method == "POST":
                if "open_position" in request.POST:
                    try:
                        volume = float(request.POST.get("volume", 0.01))
                        direction = request.POST.get("direction", "buy")
                        take_profit = float(request.POST.get("take_profit", 0))
                        stop_loss = float(request.POST.get("stop_loss", 0))
                        result = open_market_position(
                            symbol, volume, direction, take_profit, stop_loss
                        )
                        if result:
                            messages.success(request, f"Позиция по {symbol} открыта.")
                        else:
                            messages.error(
                                request, f"Ошибка при открытии позиции {symbol}."
                            )
                    except Exception as e:
                        logging.error(f"Ошибка при открытии позиции {symbol}: {e}")
                        messages.error(
                            request, f"Не удалось открыть позицию по {symbol}."
                        )

                if "place_pending_order" in request.POST:
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
                                request, f"Отложенный ордер по {symbol} установлен."
                            )
                        else:
                            messages.error(
                                request,
                                f"Ошибка при установке отложенного ордера {symbol}.",
                            )
                    except Exception as e:
                        logging.error(
                            f"Ошибка при установке отложенного ордера {symbol}: {e}"
                        )
                        messages.error(
                            request, f"Не удалось установить отложенный ордер {symbol}."
                        )

                # AI анализ
                if "analyze_with_ai" in request.POST:
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

                    result = {
                        "symbol": symbol,
                        "current_price": selected_pair_tick.get("bid")
                        or selected_pair_tick.get("ask"),
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
                        ai_analysis = analyze_with_ai(
                            result, get_investing_calendar(), get_fxstreet_news()
                        )
                        context["ai_analysis"] = ai_analysis
                    except Exception as e:
                        logging.error(f"Ошибка при анализе AI: {e}")
                        messages.error(request, "Не удалось выполнить анализ с AI.")

        finally:
            shutdown_mt5()
    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в ai_analysis: {e}")

    return render(request, "ai_analysis.html", context)


# ==========================
# DASHBOARD И ТОРГОВЛЯ
# ==========================


def dashboard(request):
    context = {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
    }
    all_s = majors + metals + cryptocurrencies + stocks + indices + commodities
    context["all_symbols"] = all_s

    symbol = request.GET.get("symbol", "EURUSD")
    context["symbol"] = symbol

    timeframes = define_timeframes()

    try:
        initialize_mt5()
        try:
            account_info, open_positions = get_account_and_positions()
            context.update(account_info)
            context["open_positions"] = open_positions

            context["economic_calendar"] = get_investing_calendar()
            context["rss_news"] = get_fxstreet_news()
            context["last_updated"] = timezone.now()

            selected_pair_tick = get_currency_tick(symbol)
            context.update(
                {"selected_pair_tick": selected_pair_tick, "selected_pair": symbol}
            )

            (
                indicators_by_timeframe,
                ict_strategies_by_timeframe,
                smc_strategies_by_timeframe,
                snr_strategies_by_timeframe,
            ) = analyze_strategies_for_timeframes(symbol, timeframes)

            regression_channel_by_timeframe = {}
            for label, tf in timeframes.items():
                regression_result = calculate_regression_channel(symbol, tf)
                if regression_result:
                    regression_channel_by_timeframe[label] = regression_result
                else:
                    logging.warning(f"Нет регрессии для {symbol} {label}")

            context.update(
                {
                    "indicators_by_timeframe": indicators_by_timeframe,
                    "ict_strategies_by_timeframe": ict_strategies_by_timeframe,
                    "smc_strategies_by_timeframe": smc_strategies_by_timeframe,
                    "snr_strategies_by_timeframe": snr_strategies_by_timeframe,
                    "regression_channel_by_timeframe": regression_channel_by_timeframe,
                }
            )

            if request.method == "POST":
                if "analyze_with_ai" in request.POST:
                    indicators = indicators_by_timeframe.get("15m", {})
                    context["indicators"] = indicators
                    try:
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

                        ai_analysis = analyze_with_ai(
                            result, context["economic_calendar"], context["rss_news"]
                        )
                        context["ai_analysis"] = ai_analysis
                    except Exception as e:
                        logging.error(f"Ошибка анализа с AI: {e}")
                        messages.error(request, "Не удалось выполнить анализ с AI.")

                if "open_position" in request.POST:
                    try:
                        symbol_req = request.POST.get("symbol", "EURUSD")
                        volume = float(request.POST.get("volume", 0.01))
                        order_type = request.POST.get("direction", "buy")
                        take_profit = float(request.POST.get("take_profit", 0))
                        stop_loss = float(request.POST.get("stop_loss", 0))
                        result = open_market_position(
                            symbol_req, volume, order_type, take_profit, stop_loss
                        )
                        if result:
                            messages.success(request, f"Позиция {symbol_req} открыта.")
                        else:
                            messages.error(
                                request, f"Ошибка открытия позиции {symbol_req}."
                            )
                    except Exception as e:
                        logging.error(f"Ошибка при открытии позиции {symbol_req}: {e}")
                        messages.error(
                            request, f"Не удалось открыть позицию {symbol_req}."
                        )

                if "place_pending_order" in request.POST:
                    try:
                        symbol_req = request.POST.get("symbol", "EURUSD")
                        volume = float(request.POST.get("volume", 0.01))
                        order_type = request.POST.get("order_type", "buy_limit")
                        price = float(request.POST.get("price", 0))
                        take_profit = float(request.POST.get("take_profit", 0))
                        stop_loss = float(request.POST.get("stop_loss", 0))
                        result = place_pending_order(
                            symbol_req,
                            volume,
                            order_type,
                            price,
                            take_profit,
                            stop_loss,
                        )
                        if result:
                            messages.success(
                                request, f"Отложенный ордер {symbol_req} установлен."
                            )
                        else:
                            messages.error(
                                request,
                                f"Ошибка установки отложенного ордера {symbol_req}.",
                            )
                    except Exception as e:
                        logging.error(f"Ошибка отложенного ордера {symbol_req}: {e}")
                        messages.error(
                            request,
                            f"Не удалось установить отложенный ордер {symbol_req}.",
                        )

        finally:
            shutdown_mt5()
    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в dashboard: {e}")

    return render(request, "dashboard.html", context)


def trade(request):
    context = {
        "majors": majors,
        "metals": metals,
        "cryptocurrencies": cryptocurrencies,
        "stocks": stocks,
        "indices": indices,
        "commodities": commodities,
    }
    all_s = majors + metals + cryptocurrencies + stocks + indices + commodities
    context["all_symbols"] = all_s

    if request.method == "POST":
        # Логика открытия позиций или ордеров
        pass

    return render(request, "trade.html", context)


# ==========================
# ПРОЧИЕ ВЬЮХИ И ФУНКЦИИ
# ==========================


def recommendations_list(request):
    recommendations = Recommendation.objects.all().order_by("-created_at")
    context = {"recommendations": recommendations}
    return render(request, "recommendations_list.html", context)


def test_view(request):
    return render(request, "test.html")


def statistics_view(request):
    try:
        account_info = get_account_info()
        balance_history = [account_info["balance"] for _ in range(14)]
        date_labels = [
            (datetime.now() - timedelta(days=i)).strftime("%d-%m-%Y") for i in range(14)
        ]
        context = {"balance_history": balance_history, "date_labels": date_labels}
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
    context = {}
    if request.method == "POST":
        volume = float(request.POST.get("volume"))
        entry_price = float(request.POST.get("entry_price"))
        stop_loss = float(request.POST.get("stop_loss"))
        take_profit = float(request.POST.get("take_profit"))
        risk = abs(entry_price - stop_loss) * volume
        reward = abs(take_profit - entry_price) * volume
        context = {"risk": risk, "reward": reward}
    return render(request, "trade_calculator.html", context)
