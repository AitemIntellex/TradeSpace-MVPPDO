import json
import logging
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
import MetaTrader5 as mt5

from src.services.market_analysis import get_market_analysis  # Подключаем маркет-анализ
from src.adviser.new_technical_indicators import get_new_indicators_data
from src.indicators.market_structure import (
    calculate_regression_channel,
    create_instrument_structure,
)
from src.indicators.technical_indicators import (
    analyze_current_price_with_fibonacci,
    calculate_ote,
    calculate_pivot_points,
    find_nearest_levels,
    is_price_in_ote,
)
from src.utils.mt5_connection import initialize_mt5
from src.trading.ict_strategy import ict_strategy
from src.trading.smc_strategy import smc_strategy
from src.trading.snr_strategy import snr_strategy
from src.trading.trading import prepare_fibonacci_levels
from src.utils.mt5_utils import shutdown_mt5
from polygon.views import define_timeframes


def technical_analysis_tas(request: HttpRequest) -> HttpResponse:

    try:
        # Инициализация MetaTrader 5
        initialize_mt5()

        # Получаем символ из cookie или GET-запроса
        symbol_from_cookie = request.COOKIES.get("selected_pair", "XAUUSD")
        symbol = request.GET.get("symbol", symbol_from_cookie)

        timeframes = define_timeframes()
        selected_timeframe = request.GET.get("timeframe", "15m")
        timeframe = timeframes.get(selected_timeframe, mt5.TIMEFRAME_M15)
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
        response = render(request, "technical_analysis/tas1.html", context)
        response.set_cookie("selected_timeframe", selected_timeframe)
        return response

    except Exception as e:
        logging.error(f"Ошибка ...: {e}")
        return JsonResponse({"error": str(e)}, status=500)

    finally:
        shutdown_mt5()


from src.services.market_analysis import get_market_analysis


def market_analysis_view(request):
    symbol = request.GET.get("symbol", "XAUUSD").strip()  # Убираем лишние пробелы
    timeframes = request.GET.getlist("timeframes")

    if "all" in timeframes:
        timeframes = "all"  # Если передано "all", анализируем всё

    print(f"🛠 DEBUG: Символ {symbol}, таймфреймы {timeframes}")  # Отладка

    analysis = get_market_analysis(symbol, timeframes)
    return JsonResponse(analysis, safe=False)
