import datetime
import MetaTrader5 as mt5
from src.trading import ict_strategy
from src.utils.mt5_utils import get_ohlc
from src.trading.trading import (
    get_rates_dataframe,
    get_indicators_data,
    calculate_macd,
    calculate_rsi,
    calculate_atr,
    calculate_bollinger_bands,
    identify_fvg,
    identify_liquidity_zones,
    calculate_fibonacci_levels,
    smc_strategy,
)


def analyze_market_and_indicators(symbol, timeframe):
    # Получаем данные один раз и передаем их всем анализам
    df = get_rates_dataframe(symbol, timeframe, 100)

    if df is None:
        print(f"Ошибка: Не удалось получить данные для {symbol}")
        return None

    # Анализ структуры рынка
    market_structure = analyze_market_structure(df)

    # Анализ ликвидности
    liquidity_zones = identify_liquidity_zones(df)

    # FVG (разрывы справедливой стоимости)
    fvg_zones = identify_fvg(df)

    # Оптимальные точки входа (OTE)
    ote_levels = calculate_ote(df)

    # Тайминги рынка
    market_timing = analyze_market_timing()

    return {
        "market_structure": market_structure,
        "liquidity_zones": liquidity_zones,
        "fvg_zones": fvg_zones,
        "ote_levels": ote_levels,
        "market_timing": market_timing,
    }


import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)


def analyze_market_structure(symbol, timeframe):
    try:
        indicators = get_indicators_data(symbol, timeframe)
        if not indicators:
            raise Exception("Не удалось получить данные индикаторов")

        short_ma = indicators.get("sma")
        long_ma = indicators.get("long_ma")

        trend = "не удалось определить тренд"
        if short_ma and long_ma:
            if short_ma > long_ma:
                trend = "восходящий"
            elif short_ma < long_ma:
                trend = "нисходящий"
            else:
                trend = "боковой"

        rsi = indicators.get("rsi")
        if rsi:
            if rsi > 70:
                trend += " (перекупленность)"
            elif rsi < 30:
                trend += " (перепроданность)"

        macd_value = indicators.get("macd")
        signal_value = indicators.get("signal")
        if macd_value and signal_value:
            if macd_value > signal_value:
                trend += " (подтвержден MACD)"

        ohlc_data = get_ohlc(symbol, timeframe, 100)
        support = min(ohlc_data["low"])
        resistance = max(ohlc_data["high"])

        return {
            "trend": trend,
            "key_levels": {"support": support, "resistance": resistance},
            "pulse_and_corrections": "Анализ импульсов и коррекций",
        }

    except Exception as e:
        logging.error(f"Ошибка анализа структуры рынка: {e}")
        return {"error": str(e)}


def identify_liquidity_zones(symbol, timeframe):
    """
    Идентификация зон ликвидности (уровни поддержки и сопротивления).
    """
    df = get_rates_dataframe(symbol, timeframe, 100)
    if df is None:
        print(f"Ошибка: Не удалось получить данные для {symbol}")
        return None, None

    support_level = df["low"].min()
    resistance_level = df["high"].max()

    return support_level, resistance_level


def calculate_ote(symbol, timeframe):
    """
    Вычисление оптимальных точек входа (OTE) с использованием уровней Фибоначчи.
    """
    return calculate_fibonacci_levels(symbol, 100, timeframe)


def analyze_market_timing():
    """
    Анализ времени торговых сессий и активности рынка.
    """
    current_time = datetime.now()
    if 9 <= current_time.hour <= 18:
        current_session = "Европейская сессия"
    else:
        current_session = "Азиатская сессия"

    active_time = f"Текущее время: {current_time.strftime('%H:%M')}"
    return {"current_session": current_session, "active_time": active_time}


# Стратегии ICT и SMC
def execute_ict_strategy(symbol, timeframe):
    return ict_strategy(symbol, timeframe)


def execute_smc_strategy(symbol, timeframe):
    return smc_strategy(symbol, timeframe)
