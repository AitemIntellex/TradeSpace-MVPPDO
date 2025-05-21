import logging
import numpy as np
import plotly.graph_objects as go
from brain.optimized.mt5_utils_optimized import get_rates_dataframe
from src.indicators.technical_indicators import (
    get_indicators_data,
    calculate_fibonacci_levels,
    identify_fvg,
)
from src.indicators.market_helpers import identify_liquidity_zones
from src.indicators.market_structure import identify_market_structure


def get_trading_plotly_data(symbol, timeframe):
    """
    Генерирует данные для визуализации в Plotly для анализа торговли.
    """
    df = get_rates_dataframe(symbol, timeframe, 500)
    if df is None or df.empty:
        return {"error": "Нет данных"}

    market_structure = identify_market_structure(symbol, timeframe)
    if not market_structure:
        return {"error": "Не удалось определить структуру рынка"}

    trend = market_structure.get("trend", "range")
    current_price = market_structure["current_price"]
    fib_levels = calculate_fibonacci_levels(symbol, timeframe, trend)
    fvg_zones = identify_fvg(df)
    liquidity_zones = identify_liquidity_zones(symbol, timeframe)
    indicators = get_indicators_data(symbol, timeframe)

    traces = []

    # Добавляем свечи OHLC
    traces.append(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC",
        )
    )

    # Добавляем уровни Фибоначчи
    if fib_levels:
        for level, price in fib_levels.items():
            traces.append(
                go.Scatter(
                    x=[df.index[0], df.index[-1]],
                    y=[price, price],
                    mode="lines",
                    name=f"Fibo {level}",
                    line=dict(dash="dash"),
                )
            )

    # Добавляем зоны FVG
    if fvg_zones:
        for zone in fvg_zones:
            traces.append(
                go.Scatter(
                    x=[df.index[0], df.index[-1]],
                    y=[zone["high"], zone["low"]],
                    mode="lines",
                    name="FVG",
                    line=dict(color="red", dash="dot"),
                )
            )

    return {
        "traces": traces,
        "trend": trend,
        "current_price": current_price,
        "fib_levels": fib_levels,
        "fvg_zones": fvg_zones,
        "liquidity_zones": liquidity_zones,
        "indicators": indicators,
    }
