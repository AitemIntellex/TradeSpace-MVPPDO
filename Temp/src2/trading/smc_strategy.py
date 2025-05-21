from src.indicators.market_helpers import identify_liquidity_zones
from src.indicators.market_structure import identify_market_structure
from src.indicators.technical_indicators import calculate_fibonacci_levels, identify_fvg
from src.trading.trading import determine_market_timing

from src.utils.mt5_utils import get_rates_dataframe
from src.indicators.technical_indicators import get_indicators_data


def smc_strategy(symbol, timeframe, num_values=1):
    # Получаем данные рыночной структуры
    market_structure = identify_market_structure(symbol, timeframe)
    if not market_structure:
        return {"signal": "no_signal"}

    trend = market_structure.get("trend", "range")
    current_price = market_structure["current_price"]
    support = market_structure.get("support", None)
    resistance = market_structure.get("resistance", None)
    regression = market_structure.get("regression", {})
    slope = regression.get("slope", 0)

    # Зоны ликвидности
    sup, res, sec_sup, sec_res = identify_liquidity_zones(symbol, timeframe)
    if sup is None or res is None:
        return {"signal": "no_signal"}

    # Получаем DataFrame для FVG
    df = get_rates_dataframe(symbol, timeframe, 500)
    fvg_zones = identify_fvg(df)

    # Уровни Фибоначчи (берем для тренда)
    fib_levels = calculate_fibonacci_levels(
        symbol, timeframe, trend="up" if "uptrend" in trend else "down"
    )

    # Индикаторы
    indicators = get_indicators_data(symbol, timeframe, num_values=num_values)
    if not indicators:
        return {"signal": "no_signal"}

    # Извлекаем последние значения индикаторов
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

    # Проверка на наличие значений
    if any(
        x is None
        for x in [macd_last, signal_last, atr_last, rsi_last, mfi_last, vwap_last]
    ):
        return {"signal": "no_signal"}

    # Маркет тайминг (опционально)
    current_session = determine_market_timing()
    # Предположим, торгуем только во время Европейской или Американской сессии
    if current_session not in ["Европейская сессия", "Американская сессия"]:
        # Можно возвращать no_signal или же игнорировать тайминг
        pass

    # Проверим наличие FVG: например, для лонга хотим FVG-зону чуть ниже цены, для шорта — выше
    # Это условно: если нет данных о расположении FVG, просто пропускаем этот фильтр
    fvg_below = False
    fvg_above = False
    if fvg_zones != "Нет данных":
        for zone in fvg_zones:
            if zone["low"] < current_price < zone["high"]:
                # FVG вокруг цены — можно интерпретировать по-разному, но допустим:
                # если среднее значение FVG зоны ниже текущей цены, считаем это "fvg_below"
                mid_fvg = (zone["low"] + zone["high"]) / 2
                if mid_fvg < current_price:
                    fvg_below = True
                else:
                    fvg_above = True

    # Определение OTE (Optimal Trade Entry) через Fib: для восходящего тренда интересен район 61.8% - 79%
    ote_levels = ["61.8%", "70.5%", "79.0%"]
    fib_ote_range = []
    if fib_levels:
        fib_ote_range = [fib_levels.get(lv) for lv in ote_levels if lv in fib_levels]

    # Условие для BUY:
    # - Тренд восходящий (uptrend/strong_uptrend)
    # - Цена близка к поддержке или вторичной поддержке (current_price ≈ sup или sec_sup), допустим в пределах 0.5% от них
    # - RSI < 30, MFI < 30 (перепроданность)
    # - MACD > Signal (бычий импульс)
    # - ATR > 0.5 (достаточная волатильность)
    # - Цена выше VWAP (цена в зоне премии для покупателей)
    # - slope > 0 (регрессия восходящая)
    # - FVG ниже цены (fvg_below = True) для потенциальной зоны ликвидности
    # - Цена недалеко от OTE-зоны по Фибоначчи (например, в пределах одной из fib_ote_range)

    price_near_support = (
        sup is not None and abs((current_price - sup) / current_price) < 0.005
    ) or (
        sec_sup is not None and abs((current_price - sec_sup) / current_price) < 0.005
    )
    price_in_ote = False
    if fib_ote_range:
        # Проверим, попадает ли цена в одну из OTE зон ±0.5%
        for fib_price in fib_ote_range:
            if fib_price and abs((current_price - fib_price) / current_price) < 0.005:
                price_in_ote = True
                break

    if (
        ("uptrend" in trend)
        and price_near_support
        and (rsi_last < 30 or mfi_last < 30)
        and (macd_last > signal_last)
        and (atr_last > 0.5)
        and vwap_last is not None
        and (vwap_last < current_price)
        and slope > 0
        and fvg_below
        and price_in_ote
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

    # Условие для SELL (аналогично, но наоборот):
    # - Тренд нисходящий
    # - Цена близка к сопротивлению
    # - RSI > 70, MFI > 70 (перекупленность)
    # - MACD < Signal (медвежий импульс)
    # - ATR > 0.5
    # - Цена ниже VWAP
    # - slope < 0
    # - FVG выше цены
    # - Цена в OTE зоне для шорта (если тренд down, fib_levels рассчитаны для down, аналогично проверяем OTE)
    # Для краткости возьмём те же условия, но зеркально.

    if (
        ("downtrend" in trend)
        and (res is not None and abs((current_price - res) / current_price) < 0.005)
        and (rsi_last > 70 or mfi_last > 70)
        and (macd_last < signal_last)
        and (atr_last > 0.5)
        and (vwap_last is not None and vwap_last > current_price)
        and slope < 0
        and fvg_above
        and price_in_ote
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

    # Если ничего не подошло, возвращаем no_signal
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
