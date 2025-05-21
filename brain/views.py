import json
import logging
import datetime
import pandas as pd

from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse

from polygon.views import define_timeframes
from .models import Thought

# ========================================
# Сторонние библиотеки
# ========================================
import MetaTrader5 as mt5

# ========================================
# Локальные модули
# ========================================
from src.adviser.new_technical_indicators import (
    get_new_indicators_data,
)
from src.indicators.technical_indicators import (
    analyze_current_price_with_fibonacci,
    calculate_fibonacci_levels,
    calculate_ote,
    calculate_pivot_points,
    find_nearest_levels,
    is_price_in_ote,
)
from src.utils.mt5_utils import (
    initialize_mt5,
    shutdown_mt5,
)
from src.indicators.market_structure import (
    calculate_regression_channel,
    create_instrument_structure,
)
from src.trading.ict_strategy import ict_strategy
from src.trading.smc_strategy import smc_strategy
from src.trading.snr_strategy import snr_strategy

logger = logging.getLogger(__name__)


def convert_values(obj):
    """
    Рекурсивно проходит по словарям/спискам и приводит объекты
    к видам, которые без проблем сериализуются в JSON:
    - None -> None (в JSON станет null)
    - pd.Timestamp -> str (isoformat)
    - datetime.datetime -> str (isoformat)
    - Остальные значения (числа, строки) не трогаем.
    """
    if isinstance(obj, dict):
        return {k: convert_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_values(x) for x in obj]
    elif isinstance(obj, pd.Timestamp):
        return (
            obj.isoformat()
        )  # Превращаем в строку "2025-02-09T11:34:40.800000" и т.д.
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    return obj


def prepare_fibonacci_levels(symbol, timeframe, trend="up", as_string=False):
    """
    Обёртка над calculate_fibonacci_levels с приведением Timestamp -> isoformat
    и возвратом данных в словаре или в виде строки (если as_string=True).
    """
    fib_data = calculate_fibonacci_levels(symbol, timeframe, trend)

    if fib_data is None:
        return "Нет данных" if as_string else {}

    fib_data = convert_values(fib_data)

    if as_string:
        return json.dumps(fib_data, ensure_ascii=False, indent=2)
    return fib_data


def thought_list(request):
    """Пример простой вьюхи — показываем список объектов Thought."""
    thoughts = Thought.objects.all()
    return render(request, "brain/thought_list.html", {"thoughts": thoughts})


def price_action_chart(request: HttpRequest) -> HttpResponse:
    """
    Вьюха, формирующая контекст для графика price action.
    Если это AJAX-запрос, возвращаем JSON, иначе HTML.
    """
    try:
        # Инициализация MetaTrader 5
        initialize_mt5()

        # Извлекаем symbol/timeframe из куки или GET
        symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
        symbol = request.GET.get("symbol", symbol_from_cookie)

        timeframes = define_timeframes()
        selected_timeframe = request.GET.get("timeframe", "15m")
        timeframe = timeframes.get(selected_timeframe, mt5.TIMEFRAME_M15)

        # Количество свечей (по умолчанию 5)
        selected_candles = int(request.GET.get("candles", 5))

        # Получаем данные
        indicators = get_new_indicators_data(
            symbol, timeframe, num_values=selected_candles
        )
        fib_data = prepare_fibonacci_levels(symbol, timeframe)
        pivot_points = calculate_pivot_points(
            symbol, timeframe, num_values=selected_candles
        )

        ict_data = ict_strategy(symbol, timeframe)
        smc_data = smc_strategy(symbol, timeframe)
        snr_data = snr_strategy(symbol, timeframe)

        instrument_structure = create_instrument_structure(symbol, timeframe)
        regression_channel = calculate_regression_channel(symbol, timeframe)
        current_price = instrument_structure.get("current_price")

        # Ближайшие уровни (по fib_data)
        nearest_levels = find_nearest_levels(fib_data, current_price)

        # OTE-анализ
        ote_analysis = calculate_ote(
            symbol=symbol,
            timeframe=timeframe,
            trend=instrument_structure.get("trend", ""),
            bars=500,
            local_bars=128,
        )
        is_in_ote = False
        if ote_analysis:
            is_in_ote = is_price_in_ote(
                price=current_price or 0,
                ote_levels=ote_analysis["ote_levels"],
            )

        # Анализ цены с Фибоначчи (если есть ohlc)
        fib_analysis = {}
        ohlc_bars = instrument_structure.get("ohlc", [])
        if ohlc_bars:
            last_bar = ohlc_bars[-1]
            fib_analysis = analyze_current_price_with_fibonacci(
                high=last_bar["high"],
                low=last_bar["low"],
                close=last_bar["close"],
                current_price=current_price,
                start_time=ohlc_bars[0]["time"],
                end_time=last_bar["time"],
            )

        # Очищаем instrument_structure от Timestamp
        cleaned_instrument_structure = convert_values(instrument_structure)

        # Логирование для отладки
        logger.info(f"Символ: {symbol}")
        logger.info(f"Таймфрейм (строка): {selected_timeframe}, MT5 TF: {timeframe}")
        logger.info(f"Число OHLC баров: {len(ohlc_bars)}")

        # Готовим Python-контекст (используется для HTML шаблона)
        context = {
            "symbol": symbol,
            "timeframes": list(timeframes.keys()),
            "selected_timeframe": selected_timeframe,
            "selected_candles": selected_candles,
            "instrument_structure": cleaned_instrument_structure,
            "regression_channel": regression_channel,
            "indicators": indicators,
            "fibonacci_levels": fib_data,
            "pivot_points": pivot_points,
            "ict_strategy": ict_data,
            "smc_strategy": smc_data,
            "snr_strategy": snr_data,
            "nearest_levels": nearest_levels,
            "fib_analysis": fib_analysis,
            "ote_analysis": ote_analysis,
            "is_in_ote": is_in_ote,
            "ohlc_data": cleaned_instrument_structure.get("ohlc", []),
        }

        # Готовим сериализованные (JSON) версии для фронтенда или AJAX
        context_json = {
            "symbol": symbol,
            "timeframes": list(timeframes.keys()),
            "selected_timeframe": selected_timeframe,
            "selected_candles": selected_candles,
            "indicators_json": json.dumps(convert_values(indicators)),
            "fibonacci_levels_json": json.dumps(convert_values(fib_data)),
            "pivot_points_json": json.dumps(convert_values(pivot_points)),
            "ict_strategy_json": json.dumps(convert_values(ict_data)),
            "smc_strategy_json": json.dumps(convert_values(smc_data)),
            "snr_strategy_json": json.dumps(convert_values(snr_data)),
            "nearest_levels_json": json.dumps(convert_values(nearest_levels)),
            "fib_analysis_json": json.dumps(convert_values(fib_analysis)),
            "ote_analysis_json": json.dumps(convert_values(ote_analysis)),
            "is_in_ote": is_in_ote,
            "instrument_structure_json": json.dumps(cleaned_instrument_structure),
            "regression_channel_json": json.dumps(convert_values(regression_channel)),
            "ohlc_json": json.dumps(cleaned_instrument_structure.get("ohlc", [])),
        }

        # Если это AJAX-запрос, возвращаем JSON
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(context_json)

        # Иначе рендерим HTML
        full_context = {**context, **context_json}
        response = render(request, "brain/PA-chart.html", full_context)

        # Сохраняем куки (символ и таймфрейм)
        response.set_cookie("selected_pair", symbol)
        response.set_cookie("selected_timeframe", selected_timeframe)

        return response

    except Exception as e:
        logger.error(f"Ошибка в price_action_chart: {e}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        shutdown_mt5()
