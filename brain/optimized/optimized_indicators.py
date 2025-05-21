import datetime
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
import pandas as pd
import talib
import MetaTrader5 as mt5

from brain.optimized.mt5_utils_optimized import get_rates_dataframe

from logs.logi import (
    log_market_structure,
    log_fibonacci_levels,
    log_fvg_zones,
    log_ict_result,
)
from src.utils.mt5_utils import get_currency_tick

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# ------------------------------ Вспомогательные функции ------------------------------


def log_data_error(symbol: str) -> None:
    logging.error(f"Ошибка получения данных для {symbol}.")


def save_json(data: Any, filename: str) -> None:
    """Сохраняет данные в JSON-файл с отступами и поддержкой Unicode."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def df_to_json(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Преобразует DataFrame в список словарей с округлением значений до 5 знаков."""
    return df.round(5).to_dict(orient="records")


# ------------------------------ Технические индикаторы ------------------------------


def calculate_moving_average(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Вычисляет скользящую среднюю по цене закрытия."""
    if len(data) < period:
        return pd.Series([None] * len(data))
    return data["close"].rolling(window=period).mean()


def analyze_market_timing() -> Dict[str, str]:
    """Анализирует время торговых сессий и активность рынка."""
    current_time = datetime.datetime.now()
    current_session = (
        "Европейская сессия" if 9 <= current_time.hour <= 18 else "Азиатская сессия"
    )
    return {
        "current_session": current_session,
        "active_time": f"Текущее время: {current_time.strftime('%H:%M')}",
    }


def identify_fvg(
    df: pd.DataFrame,
    lookback: int = 500,
    tolerance: float = 0.01,
    min_gap_candles: int = 2,
) -> Any:
    """
    Идентифицирует FVG-зоны на основе переданных данных.
    Если данных меньше, чем lookback, то lookback уменьшается.
    """
    if len(df) < lookback:
        logging.warning(
            f"Недостаточно данных для анализа FVG. Будет использовано lookback={len(df)-1}"
        )
        lookback = len(df) - 1

    fvg_zones = []
    logging.info(f"Проверка FVG на последних {lookback} свечах")

    for i in range(len(df) - lookback, len(df) - min_gap_candles):
        high_prev = df["high"].iloc[i]
        low_next = df["low"].iloc[i + min_gap_candles]
        if high_prev < low_next * (1 - tolerance):
            zone = {
                "start": (
                    df.index[i].isoformat()
                    if isinstance(df.index[i], datetime.datetime)
                    else str(df.index[i])
                ),
                "end": (
                    df.index[i + min_gap_candles].isoformat()
                    if isinstance(df.index[i + min_gap_candles], datetime.datetime)
                    else str(df.index[i + min_gap_candles])
                ),
                "high": round(high_prev, 5),
                "low": round(low_next, 5),
            }
            fvg_zones.append(zone)
            logging.info(f"Найдена FVG-зона: {zone}")

    return fvg_zones if fvg_zones else "Нет данных"


# ------------------------------ Pivot Points и Фибоначчи ------------------------------


def calculate_pivot_points(
    symbol: str, timeframe: Any, num_values: int = 128
) -> List[Dict[str, Any]]:
    """
    Рассчитывает классические Pivot Points (Pivot, S1, S2, S3, R1, R2, R3).
    """
    df = get_rates_dataframe(symbol, timeframe, num_values + 1)
    if df is None or df.empty:
        logging.warning(f"[Pivot] Нет данных для {symbol} на {timeframe}")
        return []
    results = []
    for i in range(num_values):
        high = df["high"].iloc[-(i + 2)]
        low = df["low"].iloc[-(i + 2)]
        close = df["close"].iloc[-(i + 2)]
        pivot = (high + low + close) / 3.0
        r1 = (2 * pivot) - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        s1 = (2 * pivot) - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)
        results.append(
            {
                "period": i + 1,
                "pivot": round(pivot, 5),
                "pp_resistance": [round(r1, 5), round(r2, 5), round(r3, 5)],
                "pp_support": [round(s1, 5), round(s2, 5), round(s3, 5)],
            }
        )
    return results


def calculate_fibonacci_pivot_points(
    high: float, low: float, close: float
) -> Dict[str, Any]:
    """
    Рассчитывает уровни Fibonacci Pivot Point.
    """
    pivot = (high + low + close) / 3.0
    diff = high - low
    return {
        "Pivot": round(pivot, 5),
        "Resistance": [round(pivot + diff * r, 5) for r in [0.382, 0.618, 1.0]],
        "Support": [round(pivot - diff * r, 5) for r in [0.382, 0.618, 1.0]],
    }


def find_nearest_levels(
    fib_levels: Dict[str, float], current_price: float
) -> Dict[str, Optional[float]]:
    """
    Определяет ближайшие уровни поддержки и сопротивления относительно текущей цены.
    """
    supports = {
        lvl: price
        for lvl, price in fib_levels.items()
        if isinstance(price, (int, float)) and price < current_price
    }
    resistances = {
        lvl: price
        for lvl, price in fib_levels.items()
        if isinstance(price, (int, float)) and price > current_price
    }
    nearest_support = max(supports.values(), default=None) if supports else None
    nearest_resistance = (
        min(resistances.values(), default=None) if resistances else None
    )
    return {
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
    }


def calculate_fibonacci_time_zones(
    start_time: datetime.datetime, end_time: datetime.datetime, num_zones: int = 12
) -> Dict[str, str]:
    """
    Рассчитывает временные зоны Фибоначчи между двумя временными точками.
    """
    duration = (end_time - start_time).total_seconds()
    fib_ratios = [0.236, 0.382, 0.5, 0.618, 1.0, 1.618, 2.618, 4.236]
    time_zones = {}
    for i, ratio in enumerate(fib_ratios[:num_zones]):
        zone_key = f"Zone {i+1} ({ratio*100:.1f}%)"
        zone_time = start_time + datetime.timedelta(seconds=ratio * duration)
        time_zones[zone_key] = zone_time.isoformat()
    return time_zones


def calculate_fibonacci_levels(
    symbol: str,
    timeframe: Any,
    trend: str = "up",
    bars: int = 500,
    local_bars: int = 128,
) -> Optional[Dict[str, Any]]:
    """
    Рассчитывает уровни Фибоначчи на основе локальных high/low за последние `local_bars` свечей.
    """
    df = get_rates_dataframe(symbol, timeframe, bars)
    log_messages = []

    if df is None or df.empty:
        msg = f"[FIB] Нет данных для {symbol} {timeframe}."
        logging.error(msg)
        log_messages.append(msg)
        return None

    actual_bars_loaded = len(df)
    if actual_bars_loaded < local_bars:
        local_bars = actual_bars_loaded
        msg = f"[FIB] Загружено всего {actual_bars_loaded} баров, уменьшаем local_bars до {local_bars}."
        logging.warning(msg)
        log_messages.append(msg)

    df_local = df.tail(local_bars)
    local_high = df_local["high"].max()
    local_low = df_local["low"].min()
    absolute_high = df["high"].max()
    absolute_low = df["low"].max()
    diff = local_high - local_low
    if diff == 0:
        msg = (
            f"[FIB] high == low, не можем вычислить Фибоначчи для {symbol} {timeframe}."
        )
        logging.error(msg)
        log_messages.append(msg)
        return None

    fib_values = [
        -0.618,
        0.0,
        0.236,
        0.382,
        0.5,
        0.618,
        0.705,
        0.79,
        1.0,
        1.272,
        1.618,
        2.618,
    ]
    fib_levels = {}
    fib_ranges = {}
    trend_lower = trend.lower()
    if trend_lower not in ("up", "down"):
        msg = f"[FIB] Некорректный тренд='{trend}'. Ожидается 'up' или 'down'."
        logging.error(msg)
        log_messages.append(msg)
        return None

    if trend_lower == "up":
        for fib in fib_values:
            lvl_name = f"{fib*100:.1f}%"
            lvl_value = local_high - fib * diff
            fib_levels[lvl_name] = round(lvl_value, 5)
            fib_ranges[lvl_name] = round(lvl_value - local_low, 5)
    else:
        for fib in fib_values:
            lvl_name = f"{fib*100:.1f}%"
            lvl_value = local_low + fib * diff
            fib_levels[lvl_name] = round(lvl_value, 5)
            fib_ranges[lvl_name] = round(local_high - lvl_value, 5)

    msg = (
        f"[FIB] Symbol={symbol}, TF={timeframe}, Trend={trend_lower}, LocalBars={local_bars}, "
        f"High={local_high:.5f}, Low={local_low:.5f}, FibLevels={fib_levels}"
    )
    logging.info(msg)
    log_messages.append(msg)

    tick_info = get_currency_tick(symbol)
    current_price = tick_info["bid"] if tick_info else None

    result = {
        "fib_levels": fib_levels,
        "fib_ranges": fib_ranges,
        "local_high": round(local_high, 5),
        "local_low": round(local_low, 5),
        "absolute_high": round(absolute_high, 5),
        "absolute_low": round(absolute_low, 5),
        "current_price": current_price,
        "start_time": (
            df.index.min().isoformat()
            if hasattr(df.index.min(), "isoformat")
            else str(df.index.min())
        ),
        "end_time": (
            df.index.max().isoformat()
            if hasattr(df.index.max(), "isoformat")
            else str(df.index.max())
        ),
        "trend": trend_lower,
        "bars_used": actual_bars_loaded,
        "local_bars_used": local_bars,
        "log": log_messages,
    }
    return result


def analyze_current_price_with_fibonacci(
    high: float,
    low: float,
    close: float,
    current_price: float,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
) -> Dict[str, Any]:
    """
    Проводит анализ текущей цены относительно уровней Fibonacci Pivot Point и временных зон Фибоначчи.
    """
    fib_pivot_levels = calculate_fibonacci_pivot_points(high, low, close)
    nearest_levels = find_nearest_levels(fib_pivot_levels, current_price)
    time_zones = calculate_fibonacci_time_zones(start_time, end_time)
    return {
        "fib_pivot_levels": fib_pivot_levels,
        "nearest_levels": nearest_levels,
        "time_zones": time_zones,
    }


def calculate_ote(
    symbol: str,
    timeframe: Any,
    trend: str = "up",
    bars: int = 500,
    local_bars: int = 128,
) -> Optional[Dict[str, Any]]:
    """
    Рассчитывает OTE (Optimal Trade Entry) на основе уровней Фибоначчи (61.8% и 79.0%).
    """
    fib_data = calculate_fibonacci_levels(symbol, timeframe, trend, bars, local_bars)
    if not fib_data:
        return None

    fib_levels = fib_data.get("fib_levels", {})
    level_61 = fib_levels.get("61.8%")
    level_79 = fib_levels.get("79.0%")
    if level_61 is None or level_79 is None:
        logging.warning(
            f"[OTE] Не найдены уровни 61.8% и/или 79.0% для {symbol} {timeframe}."
        )
        return fib_data

    price_61, price_79 = min(level_61, level_79), max(level_61, level_79)
    ote_range = abs(price_79 - price_61)

    current_price = fib_data.get("current_price")
    if current_price is None:
        tick_info = get_currency_tick(symbol)
        current_price = tick_info["bid"] if tick_info else 0

    in_ote = price_61 <= current_price <= price_79
    fib_data["ote_levels"] = {
        "61.8%": level_61,
        "79.0%": level_79,
        "range": round(ote_range, 5),
    }
    fib_data["in_ote"] = in_ote
    fib_data["current_price"] = current_price
    return fib_data


def is_price_in_ote(price: float, ote_levels: Dict[str, float]) -> bool:
    """
    Проверяет, находится ли цена в зоне OTE (между 61.8% и 79.0%).
    """
    lvl61 = ote_levels.get("61.8%")
    lvl79 = ote_levels.get("79.0%")
    if lvl61 is None or lvl79 is None:
        return False
    return min(lvl61, lvl79) <= price <= max(lvl61, lvl79)


# ------------------------------ Дополнительные индикаторы ------------------------------


def calculate_cci(
    symbol: str, timeframe: Any, period: int = 20, num_values: int = 3
) -> List[Optional[float]]:
    df = get_rates_dataframe(symbol, timeframe, period + num_values - 1)
    if df is None:
        log_data_error(symbol)
        return [None] * num_values
    cci = talib.CCI(df["high"], df["low"], df["close"], timeperiod=period)
    if cci.empty:
        return [None] * num_values
    return [round(value, 5) for value in cci.iloc[-num_values:].tolist()]


def calculate_atr(
    symbol: str, timeframe: Any, period: int = 14, num_values: int = 3
) -> List[Optional[float]]:
    try:
        df = get_rates_dataframe(symbol, timeframe, period + num_values - 1)
        if df is None or df.empty:
            logging.warning(f"Данные отсутствуют для {symbol} на {timeframe}.")
            return [None] * num_values
        df["high_low"] = df["high"] - df["low"]
        df["high_close"] = abs(df["high"] - df["close"].shift(1))
        df["low_close"] = abs(df["low"] - df["close"].shift(1))
        df["true_range"] = df[["high_low", "high_close", "low_close"]].max(axis=1)
        df["atr"] = df["true_range"].rolling(window=period).mean()
        atr_values = df["atr"].iloc[-num_values:]
        if atr_values.isnull().all():
            return [None] * num_values
        return [round(value, 5) for value in atr_values.tolist()]
    except Exception as e:
        logging.error(f"Ошибка расчёта ATR для {symbol} на {timeframe}: {e}")
        return [None] * num_values


def calculate_macd(
    symbol: str,
    timeframe: Any,
    short_period: int = 12,
    long_period: int = 26,
    signal_period: int = 9,
    data_period: int = 100,
    num_values: int = 3,
) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    df = get_rates_dataframe(
        symbol, timeframe, data_period + long_period + num_values - 1
    )
    if df is None:
        return [None] * num_values, [None] * num_values
    ema_short = df["close"].ewm(span=short_period, adjust=False).mean()
    ema_long = df["close"].ewm(span=long_period, adjust=False).mean()
    macd = ema_short - ema_long
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    return (
        [round(value, 6) for value in macd.iloc[-num_values:].tolist()],
        [round(value, 6) for value in signal.iloc[-num_values:].tolist()],
    )


def calculate_rsi(
    symbol: str, timeframe: Any, period: int = 14, num_values: int = 3
) -> List[Optional[float]]:
    df = get_rates_dataframe(symbol, timeframe, period + num_values - 1)
    if df is None:
        return [None] * num_values
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    if rsi.empty:
        return [None] * num_values
    return [round(value, 5) for value in rsi.iloc[-num_values:].tolist()]


def calculate_bollinger_bands(
    symbol: str,
    timeframe: Any,
    period: int = 20,
    num_std_dev: int = 2,
    data_period: int = 100,
    num_values: int = 3,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    df = get_rates_dataframe(symbol, timeframe, data_period + period + num_values - 1)
    if df is None:
        return [None] * num_values, [None] * num_values, [None] * num_values
    sma = df["close"].rolling(window=period).mean()
    std_dev = df["close"].rolling(window=period).std()
    upper_band = sma + (num_std_dev * std_dev)
    lower_band = sma - (num_std_dev * std_dev)
    return (
        (
            [round(value, 5) for value in sma.iloc[-num_values:].tolist()]
            if not sma.empty
            else [None] * num_values
        ),
        (
            [round(value, 5) for value in upper_band.iloc[-num_values:].tolist()]
            if not upper_band.empty
            else [None] * num_values
        ),
        (
            [round(value, 5) for value in lower_band.iloc[-num_values:].tolist()]
            if not lower_band.empty
            else [None] * num_values
        ),
    )


def check_vwap(
    symbol: str, timeframe: Any, period: int = 21, num_values: int = 3
) -> List[Optional[float]]:
    df = get_rates_dataframe(symbol, timeframe, period + num_values - 1)
    if df is None:
        return [None] * num_values
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_vwap = (typical_price * df["tick_volume"]).cumsum() / df[
        "tick_volume"
    ].cumsum()
    if cumulative_vwap.empty:
        return [None] * num_values
    return [round(value, 5) for value in cumulative_vwap.iloc[-num_values:].tolist()]


def calculate_mfi(
    symbol: str, timeframe: Any, period: int = 14, num_values: int = 3
) -> List[Optional[float]]:
    df = get_rates_dataframe(symbol, timeframe, period + num_values)
    if df is None or df["tick_volume"].isnull().all():
        return [None] * num_values
    mfi_series = talib.MFI(
        df["high"], df["low"], df["close"], df["tick_volume"], timeperiod=period
    )
    if mfi_series.empty:
        return [None] * num_values
    return [round(value, 5) for value in mfi_series.iloc[-num_values:].tolist()]


def calculate_stochastic(
    symbol: str, timeframe: Any, num_values: int = 3
) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100 + num_values)
    if rates is None or len(rates) == 0:
        log_data_error(symbol)
        return [None] * num_values, [None] * num_values
    high_prices = np.array([r["high"] for r in rates])
    low_prices = np.array([r["low"] for r in rates])
    close_prices = np.array([r["close"] for r in rates])
    slowk, slowd = talib.STOCH(
        high_prices,
        low_prices,
        close_prices,
        fastk_period=9,
        slowk_period=7,
        slowk_matype=0,
        slowd_period=3,
        slowd_matype=0,
    )
    if (
        slowk is None
        or slowd is None
        or len(slowk) < num_values
        or len(slowd) < num_values
    ):
        return [None] * num_values, [None] * num_values
    return (
        [round(value, 5) for value in slowk[-num_values:].tolist()],
        [round(value, 5) for value in slowd[-num_values:].tolist()],
    )


def calculate_stochastic_with_divergence(
    symbol: str, timeframe: Any, num_values: int = 3, period: int = 100
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[str]]]:
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period + num_values)
    if rates is None or len(rates) == 0:
        log_data_error(symbol)
        return [None] * num_values, [None] * num_values, [None] * num_values
    high_prices = [r["high"] for r in rates]
    low_prices = [r["low"] for r in rates]
    close_prices = [r["close"] for r in rates]
    slowk, slowd = talib.STOCH(
        np.array(high_prices),
        np.array(low_prices),
        np.array(close_prices),
        fastk_period=9,
        slowk_period=7,
        slowk_matype=0,
        slowd_period=3,
        slowd_matype=0,
    )
    if (
        slowk is None
        or slowd is None
        or len(slowk) < num_values
        or len(slowd) < num_values
    ):
        return [None] * num_values, [None] * num_values, [None] * num_values

    divergences = []
    for i in range(-num_values, 0):
        if i < -1:
            if close_prices[i] < close_prices[i - 1] and slowk[i] > slowk[i - 1]:
                divergences.append("bullish_divergence")
            elif close_prices[i] > close_prices[i - 1] and slowk[i] < slowk[i - 1]:
                divergences.append("bearish_divergence")
            else:
                divergences.append(None)
        else:
            divergences.append(None)
    return (
        [round(value, 5) for value in slowk[-num_values:].tolist()],
        [round(value, 5) for value in slowd[-num_values:].tolist()],
        divergences,
    )


# ------------------------------ Получение OHLC-данных ------------------------------
import MetaTrader5 as mt5
import pandas as pd
import time

TIMEFRAME_MAPPING = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
}


def initialize_mt5():
    """Инициализирует MetaTrader 5"""
    if not mt5.initialize():
        raise Exception("Ошибка инициализации MT5")
    print("✅ MT5 успешно инициализирован")
    print(mt5.terminal_info())  # Посмотреть, где лежит exe и т.д.
    print(mt5.account_info())


def ensure_symbol_is_selected(symbol: str):
    """Проверяет, добавлен ли символ в Market Watch, и активирует его"""
    if not mt5.symbol_select(symbol, True):
        raise Exception(
            f"❌ Символ {symbol} не найден в Market Watch. Добавьте его вручную в MT5."
        )


def fetch_ohlc_data(symbol: str, timeframe: str, num_candles: int):
    """Получает OHLC-данные из MT5"""
    initialize_mt5()

    mt5_timeframe = TIMEFRAME_MAPPING.get(timeframe)
    if mt5_timeframe is None:
        raise ValueError(f"Неверный формат таймфрейма: {timeframe}")

    ensure_symbol_is_selected(symbol)

    print(f"🔍 Получаем {num_candles} свечей для {symbol} ({mt5_timeframe})")

    # Задержка перед получением данных (иногда MT5 не сразу подгружает свечи)
    time.sleep(1)

    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, num_candles)
    if rates is None or len(rates) == 0:
        raise Exception(f"❌ Не удалось получить данные для {symbol} {timeframe}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df


def get_ohlc(symbol: str, timeframe: int, num_values: int) -> pd.DataFrame:
    if not mt5.symbol_select(symbol, True):
        raise Exception(f"Failed to select symbol {symbol}.")
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_values)
    if rates is None:
        raise Exception(f"Failed to fetch OHLC data for {symbol}.")
    rates_frame = pd.DataFrame(rates)
    rates_frame["time"] = pd.to_datetime(rates_frame["time"], unit="s")
    return rates_frame[["time", "open", "high", "low", "close"]]


def get_ohlc_extended(
    symbol: str, timeframe: int, number_of_candles: int, round_digits: int = 5
) -> pd.DataFrame:
    if not mt5.symbol_select(symbol, True):
        raise Exception(f"Не удалось выбрать символ {symbol}")
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, number_of_candles)
    if rates is None:
        raise Exception(f"Не удалось получить данные для символа {symbol}")
    rates_frame = pd.DataFrame(rates)
    rates_frame["time"] = pd.to_datetime(rates_frame["time"], unit="s")
    rates_frame["open"] = rates_frame["open"].round(round_digits)
    rates_frame["high"] = rates_frame["high"].round(round_digits)
    rates_frame["low"] = rates_frame["low"].round(round_digits)
    rates_frame["close"] = rates_frame["close"].round(round_digits)
    return rates_frame[["time", "open", "high", "low", "close"]]


# ------------------------------ Агрегация данных для Plotly ------------------------------


def generate_plotly_data(
    symbol: str, timeframe: str, num_candles: int = 500
) -> Dict[str, Any]:
    """
    Собирает данные для построения графиков Plotly в единый JSON-формат.
    """
    data: Dict[str, Any] = {}
    try:
        # Получаем OHLC-данные
        ohlc_data = fetch_ohlc_data(symbol, timeframe, num_candles)
        data["ohlc"] = ohlc_data

        # Получаем технические индикаторы
        df_rates = get_rates_dataframe(symbol, timeframe, num_candles)
        if df_rates is not None and not df_rates.empty:
            data["moving_average"] = df_to_json(
                pd.DataFrame(
                    {
                        "time": df_rates.index,
                        "moving_average": calculate_moving_average(df_rates).tolist(),
                    }
                )
            )
            data["fvg"] = identify_fvg(df_rates)
            data["cci"] = calculate_cci(symbol, timeframe)
            data["atr"] = calculate_atr(symbol, timeframe)
            macd, macd_signal = calculate_macd(symbol, timeframe)
            data["macd"] = macd
            data["macd_signal"] = macd_signal
            data["rsi"] = calculate_rsi(symbol, timeframe)
            sma, upper_band, lower_band = calculate_bollinger_bands(symbol, timeframe)
            data["bollinger_sma"] = sma
            data["bollinger_upper"] = upper_band
            data["bollinger_lower"] = lower_band
            data["vwap"] = check_vwap(symbol, timeframe)
            data["mfi"] = calculate_mfi(symbol, timeframe)
            sto_k, sto_d = calculate_stochastic(symbol, timeframe)
            data["stochastic_k"] = sto_k
            data["stochastic_d"] = sto_d
            data["market_timing"] = analyze_market_timing()
        else:
            logging.warning(f"Нет данных для {symbol} на {timeframe}")
    except Exception as ex:
        logging.exception(f"Ошибка генерации данных для Plotly: {ex}")
    return data


# ------------------------------ Основной блок ------------------------------


def main() -> None:
    symbol = "EURUSD"  # Пример: финансовый инструмент
    timeframe = "M15"  # Пример: таймфрейм
    num_candles = 500  # Количество загружаемых баров
    data = generate_plotly_data(symbol, timeframe, num_candles)
    output_file = f"{symbol}_{timeframe}_data.json"
    save_json(data, output_file)
    logging.info(f"Данные сохранены в {output_file}")


if __name__ == "__main__":
    main()

### ### ###        ### ###    ###  #######
### ### ####       ### #####  ###  ########
### ### #####      ### ##########  ###   ###
### ### #####      ### ### ######  ###   ###
### ### ####       ### ###   ####  ########
### ### ###        ### ###    ###  #######


def get_indicators_data(symbol: str, timeframe: str, num_candles: int):
    """
    Собирает данные всех индикаторов в один JSON-объект с возможностью выбора символа и таймфрейма.
    """
    try:
        ohlc_data = fetch_ohlc_data(symbol, timeframe, num_candles)
        if ohlc_data is None or ohlc_data.empty:
            return {"error": f"Нет данных для {symbol} {timeframe}"}

        rates_df = get_rates_dataframe(symbol, timeframe, num_candles)
        if rates_df is None or rates_df.empty:
            return {"error": f"Ошибка получения данных для {symbol} {timeframe}"}

        data = {
            "ohlc": ohlc_data.to_dict(orient="records"),
            "moving_average": calculate_moving_average(rates_df).tolist(),
            "fvg": identify_fvg(rates_df),
            "cci": calculate_cci(symbol, timeframe),
            "atr": calculate_atr(symbol, timeframe),
            "macd": calculate_macd(symbol, timeframe),
            "rsi": calculate_rsi(symbol, timeframe),
            "bollinger_bands": calculate_bollinger_bands(symbol, timeframe),
            "vwap": check_vwap(symbol, timeframe),
            "mfi": calculate_mfi(symbol, timeframe),
            "stochastic": calculate_stochastic(symbol, timeframe),
            "market_timing": analyze_market_timing(),
        }
        return data

    except Exception as e:
        return {"error": str(e)}

def get_indicators_data_history(symbol, timeframe, count=20):
    try:
        ohlc_data = fetch_ohlc_data(symbol, timeframe, count)
        if not ohlc_data:
            return {"error": f"Нет данных по {symbol} на {timeframe}"}

        rates_df = get_rates_dataframe(symbol, timeframe, count)
        if rates_df.empty:
            return {"error": f"Пустой DataFrame для {symbol} {timeframe}"}

        indicators = get_indicators_data(symbol, timeframe, num_candles=count)
        indicators["ohlc"] = ohlc_data  # Подставляем свечи
        return indicators

    except Exception as e:
        logging.error(f"Ошибка в get_indicators_data_history: {e}")
        return {"error": str(e)}
