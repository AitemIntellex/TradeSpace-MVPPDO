import logging
from src.indicators.market_helpers import identify_liquidity_zones
from src.indicators.market_structure import identify_market_structure
from src.indicators.technical_indicators import calculate_fibonacci_levels, identify_fvg
from src.trading.trading import determine_market_timing
from src.utils.mt5_utils import get_rates_dataframe
import plotly.graph_objects as go

def get_snr_plotly_data(symbol, timeframe, num_values=1):
    """
    Подготавливает данные для визуализации SNR-стратегии с использованием Plotly.
    """
    # Получаем данные
    df = get_rates_dataframe(symbol, timeframe, 500)
    if df is None or df.empty:
        return {"error": "Нет данных"}

    market_structure = identify_market_structure(symbol, timeframe)
    if not market_structure:
        return {"error": "Не удалось определить структуру рынка"}

    trend = market_structure.get("trend", "range")
    current_price = market_structure["current_price"]
    regression = market_structure.get("regression", {})
    slope = regression.get("slope", 0)

    liquidity_zones = identify_liquidity_zones(symbol, timeframe)
    fvg_zones = identify_fvg(df)
    fib_result = calculate_fibonacci_levels(symbol, timeframe, trend="up" if "uptrend" in trend else "down", bars=500, local_bars=100)
    fib_levels = fib_result.get("fib_levels", {}) if fib_result else {}

    # Подготовка данных для Plotly
    traces = []

    # Добавляем свечи OHLC
    traces.append(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="OHLC"
    ))

    # Добавляем уровни Фибоначчи
    for level, price in fib_levels.items():
        if price:
            traces.append(go.Scatter(
                x=[df.index[0], df.index[-1]],
                y=[price, price],
                mode="lines",
                name=f"Fibo {level}",
                line=dict(dash="dash")
            ))

    # Добавляем зоны FVG
    if isinstance(fvg_zones, list):
        for zone in fvg_zones:
            traces.append(go.Scatter(
                x=[df.index[0], df.index[-1]],
                y=[zone["high"], zone["low"]],
                mode="lines",
                name="FVG",
                line=dict(color="red", dash="dot")
            ))

    return {
        "traces": traces,
        "trend": trend,
        "current_price": current_price,
        "fib_levels": fib_levels,
        "fvg_zones": fvg_zones,
        "liquidity_zones": liquidity_zones,
        "slope": slope
    }
