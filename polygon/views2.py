from django.shortcuts import render, redirect
import talib

from src.indicators.technical_indicators import (
    calculate_fibonacci_levels,
    calculate_macd,
    calculate_pivot_points,
    calculate_rsi,
)
from src.utils.ai_analytic import analyze_with_ai, analyze_tech_data_with_ai
from src.utils.mt5_utils import (
    get_historical_account_data,
    get_trade_history,
    initialize_mt5,
    shutdown_mt5,
    get_account_info,
    get_open_positions,
    get_currency_tick,
    open_market_position,
    place_pending_order,  # Должно быть правильно импортировано
    get_rates_dataframe,
)


from src.utils.investing_calendar import get_investing_calendar
from src.utils.rss_news import get_fxstreet_news
from django.utils import timezone
import pandas as pd
import matplotlib
from django.contrib import messages  # Для уведомлений о статусе операций
import logging
import MetaTrader5 as mt5
from src.trading.trading import (
    get_indicators_data,
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

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import urllib, base64
from django.http import JsonResponse

# Настройка логирования
logging.basicConfig(
    level=logging.WARNING,  # Для логирования только предупреждений и ошибок
    format="%(asctime)s - %(levelname)s - %(message)s",
)
from datetime import datetime, timedelta
import datetime, os

from django.views.decorators.csrf import csrf_exempt
from src.trading.forex_pair import (
    majors,
    metals,
    cryptocurrencies,
    stocks,
    indices,
    commodities,
)
import openai
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


from django.shortcuts import render

# Настройка логирования
logging.basicConfig(
    level=logging.WARNING,  # Для логирования только предупреждений и ошибок
    format="%(asctime)s - %(levelname)s - %(message)s",
)


from django.shortcuts import render
from src.utils.mt5_utils import (
    initialize_mt5,
    shutdown_mt5,
    get_account_info,
    get_open_positions,
    get_currency_tick,
    get_rates_dataframe,
)
from django.utils import timezone
import logging
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta  # Импортируем корректно

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Для логирования всех событий, включая отладочные сообщения
    format="%(asctime)s - %(levelname)s - %(message)s",
)


from datetime import datetime, timedelta
from django.utils import timezone
from django.shortcuts import render
from src.utils.mt5_utils import (
    initialize_mt5,
    shutdown_mt5,
    get_account_info,
    get_open_positions,
    get_trading_profit_history,
    get_currency_tick,
)
from django.contrib.auth import logout


def logout_view(request):
    # Сначала сбрасываем все данные пользователя и выходим
    logout(request)

    # Затем чистим сессию
    request.session.flush()

    # Перенаправляем на страницу входа
    return redirect("login")


import calendar
from datetime import datetime, timedelta
from django.utils import timezone
from django.shortcuts import render
import logging
from django.shortcuts import render
from django.http import JsonResponse
from src.utils.investing_calendar import get_investing_calendar  # Ваш модуль


