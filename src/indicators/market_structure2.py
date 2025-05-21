import talib
from src.indicators.technical_indicators import (
    calculate_fibonacci_levels,
    get_indicators_data,
)
from src.utils.mt5_utils import get_rates_dataframe
import numpy as np
from src.indicators.market_helpers import identify_liquidity_zones
from src.trading.trading import log_data_error
from scipy.signal import argrelextrema
import logging


def get_local_extremes(df, column="close", order=10):
    values = df[column].values
    local_max_indices = argrelextrema(values, comparator=np.greater, order=order)[0]
    local_min_indices = argrelextrema(values, comparator=np.less, order=order)[0]
    return df.iloc[local_max_indices], df.iloc[local_min_indices]


def identify_market_structure(symbol, timeframe):
    """
    Анализ структуры рынка для заданного символа и таймфрейма.

    :param symbol: Символ финансового инструмента.
    :param timeframe: Таймфрейм (например, mt5.TIMEFRAME_H1).
    :return: Словарь с информацией о структуре рынка или None при ошибке.
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

    # Локальные экстремумы
    local_highs, local_lows = get_local_extremes(df, column="close", order=20)
    local_high = local_highs["close"].max() if not local_highs.empty else None
    local_low = local_lows["close"].min() if not local_lows.empty else None

    # Вычисление локальных экстремумов
    local_highs, local_lows = get_local_extremes(df, column="close", order=20)
    support = local_lows["close"].mean() if not local_lows.empty else None
    resistance = local_highs["close"].mean() if not local_highs.empty else None

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
        overall_range = df["high"].max() - df["low"].min()
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

    # Вычисление ATR
    atr = None
    if data_length >= 15:  # ATR требует минимум 14 периодов
        try:
            atr = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14).iloc[-1]
        except Exception as e:
            logging.error(f"Ошибка расчёта ATR для {symbol} {timeframe}: {e}")
    else:
        logging.warning(f"Недостаточно данных для расчёта ATR {symbol} {timeframe}.")

    # Вычисление регрессионного канала
    regression_result = calculate_regression_channel(symbol, timeframe) or {}

    # Создание структуры рынка
    market_structure = {
        "current_price": current_price,
        "trend": trend,
        "trend_confirmation": trend_confirmation,
        "support": support,
        "resistance": resistance,
        "recent_highs": recent_highs,
        "recent_lows": recent_lows,
        "atr": atr,
        "regression": regression_result,
        "incomplete_data": data_length < 200,
        "absolute_high": absolute_high,
        "absolute_low": absolute_low,
        "local_high": local_high,
        "local_low": local_low,
    }

    # Логирование результата
    logging.info(f"Структура рынка для {symbol} {timeframe}: {market_structure}")

    return market_structure


import numpy as np


def create_instrument_structure(symbol, timeframe, bars=128, local_order=20):
    """
    Создает идентификатор структуры инструмента на основе ключевых данных.
    """
    try:
        # Определение структуры рынка
        market_structure = identify_market_structure(symbol, timeframe)
        if market_structure is None:
            raise ValueError(
                f"Не удалось получить структуру рынка для {symbol} {timeframe}."
            )

        trend = market_structure.get("trend", "up")
        if trend not in ["uptrend", "downtrend", "range"]:
            logging.warning(
                f"Некорректный тренд ({trend}) для {symbol} {timeframe}. "
                f"Тренд оставлен как '{trend}'."
            )

        # Расчет уровней Фибоначчи
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

        # Определение зон ликвидности
        liquidity_zones = identify_liquidity_zones(symbol, timeframe)

        # Получение индикаторов (включает OHLC)
        indicators_data = get_indicators_data(symbol, timeframe, num_values=bars)
        ohlc_data = indicators_data.get("ohlc")
        if ohlc_data is None:
            raise ValueError(f"OHLC данные отсутствуют для {symbol} {timeframe}")

        # Локальные экстремумы
        df = get_rates_dataframe(symbol, timeframe, bars)
        local_highs, local_lows = get_local_extremes(
            df, column="close", order=local_order
        )
        support = local_lows["close"].mean()
        resistance = local_highs["close"].mean()

        # Объединение данных в структуру инструмента
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


def calculate_regression_channel(symbol, timeframe):
    """Calculate the regression channel for a given symbol and timeframe.

    Args:
        symbol (str): The financial instrument symbol.
        timeframe (str): The timeframe for the data.

    Returns:
        dict or None: Contains slope, intercept, upper_channel, and lower_channel if successful; otherwise None.
    """
    df = get_rates_dataframe(symbol, timeframe, period=500)

    if df is None or df.empty:
        logging.error(
            f"Ошибка: Недостаточно данных для регрессионного анализа по символу {symbol} и таймфрейму {timeframe}"
        )
        return None

    x = np.arange(len(df))
    y = df["close"]

    try:
        slope, intercept = np.polyfit(x, y, 1)
    except ValueError as e:
        logging.error(f"Ошибка при расчете линейной регрессии для {symbol}: {e}")
        return None

    std_dev = np.std(y)
    upper_channel = intercept + slope * x + std_dev
    lower_channel = intercept + slope * x - std_dev

    # Округляем до 5 знаков после запятой
    regression_result = {
        "slope": round(slope, 5),  # Наклон
        "intercept": round(intercept, 5),  # Пересечение
        "upper_channel": round(upper_channel[-1], 5),  # Верхний канал
        "lower_channel": round(lower_channel[-1], 5),  # Нижний канал
    }

    logging.info(
        f"Регрессионный анализ для {symbol} ({timeframe}): наклон={regression_result['slope']}, "
        f"пересечение={regression_result['intercept']}, верхний канал={regression_result['upper_channel']}, "
        f"нижний канал={regression_result['lower_channel']}"
    )

    return regression_result  # Возвращаем результаты регрессионного анализа
