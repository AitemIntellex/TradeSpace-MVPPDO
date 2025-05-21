# src/indicators/market_helpers.py
import logging
import numpy as np
import talib
from src.utils.mt5_utils import get_rates_dataframe


import logging

import talib

from src.indicators.technical_indicators import calculate_fibonacci_levels
from src.utils.mt5_utils import get_rates_dataframe

from src.trading.trading import calculate_regression_channel, log_data_error


def identify_market_structure(symbol, timeframe):
    df = get_rates_dataframe(symbol, timeframe, 500)
    if df is None or df.empty:
        log_data_error(symbol)
        return None

    # Проверяем, достаточно ли данных для SMA 200
    if len(df) < 200:
        logging.warning(
            f"Недостаточно данных для полного анализа {symbol} {timeframe}. Доступно {len(df)} баров."
        )
        # Можно либо вернуть None, либо продолжить, но результаты будут менее точными

    high = df["high"].max()
    low = df["low"].min()
    current_price = df["close"].iloc[-1]

    # Убедимся, что достаточно данных для rolling(20)
    if len(df) < 20:
        logging.warning(
            f"Мало данных для анализа 20-периодного тренда {symbol} {timeframe}."
        )
        # Можно сделать fallback или вернуть None

    recent_highs = df["high"].rolling(window=20).max().iloc[-1]
    recent_lows = df["low"].rolling(window=20).min().iloc[-1]

    if current_price > recent_highs:
        trend = "strong_uptrend"
    elif current_price < recent_lows:
        trend = "strong_downtrend"
    else:
        # Проверка на "range"
        if (recent_highs - recent_lows) < (high - low) * 0.2:
            trend = "range"
        else:
            trend = "uptrend" if current_price > df["close"].mean() else "downtrend"

    # Расчёт SMA
    sma_50 = (
        df["close"].rolling(window=50).mean().iloc[-1]
        if len(df) >= 50
        else df["close"].mean()
    )
    sma_200 = (
        df["close"].rolling(window=200).mean().iloc[-1]
        if len(df) >= 200
        else df["close"].mean()
    )

    if sma_50 > sma_200:
        trend_confirmation = "uptrend_confirmation"
    elif sma_50 < sma_200:
        trend_confirmation = "downtrend_confirmation"
    else:
        trend_confirmation = "no_confirmation"

    # Проверяем наличие достаточных данных для ATR
    if len(df) < 15:  # ATR 14 периодов
        logging.warning(f"Недостаточно данных для расчета ATR {symbol} {timeframe}.")
        atr = None
    else:
        atr = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14).iloc[-1]

    regression_result = calculate_regression_channel(symbol, timeframe) or {}

    market_structure = {
        "current_price": current_price,
        "trend": trend,
        "trend_confirmation": trend_confirmation,
        "support": low,
        "resistance": high,
        "recent_highs": recent_highs,
        "recent_lows": recent_lows,
        "atr": atr,
        "regression": regression_result,
        "incomplete_data": len(df) < 200,  # Флаг для проверки полноты данных
    }

    return market_structure


def identify_liquidity_zones(symbol, timeframe):
    df = get_rates_dataframe(symbol, timeframe, 500)
    if df is None:
        log_data_error(symbol)
        return None, None, None, None

    support_level = df["low"].min()
    resistance_level = df["high"].max()

    filtered_df = df[
        (df["high"] < df["high"].quantile(0.95))
        & (df["low"] > df["low"].quantile(0.05))
    ]
    secondary_support = filtered_df["low"].min()
    secondary_resistance = filtered_df["high"].max()

    regression_result = calculate_regression_channel(symbol, timeframe)
    if regression_result:
        secondary_support = min(secondary_support, regression_result["lower_channel"])
        secondary_resistance = max(
            secondary_resistance, regression_result["upper_channel"]
        )

    return support_level, resistance_level, secondary_support, secondary_resistance
