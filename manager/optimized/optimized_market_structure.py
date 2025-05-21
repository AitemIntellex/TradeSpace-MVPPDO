import logging
from typing import Optional, Tuple, Dict, Any

import numpy as np
import pandas as pd
import talib
from scipy.signal import argrelextrema

from brain.optimized.optimized_indicators import fetch_ohlc_data, generate_plotly_data
from src.indicators.technical_indicators import (
    calculate_fibonacci_levels,
    get_indicators_data,
)
from src.indicators.market_helpers import identify_liquidity_zones
from src.trading.trading import log_data_error
from src.utils.mt5_utils import get_rates_dataframe

# Настройка логирования (если не задана глобально)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_local_extremes(
    df: pd.DataFrame, column: str = "close", order: int = 10
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Находит локальные максимумы и минимумы в заданном столбце DataFrame с указанным порядком.

    :param df: DataFrame с данными.
    :param column: Название столбца для анализа (по умолчанию "close").
    :param order: Порядок (количество точек до/после).
    :return: Кортеж (локальные максимумы, локальные минимумы).
    """
    values = df[column].values
    local_max_indices = argrelextrema(values, comparator=np.greater, order=order)[0]
    local_min_indices = argrelextrema(values, comparator=np.less, order=order)[0]
    return df.iloc[local_max_indices], df.iloc[local_min_indices]


def calculate_regression_channel(
    symbol: str, timeframe: str
) -> Optional[Dict[str, float]]:
    """
    Выполняет регрессионный анализ закрывающих цен и рассчитывает верхнюю и нижнюю границы канала.

    :param symbol: Символ финансового инструмента.
    :param timeframe: Таймфрейм (например, "H1" или mt5.TIMEFRAME_H1).
    :return: Словарь с коэффициентами регрессии и значениями канала, либо None при ошибке.
    """
    df = get_rates_dataframe(symbol, timeframe, period=500)
    if df is None or df.empty:
        logging.error(
            f"Недостаточно данных для регрессионного анализа по {symbol} {timeframe}"
        )
        return None

    x = np.arange(len(df))
    y = df["close"]

    try:
        slope, intercept = np.polyfit(x, y, 1)
    except ValueError as e:
        logging.error(f"Ошибка при расчёте линейной регрессии для {symbol}: {e}")
        return None

    std_dev = np.std(y)
    # Для определения границ берём последнее значение регрессии с добавлением/вычитанием стандартного отклонения
    upper_channel = intercept + slope * x[-1] + std_dev
    lower_channel = intercept + slope * x[-1] - std_dev

    regression_result = {
        "slope": round(slope, 5),
        "intercept": round(intercept, 5),
        "upper_channel": round(upper_channel, 5),
        "lower_channel": round(lower_channel, 5),
    }

    logging.info(
        f"Регрессионный анализ для {symbol} ({timeframe}): "
        f"наклон={regression_result['slope']}, пересечение={regression_result['intercept']}, "
        f"верхний канал={regression_result['upper_channel']}, нижний канал={regression_result['lower_channel']}"
    )
    return regression_result


def identify_market_structure(symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
    """
    Анализирует рыночную структуру для заданного символа и таймфрейма.

    :param symbol: Символ финансового инструмента.
    :param timeframe: Таймфрейм (например, "H1").
    :return: Словарь с характеристиками структуры рынка или None при ошибке.
    """
    df = get_rates_dataframe(symbol, timeframe, 500)
    if df is None or df.empty:
        log_data_error(symbol)
        return None

    data_length = len(df)
    if data_length < 20:
        logging.warning(
            f"Мало данных для анализа 20-периодного тренда {symbol} {timeframe}."
        )
        return None

    # Абсолютные экстремумы
    absolute_high = df["high"].max()
    absolute_low = df["low"].min()

    # Локальные экстремумы и базовые статистики
    local_max_df, local_min_df = get_local_extremes(df, column="close", order=20)
    local_high = local_max_df["close"].max() if not local_max_df.empty else None
    local_low = local_min_df["close"].min() if not local_min_df.empty else None
    support = local_min_df["close"].mean() if not local_min_df.empty else None
    resistance = local_max_df["close"].mean() if not local_max_df.empty else None

    current_price = df["close"].iloc[-1]
    recent_highs = df["high"].rolling(window=20).max().iloc[-1]
    recent_lows = df["low"].rolling(window=20).min().iloc[-1]

    # Определение тренда
    if current_price > recent_highs:
        trend = "strong_uptrend"
    elif current_price < recent_lows:
        trend = "strong_downtrend"
    else:
        price_range = recent_highs - recent_lows
        overall_range = absolute_high - absolute_low
        trend = (
            "range"
            if price_range < (overall_range * 0.2)
            else ("uptrend" if current_price > df["close"].mean() else "downtrend")
        )
        logging.info(
            f"Current Price: {current_price}, Recent Highs: {recent_highs}, "
            f"Recent Lows: {recent_lows}, Price Range: {price_range}, "
            f"Overall Range: {overall_range}, Trend: {trend}"
        )

    # Вычисление SMA для подтверждения тренда
    sma_50 = (
        df["close"].rolling(window=50).mean().iloc[-1]
        if data_length >= 50
        else df["close"].mean()
    )
    sma_200 = (
        df["close"].rolling(window=200).mean().iloc[-1]
        if data_length >= 200
        else df["close"].mean()
    )
    trend_confirmation = (
        "uptrend_confirmation"
        if sma_50 > sma_200
        else "downtrend_confirmation" if sma_50 < sma_200 else "no_confirmation"
    )

    # Вычисление ATR (если есть достаточно данных)
    atr = None
    if data_length >= 15:
        try:
            atr_series = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14)
            atr = atr_series.iloc[-1] if not atr_series.empty else None
        except Exception as e:
            logging.error(f"Ошибка расчёта ATR для {symbol} {timeframe}: {e}")
    else:
        logging.warning(f"Недостаточно данных для расчёта ATR {symbol} {timeframe}.")

    regression_result = calculate_regression_channel(symbol, timeframe) or {}

    market_structure = {
        "current_price": current_price,
        "trend": trend,
        "trend_confirmation": trend_confirmation,
        "support": support,
        "resistance": resistance,
        "recent_highs": recent_highs,
        "recent_lows": recent_lows,
        "atr": round(atr, 5) if atr is not None else None,
        "regression": regression_result,
        "incomplete_data": data_length < 200,
        "absolute_high": absolute_high,
        "absolute_low": absolute_low,
        "local_high": local_high,
        "local_low": local_low,
    }

    logging.info(f"Структура рынка для {symbol} {timeframe}: {market_structure}")
    return market_structure


def create_instrument_structure(
    symbol: str, timeframe: str, bars: int = 128, local_order: int = 20
) -> Optional[Dict[str, Any]]:
    """
    Создаёт структуру инструмента, объединяя анализ рыночной структуры, расчёт уровней Фибоначчи,
    определение зон ликвидности и индикаторов.

    :param symbol: Символ финансового инструмента.
    :param timeframe: Таймфрейм (например, "M15").
    :param bars: Количество баров для расчётов (по умолчанию 128).
    :param local_order: Порядок для расчёта локальных экстремумов (по умолчанию 20).
    :return: Словарь с данными структуры инструмента или None при ошибке.
    """
    try:
        market_structure = identify_market_structure(symbol, timeframe)
        if market_structure is None:
            raise ValueError(
                f"Не удалось получить структуру рынка для {symbol} {timeframe}."
            )

        trend = market_structure.get("trend", "up")
        if trend not in [
            "uptrend",
            "downtrend",
            "range",
            "strong_uptrend",
            "strong_downtrend",
        ]:
            logging.warning(
                f"Некорректный тренд ({trend}) для {symbol} {timeframe}. Тренд оставлен как '{trend}'."
            )

        fib_result = calculate_fibonacci_levels(
            symbol,
            timeframe,
            trend="up" if "uptrend" in trend else "down",
            bars=bars,
            local_bars=200,
        )
        if fib_result is None:
            raise ValueError(
                f"Не удалось рассчитать уровни Фибоначчи для {symbol} {timeframe}."
            )
        fib_levels = fib_result.get("fib_levels", {})

        liquidity_zones = identify_liquidity_zones(symbol, timeframe)

        indicators_data = get_indicators_data(symbol, timeframe, num_values=bars)
        ohlc_data = indicators_data.get("ohlc")
        if ohlc_data is None:
            raise ValueError(f"OHLC данные отсутствуют для {symbol} {timeframe}.")

        # Локальные экстремумы для поддержки и сопротивления
        df = get_rates_dataframe(symbol, timeframe, bars)
        if df is None or df.empty:
            raise ValueError(
                f"Нет данных для расчёта локальных экстремумов {symbol} {timeframe}."
            )
        local_max_df, local_min_df = get_local_extremes(
            df, column="close", order=local_order
        )
        support = local_min_df["close"].mean() if not local_min_df.empty else None
        resistance = local_max_df["close"].mean() if not local_max_df.empty else None

        instrument_structure = {
            "current_price": market_structure.get("current_price"),
            "trend": trend,
            "support": support,
            "resistance": resistance,
            "fib_levels": fib_levels,
            "liquidity_zones": liquidity_zones,
            "regression": market_structure.get("regression"),
            "atr": market_structure.get("atr"),
            "ohlc": ohlc_data,
        }

        logging.info(
            f"Создана структура инструмента для {symbol} {timeframe}: {instrument_structure}"
        )
        return instrument_structure

    except Exception as e:
        logging.error(f"Ошибка создания структуры инструмента: {e}")
        return None


from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import logging


from brain.optimized.mt5_utils_optimized import get_trade_history

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@method_decorator(csrf_exempt, name="dispatch")
class MarketDataAPIView(View):
    """
    API-представление для получения рыночных данных.
    """

    def get(self, request, *args, **kwargs):
        symbol = request.GET.get("symbol", "EURUSD")  # Символ по умолчанию
        timeframe = request.GET.get("timeframe", "M15")  # Таймфрейм по умолчанию
        num_candles = int(request.GET.get("num_candles", 500))

        try:
            market_data = generate_plotly_data(symbol, timeframe, num_candles)
            structure_data = create_instrument_structure(symbol, timeframe)
            trade_history = get_trade_history()

            response_data = {
                "market_data": market_data,
                "structure": structure_data,
                "trade_history": trade_history,
            }
            return JsonResponse(
                response_data,
                safe=False,
                json_dumps_params={"indent": 4, "ensure_ascii": False},
            )
        except Exception as e:
            logging.error(f"Ошибка при генерации данных API: {e}")
            return JsonResponse({"error": str(e)}, status=500)
