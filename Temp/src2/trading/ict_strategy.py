import logging
from src.indicators.market_helpers import identify_liquidity_zones
from src.indicators.market_structure import identify_market_structure
from src.indicators.technical_indicators import get_indicators_data
from src.indicators.technical_indicators import calculate_fibonacci_levels, identify_fvg
from src.trading.trading import determine_market_timing
from src.indicators.market_helpers import identify_liquidity_zones

from src.utils.mt5_utils import get_rates_dataframe


def ict_strategy(symbol, timeframe, num_values=1):
    """
    Стратегия ICT с учётом новых Fibonacci уровней,
    где calculate_fibonacci_levels возвращает расширенный словарь.
    """
    # 1. Определяем структуру рынка
    market_structure = identify_market_structure(symbol, timeframe)
    if not market_structure:
        return {"signal": "no_signal"}

    trend = market_structure.get("trend", "range")
    current_price = market_structure["current_price"]
    regression = market_structure.get("regression", {})
    slope = regression.get("slope", 0)

    # 2. Ищем зоны ликвидности
    sup, res, sec_sup, sec_res = identify_liquidity_zones(symbol, timeframe)
    if sup is None or res is None:
        return {"signal": "no_signal"}

    # 3. Получаем DataFrame для FVG
    df = get_rates_dataframe(symbol, timeframe, 500)
    fvg_zones = identify_fvg(df)

    # 4. Вычисляем уровни Фибоначчи (новая функция)
    #    - Используем bars=500 и local_bars=100 (или при желании другие).
    #    - trend='up' если есть 'uptrend', иначе 'down'.
    fib_result = calculate_fibonacci_levels(
        symbol,
        timeframe,
        trend="up" if "uptrend" in trend else "down" if "downtrend" in trend else "up",
        bars=500,
        local_bars=100,
    )

    # Проверяем, что fib_result не None
    if fib_result is None:
        # Значит, произошла ошибка или нет данных
        fib_levels = {}
    else:
        fib_levels = fib_result.get("fib_levels", {})

    # 5. Формируем список OTE уровней из fib_levels
    ote_levels = ["61.8%", "70.5%", "79.0%"]
    fib_ote_prices = [fib_levels.get(lv) for lv in ote_levels] if fib_levels else []

    def price_in_ote(price, ote_prices, tolerance=0.005):
        """
        Проверяем, находится ли 'price' в диапазоне между
        MIN(ote_prices) и MAX(ote_prices), с учётом tolerance.
        """
        if not ote_prices or len(ote_prices) < 2:
            return False

        # Оставим только валидные значения (не None)
        valid_prices = [p for p in ote_prices if p is not None]
        if len(valid_prices) < 2:
            return False

        ote_min = min(valid_prices)
        ote_max = max(valid_prices)

        # Проверяем, что цена в (ote_min*(1-tol), ote_max*(1+tol))
        return (price >= ote_min * (1 - tolerance)) and (
            price <= ote_max * (1 + tolerance)
        )

    in_ote = price_in_ote(current_price, fib_ote_prices)

    # 6. Индикаторы
    indicators = get_indicators_data(symbol, timeframe, num_values=num_values)
    if not indicators:
        return {"signal": "no_signal"}

    macd_values = indicators.get("macd", [None] * num_values)
    signal_values = indicators.get("signal", [None] * num_values)
    atr_values = indicators.get("atr", [None] * num_values)
    rsi_values = indicators.get("rsi", [None] * num_values)
    mfi_values = indicators.get("mfi", [None] * num_values)
    vwap_values = indicators.get("vwap", [None] * num_values)

    # Берём последние значения
    macd_last = macd_values[-1]
    signal_last = signal_values[-1]
    atr_last = atr_values[-1]
    rsi_last = rsi_values[-1]
    mfi_last = mfi_values[-1]
    vwap_last = vwap_values[-1]

    # Проверка базовых индикаторов (если что-то None, нет сигнала)
    if any(
        x is None
        for x in [macd_last, signal_last, atr_last, rsi_last, mfi_last, vwap_last]
    ):
        return {"signal": "no_signal"}

    # 7. Маркет тайминг (опциональный фильтр)
    current_session = determine_market_timing()
    # if current_session not in ["Европейская сессия", "Американская сессия"]:
    #     return {"signal": "no_signal"}

    # 8. Фильтр по волатильности (ATR > 0.5)
    if atr_last < 0.5:
        return {"signal": "no_signal"}

    # 9. Логика RSI / MFI (перекупленность/перепроданность)
    oversold = (rsi_last < 30) or (mfi_last < 30)
    overbought = (rsi_last > 70) or (mfi_last > 70)

    # Логика MACD (импульс)
    bullish_momentum = macd_last > signal_last
    bearish_momentum = macd_last < signal_last

    # VWAP
    above_vwap = (vwap_last is not None) and (current_price > vwap_last)
    below_vwap = (vwap_last is not None) and (current_price < vwap_last)

    # 10. Определение расположения FVG (хотим FVG ниже цены для лонга, выше — для шорта)
    fvg_below = False
    fvg_above = False
    if fvg_zones != "Нет данных":
        for zone in fvg_zones:
            mid_fvg = (zone["low"] + zone["high"]) / 2
            if mid_fvg < current_price:
                fvg_below = True
            else:
                fvg_above = True

    # 11. BUY условие (ICT классика для лонга):
    # - Тренд восходящий ("uptrend" in trend)
    # - Цена в OTE зоне (61.8% - 79%)
    # - oversold (rsi/mfi низкие)
    # - bullish_momentum (macd > signal)
    # - ATR > 0.5
    # - slope > 0, fvg_below = True (есть FVG ниже цены)
    if (
        ("uptrend" in trend)
        and in_ote
        and oversold
        and bullish_momentum
        and atr_last > 0.5
        and slope > 0
        and fvg_below
    ):
        return {
            "signal": "buy",
            "trend": trend,
            "support": sup,
            "resistance": res,
            "secondary_support": sec_sup,
            "secondary_resistance": sec_res,
            "fvg_zones": fvg_zones,
            "fib_result": fib_result,  # Сразу возвращаем весь словарь
            "fib_levels": fib_levels,  # Или отдельно, если нужно
            "session": current_session,
        }

    # 12. SELL условие (ICT классика для шорта):
    # - Тренд нисходящий ("downtrend" in trend)
    # - Цена в OTE зоне для шорта
    # - overbought (rsi/mfi высокие)
    # - bearish_momentum (macd < signal)
    # - ATR > 0.5
    # - slope < 0, fvg_above = True
    if (
        ("downtrend" in trend)
        and in_ote
        and overbought
        and bearish_momentum
        and atr_last > 0.5
        and slope < 0
        and fvg_above
    ):
        return {
            "signal": "sell",
            "trend": trend,
            "support": sup,
            "resistance": res,
            "secondary_support": sec_sup,
            "secondary_resistance": sec_res,
            "fvg_zones": fvg_zones,
            "fib_result": fib_result,
            "fib_levels": fib_levels,
            "session": current_session,
        }

    # 13. Иначе нет сигнала, но вернём данные для веба
    return {
        "signal": "no_signal",
        "trend": trend,
        "support": sup,
        "resistance": res,
        "secondary_support": sec_sup,
        "secondary_resistance": sec_res,
        "fvg_zones": fvg_zones,
        "fib_result": fib_result,
        "fib_levels": fib_levels,
        "session": current_session,
    }
