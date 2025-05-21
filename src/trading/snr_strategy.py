# TradeSpace_v3_/src/trading/snr_strategy.py
from src.indicators.market_helpers import identify_liquidity_zones
from src.indicators.market_structure import identify_market_structure
from src.indicators.technical_indicators import calculate_fibonacci_levels, identify_fvg
from src.trading.trading import determine_market_timing

from src.utils.mt5_utils import get_rates_dataframe
from src.indicators.technical_indicators import get_indicators_data


def snr_strategy(symbol, timeframe, num_values=1):
    # Получаем структуру рынка и тренд
    market_structure = identify_market_structure(symbol, timeframe)
    if not market_structure:
        return {"signal": "no_signal"}

    trend = market_structure.get("trend", "range")
    current_price = market_structure["current_price"]
    regression = market_structure.get("regression", {})
    slope = regression.get("slope", 0)

    # Ликвидность и уровни
    sup, res, sec_sup, sec_res = identify_liquidity_zones(symbol, timeframe)
    if sup is None or res is None:
        return {"signal": "no_signal"}

    # Проверим близость цены к уровням: например, если цена в пределах 0.5% от уровня
    def near_level(price, level, tolerance=0.005):
        if level is None:
            return False
        return abs((price - level) / price) < tolerance

    price_near_support = near_level(current_price, sup) or near_level(
        current_price, sec_sup
    )
    price_near_resistance = near_level(current_price, res) or near_level(
        current_price, sec_res
    )

    # FVG-зоны
    df = get_rates_dataframe(symbol, timeframe, 500)
    fvg_zones = identify_fvg(df)

    # Получаем индикаторы
    indicators = get_indicators_data(symbol, timeframe, num_values=num_values)
    if not indicators:
        return {"signal": "no_signal"}

    # Извлечение индикаторов
    macd_values = indicators.get("macd", [None] * num_values)
    signal_values = indicators.get("signal", [None] * num_values)
    atr_values = indicators.get("atr", [None] * num_values)
    rsi_values = indicators.get("rsi", [None] * num_values)
    mfi_values = indicators.get("mfi", [None] * num_values)
    vwap_values = indicators.get("vwap", [None] * num_values)
    stochastic_k = indicators.get("stochastic_k", [None] * num_values)
    stochastic_d = indicators.get("stochastic_d", [None] * num_values)

    # Берем последние значения
    macd_last = macd_values[-1]
    signal_last = signal_values[-1]
    atr_last = atr_values[-1]
    rsi_last = rsi_values[-1]
    mfi_last = mfi_values[-1]
    vwap_last = vwap_values[-1]

    # Проверяем, что ключевые индикаторы не None
    if any(
        x is None
        for x in [macd_last, signal_last, atr_last, rsi_last, mfi_last, vwap_last]
    ):
        return {"signal": "no_signal"}

    # Определим рыночный тайминг
    current_session = determine_market_timing()
    # Если хотим фильтровать по сессии:
    # Торгуем только в активные сессии, например Европейская или Американская
    # if current_session not in ["Европейская сессия", "Американская сессия"]:
    #     return {"signal": "no_signal"}

    # Используем ATR > 0.5 для фильтра по волатильности
    if atr_last is not None and atr_last < 0.5:
        # Слишком низкая волатильность — пропускаем
        return {"signal": "no_signal"}

    # Проверка перекупленности/перепроданности:
    # Для покупок: RSI < 30 или MFI < 30 может указывать на перепроданность
    oversold = (rsi_last is not None and rsi_last < 30) or (
        mfi_last is not None and mfi_last < 30
    )
    # Для продаж: RSI > 70 или MFI > 70 — перекупленность
    overbought = (rsi_last is not None and rsi_last > 70) or (
        mfi_last is not None and mfi_last > 70
    )

    # MACD и Signal для импульса
    bullish_momentum = (
        macd_last is not None and signal_last is not None and macd_last > signal_last
    )
    bearish_momentum = (
        macd_last is not None and signal_last is not None and macd_last < signal_last
    )

    # VWAP: цена выше VWAP — бычий настрой, ниже — медвежий
    above_vwap = vwap_last is not None and vwap_last < current_price
    below_vwap = vwap_last is not None and vwap_last > current_price

    # Slope канала регрессии:
    # slope > 0 — восходящая тенденция, slope < 0 — нисходящая
    # Это дополнительный фильтр к тренду
    up_slope = slope > 0
    down_slope = slope < 0

    # Фибоначчи (опционально)
    fib_levels = calculate_fibonacci_levels(
        symbol, timeframe, "up" if "uptrend" in trend else "down"
    )

    # Логика входа:
    # BUY условие:
    # - Цена у поддержки
    # - Тренд (uptrend/strong_uptrend) или хотя бы up_slope
    # - Перепроданность (oversold)
    # - Bullish momentum (macd > signal)
    # - Цена выше VWAP (опционально, можно ослабить для buy у поддержки)
    # - ATR > 0.5 (уже проверили)
    # Если хотим более гибкий подход, например при покупке от поддержки можно разрешить, чтобы цена была ниже VWAP, считая, что мы покупаем на "дисконт"
    # Но классический подход: лучше, когда выше VWAP. При желании можно убрать это условие или инвертировать.

    if (
        price_near_support
        and ("uptrend" in trend)
        and oversold
        and bullish_momentum
        and (above_vwap or up_slope)
    ):
        return {
            "signal": "buy",
            "trend": trend,
            "support": sup,
            "resistance": res,
            "secondary_support": sec_sup,
            "secondary_resistance": sec_res,
            "fvg_zones": fvg_zones,
            "fib_levels": fib_levels,
            "session": current_session,
        }

    # SELL условие:
    # - Цена у сопротивления
    # - Тренд (downtrend/strong_downtrend) или down_slope
    # - Перекупленность (overbought)
    # - Bearish momentum (macd < signal)
    # - Цена ниже VWAP
    # - ATR > 0.5
    if (
        price_near_resistance
        and ("downtrend" in trend)
        and overbought
        and bearish_momentum
        and (below_vwap or down_slope)
    ):
        return {
            "signal": "sell",
            "trend": trend,
            "support": sup,
            "resistance": res,
            "secondary_support": sec_sup,
            "secondary_resistance": sec_res,
            "fvg_zones": fvg_zones,
            "fib_levels": fib_levels,
            "session": current_session,
        }

    # Если условия не выполнились
    return {
        "signal": "no_signal",
        "trend": trend,
        "support": sup,
        "resistance": res,
        "secondary_support": sec_sup,
        "secondary_resistance": sec_res,
        "fvg_zones": fvg_zones,
        "fib_levels": fib_levels,
        "session": current_session,
    }