from datetime import datetime
from django.http import JsonResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def update_database(request):
    if request.method == "POST":
        # Логика обновления базы данных
        try:
            # Пример обновления данных
            update_some_data()
            return JsonResponse({"status": "success", "message": "Данные обновлены."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse(
        {"status": "error", "message": "Некорректный запрос."}, status=400
    )


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


# # Страница технического анализа
# def technical_analysis(request):
#     # Страница технического анализа
#     symbol = request.GET.get("symbol", "EURUSD")
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
#             # Получаем тик выбранной валютной пары
#             selected_pair_tick = get_currency_tick(symbol)
#             if selected_pair_tick is None:
#                 raise Exception(f"Не удалось получить тик для символа {symbol}.")

#             context["selected_pair_tick"] = selected_pair_tick

#             # Анализ стратегий и регрессионного канала для всех таймфреймов
#             (
#                 indicators_by_timeframe,
#                 ict_strategies_by_timeframe,
#                 smc_strategies_by_timeframe,
#                 snr_strategies_by_timeframe,
#             ) = analyze_strategies_for_timeframes(symbol, timeframes)

#             regression_channel_by_timeframe = {}
#             for label, timeframe in timeframes.items():
#                 regression_result = calculate_regression_channel(symbol, timeframe)
#                 if regression_result:
#                     regression_channel_by_timeframe[label] = regression_result
#                 else:
#                     logging.warning(
#                         f"Регрессионный анализ не выполнен для {symbol} на таймфрейме {label}"
#                     )

#             # Обновляем контекст для передачи в шаблон
#             strategies = [
#                 {"name": "ICT Strategy", "data": ict_strategies_by_timeframe},
#                 {"name": "SMC Strategy", "data": smc_strategies_by_timeframe},
#                 {"name": "SNR Strategy", "data": snr_strategies_by_timeframe},
#             ]

#             context.update(
#                 {
#                     "indicators_by_timeframe": indicators_by_timeframe,
#                     "strategies": strategies,
#                     "regression_channel_by_timeframe": regression_channel_by_timeframe,
#                 }
#             )

#         finally:
#             shutdown_mt5()  # Отключаем MetaTrader 5

#     except Exception as e:
#         context["error"] = str(e)
#         logging.error(f"Ошибка в technical_analysis: {e}")

#     return render(request, "technical_analysis.html", context)


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


from src.trading.trading import (
    get_indicators_data,
    analyze_strategies_for_timeframes,
)


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


from django.shortcuts import render
from django.http import JsonResponse
from src.utils.mt5_utils import initialize_mt5, shutdown_mt5
from src.indicators.technical_indicators import get_indicators_data
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


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


# Нам нужно поработать над этой страницей
# def technical_analysis_indicators(request):
#     """
#     Обобщённая страница для вывода технических индикаторов и структуры рынка
#     по всем таймфреймам одновременно (или выборочно).
#     """
#     open_positions = get_open_positions()

#     # Get symbol from cookie or query parameters
#     symbol = request.GET.get("symbol", request.COOKIES.get("selected_pair", "XAUUSD"))

#     # Get the number of values, ensure it is an integer
#     try:
#         num_values_int = int(request.GET.get("num_values", "1"))
#     except ValueError:
#         num_values_int = 1

#     timeframes = define_timeframes()  # e.g., {"1m": "M1", "5m": "M5", ...}

#     context = {
#         "selected_pair": symbol,
#         "num_values": num_values_int,
#     }

#     # Initialize result containers
#     structure_by_timeframe = {}
#     indicators_by_timeframe = {}
#     pivot_points_by_timeframe = {}
#     market_structure_by_timeframe = {}
#     fibonacci_by_timeframe = {}

#     try:
#         initialize_mt5()
#         try:
#             selected_pair_tick = get_currency_tick(symbol)
#             if selected_pair_tick is None:
#                 raise Exception(f"Не удалось получить тик для символа {symbol}.")
#             context["selected_pair_tick"] = selected_pair_tick

#             default_structure = {
#                 "trend": "Нет данных",
#                 "support": "Нет данных",
#                 "resistance": "Нет данных",
#                 "atr": "Нет данных",
#             }
#             default_indicators = {
#                 "atr": "Нет данных",
#                 "mfi": "Нет данных",
#                 "cci": "Нет данных",
#                 "stochastic": "Нет данных",
#                 "sma": "Нет данных",
#                 "macd_signal": "Нет данных",
#                 "rsi": "Нет данных",
#             }
#             default_pivot_points = {
#                 "pivot": "Нет данных",
#                 "pp_resistance": "Нет данных",
#                 "pp_support": "Нет данных",
#             }
#             default_fibonacci = {
#                 "fib_levels": {},
#                 "local_high": "Нет данных",
#                 "local_low": "Нет данных",
#             }

#             for label, tf in timeframes.items():
#                 instrument_data = (
#                     create_instrument_structure(symbol, tf, bars=num_values_int)
#                     or default_structure
#                 )
#                 ind_data = (
#                     get_indicators_data(symbol, tf, num_values=num_values_int)
#                     or default_indicators
#                 )
#                 pivot_points = (
#                     calculate_pivot_points(symbol, tf, num_values_int)
#                     or default_pivot_points
#                 )
#                 fibonacci_data = (
#                     calculate_fibonacci_levels(symbol, tf, bars=500, local_bars=100)
#                     or default_fibonacci
#                 )
#                 ms = identify_market_structure(symbol, tf) or default_structure

#                 structure_by_timeframe[label] = instrument_data
#                 indicators_by_timeframe[label] = ind_data
#                 pivot_points_by_timeframe[label] = pivot_points
#                 market_structure_by_timeframe[label] = ms
#                 fibonacci_by_timeframe[label] = fibonacci_data

#                 for label, tf in timeframes.items():
#                     fibonacci_data = calculate_fibonacci_levels(
#                         symbol, tf, bars=500, local_bars=100
#                     ) or {
#                         "fib_levels": {},
#                         "local_high": "Нет данных",
#                         "local_low": "Нет данных",
#                     }
#                     fibonacci_by_timeframe[label] = fibonacci_data

#                     # Логируем результат для каждого таймфрейма
#                     logging.info(f"Fibonacci Data for {label}: {fibonacci_data}")

#         finally:
#             shutdown_mt5()

#     except Exception as e:
#         context["error"] = str(e)
#         logging.error(f"Ошибка в technical_analysis_general: {e}")

#     context.update(
#         {
#             "structure_by_timeframe": structure_by_timeframe,
#             "indicators_by_timeframe": indicators_by_timeframe,
#             "pivot_points_by_timeframe": pivot_points_by_timeframe,
#             "market_structure_by_timeframe": market_structure_by_timeframe,
#             "fibonacci_by_timeframe": fibonacci_by_timeframe,  # Должно быть добавлено
#         }
#     )

#     return render(
#         request, "technical_analysis/technical_analysis_indicators.html", context
#     )


import logging
from django.shortcuts import render

# Предполагаем, что эти и другие необходимые функции и переменные где-то импортированы:
# from .mt5_utils import (initialize_mt5, shutdown_mt5, get_currency_tick, get_open_positions, define_timeframes)
# from .indicators.market_structure import create_instrument_structure
# from .indicators.technical_indicators import get_indicators_data
# from .strategies import (calculate_pivot_points, calculate_fibonacci_levels, identify_market_structure)
# majors, metals, cryptocurrencies, stocks, indices, commodities = ...


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

    Параметры запроса:
        symbol       - финансовый инструмент (по умолчанию XAUUSD или из cookie)
        num_values   - сколько баров подгружаем (по умолчанию 1)
        timeframe    - если указать конкретный (например, "1h"), будет вывод только по нему
                       если не указано или 'ALL', то по всем таймфреймам
        recent_count - сколько последних значений для некоторых индикаторов показать (по умолчанию 3)
    """
    open_positions = get_open_positions()

    # 1) Получаем текущий символ (из GET, потом cookie, иначе XAUUSD)
    symbol = request.GET.get("symbol", request.COOKIES.get("selected_pair", "XAUUSD"))

    # 2) Определяем, сколько баров подгружаем (по умолчанию 1)
    try:
        num_values_int = int(request.GET.get("num_values", "1"))
    except ValueError:
        num_values_int = 1

    # 3) Определяем, какие таймфреймы обрабатываем:
    #    - либо все (по умолчанию),
    #    - либо только один, если передан timeframe в GET.
    requested_tf = request.GET.get("timeframe", "ALL")  # например,  "1h" или "ALL"
    all_timeframes = (
        define_timeframes()
    )  # e.g. {"1m": "M1", "5m": "M5", "1h": "H1", ...}
    if requested_tf.upper() != "ALL" and requested_tf in all_timeframes:
        # Оставляем только один таймфрейм
        timeframes = {requested_tf: all_timeframes[requested_tf]}
    else:
        # Берём все
        timeframes = all_timeframes

    # 4) Сколько последних значений (свечей) для некоторых индикаторов нужно вывести?
    try:
        recent_count = int(request.GET.get("recent_count", "3"))
    except ValueError:
        recent_count = 3

    # 5) Подготовим основу для контекста
    context = {
        "selected_pair": symbol,
        "num_values": num_values_int,
        "requested_timeframe": requested_tf,
        "recent_count": recent_count,
        # Можно добавить (если нужно отобразить списки символов на странице):
        # "majors": majors,
        # "metals": metals,
        # ...
    }

    # 6) Готовим словари под результаты
    structure_by_timeframe = {}
    indicators_by_timeframe = {}
    pivot_points_by_timeframe = {}
    market_structure_by_timeframe = {}
    fibonacci_by_timeframe = {}

    # 7) Словари со значениями по умолчанию, чтобы избежать ошибок "None"
    default_structure = {
        "trend": "Нет данных",
        "support": "Нет данных",
        "resistance": "Нет данных",
        "atr": "Нет данных",
    }
    default_indicators = {
        # Зависит от того, какие индикаторы конкретно используете
        "atr": [],
        "mfi": [],
        "cci": [],
        "stochastic_k": [],
        "stochastic_d": [],
        "sma": [],
        "macd": [],
        "signal": [],
        "rsi": [],
        # ... можно дополнять
    }
    default_pivot_points = [
        {
            "pivot": None,
            "pp_resistance": [None, None, None],
            "pp_support": [None, None, None],
        }
    ]
    default_fibonacci = {
        "fib_levels": {},
        "local_high": "Нет данных",
        "local_low": "Нет данных",
    }

    # 8) Подключаемся к MT5 и собираем данные
    try:
        initialize_mt5()
        try:
            # Проверим тик по выбранному символу
            selected_pair_tick = get_currency_tick(symbol)
            if selected_pair_tick is None:
                raise Exception(f"Не удалось получить тик для символа {symbol}.")

            # Можно сохранить в контекст, чтобы на странице показать текущий бид/аск и т.д.
            context["selected_pair_tick"] = selected_pair_tick

            for timeframe, data in indicators_by_timeframe.items():
                trend = data.get("trend", "range")
                data["trend_color"] = get_trend_color(trend)  # Добавляем цвет тренда
            # Проходимся по нужным таймфреймам
            for label, tf in timeframes.items():
                # 8.1) Общая структура инструмента
                instrument_data = create_instrument_structure(
                    symbol, tf, bars=num_values_int
                )
                if not instrument_data:
                    instrument_data = dict(default_structure)
                # Добавляем светофор (цвет фона) по тренду:
                trend_str = instrument_data.get("trend", "Нет данных")
                instrument_data["trend_color"] = get_color_for_trend(trend_str)

                # 8.2) Индикаторы
                ind_data = get_indicators_data(symbol, tf, num_values=num_values_int)
                if not ind_data:
                    ind_data = dict(default_indicators)
                # Если нужно сохранить только последние few значений, например recent_count
                # для RSI, MACD, и т.д., то можно сократить списки:
                # (Будьте аккуратны, если индикатор None или список пуст)
                for key, val in ind_data.items():
                    if isinstance(val, list) and len(val) > recent_count:
                        ind_data[key] = val[-recent_count:]

                # 8.3) Pivot Points
                pivot_points = calculate_pivot_points(symbol, tf, num_values_int)
                if not pivot_points:
                    # Пивот-функция может возвращать список словарей, например, на каждый бар,
                    # или только один словарь. Это зависит от реализации.
                    # Допустим, вернём список со словарями.
                    pivot_points = default_pivot_points

                # 8.4) Уровни Фибоначчи
                fibonacci_data = calculate_fibonacci_levels(
                    symbol, tf, bars=500, local_bars=100
                )
                if not fibonacci_data:
                    fibonacci_data = dict(default_fibonacci)

                # 8.5) Простая структура рынка (market_structure)
                ms = identify_market_structure(symbol, tf)
                if not ms:
                    ms = dict(default_structure)
                ms_trend_str = ms.get("trend", "Нет данных")
                ms["trend_color"] = get_color_for_trend(ms_trend_str)

                # 8.6) Сохраняем всё в соответствующие словари:
                structure_by_timeframe[label] = instrument_data
                indicators_by_timeframe[label] = ind_data
                pivot_points_by_timeframe[label] = pivot_points
                fibonacci_by_timeframe[label] = fibonacci_data
                market_structure_by_timeframe[label] = ms

                logging.info(f"Timeframe: {label} => Instrument: {instrument_data}")
                logging.info(f"Timeframe: {label} => Indicators: {ind_data}")
                logging.info(f"Timeframe: {label} => Pivots: {pivot_points}")
                logging.info(f"Timeframe: {label} => Fib: {fibonacci_data}")
                logging.info(f"Timeframe: {label} => MS: {ms}")

        finally:
            shutdown_mt5()
    except Exception as e:
        context["error"] = str(e)
        logging.error(f"Ошибка в technical_analysis_indicators: {e}")

    # 9) Дополняем контекст собранными результатами
    context.update(
        {
            "structure_by_timeframe": structure_by_timeframe,
            "indicators_by_timeframe": indicators_by_timeframe,
            "pivot_points_by_timeframe": pivot_points_by_timeframe,
            "market_structure_by_timeframe": market_structure_by_timeframe,
            "fibonacci_by_timeframe": fibonacci_by_timeframe,
        }
    )

    # 10) Рендерим шаблон
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


def technical_analysis_strategies(request):
    context = {
        "strategies_process_by_timeframe": ...,
    }
    return render(
        request, "technical_analysis/technical_analysis_strategies.html", context
    )


def technical_analysis_smc(request):
    # Если нужно что-то специфичное для SMC
    context = {}
    return render(request, "technical_analysis/technical_analysis_smc.html", context)


def technical_analysis_ict(request):
    context = {}
    return render(request, "technical_analysis/technical_analysis_ict.html", context)


def technical_analysis_snr(request):
    context = {}
    return render(request, "technical_analysis/technical_analysis_snr.html", context)


from django.core.cache import cache


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


from django.shortcuts import render
from .models import Recommendation
import logging
from django.core.paginator import Paginator


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


from django.http import JsonResponse


def get_symbol_data(request):
    symbol = request.GET.get("symbol")
    if not symbol:
        return JsonResponse({"error": "Символ не указан"}, status=400)

    try:
        data = get_currency_tick(symbol)  # Из mt5_utils.py
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


from django.http import JsonResponse


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


from django.shortcuts import render
from MetaTrader5 import initialize, history_deals_get, account_info


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


import calendar


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
    symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
    symbol = request.GET.get("symbol", symbol_from_cookie)

    # Определяем доступные таймфреймы
    timeframes = define_timeframes()
    timeframe_label = request.GET.get("timeframe", "all")  # "all" для всех таймфреймов
    num_values = int(request.GET.get("num_values", 500))  # Значение по умолчанию

    try:
        if timeframe_label == "all":
            instrument_data_by_timeframe = {
                tf_label: create_instrument_structure(symbol, tf_value)
                for tf_label, tf_value in timeframes.items()
            }
        else:
            tf_value = timeframes.get(timeframe_label, mt5.TIMEFRAME_H1)
            instrument_data_by_timeframe = {
                timeframe_label: create_instrument_structure(symbol, tf_value)
            }

        # Формируем данные для графиков
        chart_data = []
        for tf_label, data in instrument_data_by_timeframe.items():
            if data and "ohlc" in data and data["ohlc"]:
                df = pd.DataFrame(data["ohlc"])

                # Преобразуем `time` в строку (ISO формат)
                df["time"] = df["time"].dt.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )  # Преобразуем в ISO 8601

                ohlc = {
                    "time": df["time"].tolist(),
                    "open": df["open"].tolist(),
                    "high": df["high"].tolist(),
                    "low": df["low"].tolist(),
                    "close": df["close"].tolist(),
                }
                fib_levels = data.get("fib_levels", {})
                chart_data.append(
                    {
                        "timeframe": tf_label,
                        "ohlc": ohlc,
                        "fib_levels": fib_levels,
                    }
                )

        context = {
            "symbol": symbol,
            "timeframe_label": timeframe_label,
            "timeframes": list(timeframes.keys()),
            "instrument_data_by_timeframe": instrument_data_by_timeframe,
            "chart_data": chart_data,
            "num_values": num_values,
        }

    except Exception as e:
        logging.error(f"Ошибка анализа инструмента: {e}")
        context = {
            "error": str(e),
            "symbol": symbol,
            "timeframe_label": timeframe_label,
            "timeframes": list(timeframes.keys()),
        }

    return render(request, "technical_analysis/instrument_analysis.html", context)


# ###################################### #
import plotly.graph_objects as go


def trade_chart(request):
    """Генерация графика для веб-интерфейса"""
    symbol = request.GET.get("symbol", "XAUUSD")
    timeframe = request.GET.get("timeframe", "15m")

    # Получаем исторические данные (OHLC)
    df = get_rates_dataframe(symbol, timeframe, 100)
    if df is None or df.empty:
        return JsonResponse({"error": "Нет данных"}, status=400)

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
    return render(request, "technical_analysis/plotly_chart.html")
