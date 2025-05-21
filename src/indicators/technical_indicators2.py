import datetime
import logging
import numpy as np
import pandas as pd
import talib
import MetaTrader5 as mt5
from src.utils.mt5_utils import (
    get_ohlc_extended,
    initialize_mt5,
    shutdown_mt5,
    get_account_info,
    get_currency_tick,
    close_all_positions,
    close_positions_in_profit,
    close_positions_in_loss,
    close_positions_by_symbol,
    open_position,
    get_rates_dataframe,
)
from logs.logi import (
    log_market_structure,
    log_fibonacci_levels,
    log_fvg_zones,
    log_ict_result,
)

import logging
import datetime
from typing import Optional, List, Dict, Any

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def calculate_moving_average(data, period=14):
    """Calculate Moving Average."""
    if len(data) < period:
        return pd.Series([None] * len(data))  # Недостаточно данных для расчета
    return data["close"].rolling(window=period).mean()


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


def identify_fvg(df, lookback=300, tolerance=0.01, min_gap_candles=2):
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
            fvg_zone = {
                "start": df.index[i],
                "end": df.index[i + min_gap_candles],
                "high": high_prev,
                "low": low_next,
            }
            fvg_zones.append(fvg_zone)
            logging.info(
                f"Найдена FVG-зона: start={df.index[i]}, end={df.index[i+min_gap_candles]}, high={high_prev}, low={low_next}"
            )

    if not fvg_zones:
        logging.info("FVG-Зоны: Нет данных.")

    return fvg_zones if fvg_zones else "Нет данных"


def calculate_pivot_points(
    symbol: str, timeframe, num_values: int = 128
) -> List[Dict[str, Any]]:
    """
    Рассчитывает классические Pivot Points (Pivot, S1, S2, S3, R1, R2, R3).

    Args:
        symbol (str): Финансовый инструмент (например, 'EURUSD').
        timeframe: Таймфрейм (например, 'M5' или mt5.TIMEFRAME_M5).
        num_values (int): Количество баров (свечей), по которым рассчитываем.

    Returns:
        List[Dict[str, Any]]: Список словарей, где каждый словарь имеет поля:
            period (int),
            pivot (float),
            pp_resistance (List[float]),
            pp_support (List[float]).
        Пустой список, если нет данных.
    """
    df = get_rates_dataframe(symbol, timeframe, num_values + 1)
    if df is None or df.empty:
        logging.warning(f"[Pivot] Нет данных для {symbol} на {timeframe}")
        return []

    results = []

    # Идём от последних баров к более старым
    # Для каждого бара (i) рассчитываем собственные Pivots
    for i in range(num_values):
        # - (i+2) потому что 0 => последний бар, 1 => предпоследний и т.д.
        #   +1 нужно, т.к. num_values + 1 загрузили
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
    Рассчитывает уровни Fibonacci Pivot Point и группирует Resistance и Support.

    Args:
        high (float): Максимум цены за период.
        low (float): Минимум цены за период.
        close (float): Цена закрытия периода.

    Returns:
        Dict[str, Any]: Словарь с уровнями Pivot, Resistance и Support.
    """
    pivot = (high + low + close) / 3.0
    diff = high - low
    fib_levels = {
        "Pivot": pivot,
        "Resistance": [
            pivot + diff * 0.382,
            pivot + diff * 0.618,
            pivot + diff * 1.000,
        ],
        "Support": [pivot - diff * 0.382, pivot - diff * 0.618, pivot - diff * 1.000],
    }
    return fib_levels


def find_nearest_levels(
    fib_levels: Dict[str, float], current_price: float
) -> Dict[str, Optional[float]]:
    """
    Определяет ближайшие уровни поддержки и сопротивления относительно текущей цены.

    Args:
        fib_levels (dict): Словарь уровней (уровень: цена).
        current_price (float): Текущая цена.

    Returns:
        dict: Ближайший уровень поддержки ('nearest_support') и сопротивления ('nearest_resistance').
    """
    # Фильтруем только числовые значения
    supports = {
        level: price
        for level, price in fib_levels.items()
        if isinstance(price, (int, float)) and price < current_price
    }
    resistances = {
        level: price
        for level, price in fib_levels.items()
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
) -> Dict[str, datetime.datetime]:
    """
    Рассчитывает временные зоны Фибоначчи между двумя временными точками.

    Args:
        start_time (datetime.datetime): Начальное время.
        end_time (datetime.datetime): Конечное время.
        num_zones (int): Сколько зон (по умолчанию 12).

    Returns:
        dict: Названные временные зоны, ключ = "Zone i (xx.x%)",
              значение = datetime.datetime (конкретный момент времени).
    """
    duration = (end_time - start_time).total_seconds()
    fib_ratios = [0.236, 0.382, 0.5, 0.618, 1.0, 1.618, 2.618, 4.236]  # можно расширить

    time_zones = {}
    # Не превышаем num_zones, если fib_ratios короче
    for i, ratio in enumerate(fib_ratios[:num_zones]):
        zone_key = f"Zone {i+1} ({ratio*100:.1f}%)"
        zone_time = start_time + datetime.timedelta(seconds=ratio * duration)
        time_zones[zone_key] = zone_time

    return time_zones


def calculate_fibonacci_levels(
    symbol: str, timeframe, trend: str = "up", bars: int = 500, local_bars: int = 128
) -> Optional[Dict[str, Any]]:
    """
    Рассчитывает уровни Фибоначчи (0%, 23.6%, 38.2%, 50%, 61.8%, 70.5%, 79%, 100%, 127.2%, 161.8%, 261.8%)
    на основе локальных high/low за последние `local_bars` свечей.

    Args:
        symbol (str): Финансовый инструмент (e.g., 'EURUSD').
        timeframe: Таймфрейм (e.g., 'M5', mt5.TIMEFRAME_M5).
        trend (str): 'up' или 'down', определяет направление вычисления уровней.
        bars (int): Сколько баров грузим (по умолчанию 500).
        local_bars (int): Кол-во баров для поиска локального максимума/минимума (по умолчанию 128).

    Returns:
        dict: Содержит "fib_levels", "fib_ranges", "local_high", "local_low",
              "absolute_high", "absolute_low", "current_price", "start_time", "end_time",
              "trend", "bars_used", "local_bars_used", "log".
        Или None, если данные не получены или не вычислены.
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
        msg = (
            f"[FIB] Предупреждение: загружено всего {actual_bars_loaded} баров, "
            f"уменьшаем local_bars до {local_bars}."
        )
        logging.warning(msg)
        log_messages.append(msg)

    df_local = df.tail(local_bars)
    local_high_price = df_local["high"].max()
    local_low_price = df_local["low"].min()

    absolute_high_price = df["high"].max()
    absolute_low_price = df["low"].min()

    diff = local_high_price - local_low_price
    if diff == 0:
        msg = f"[FIB] high == low => не можем вычислить Фибоначчи для {symbol} {timeframe}."
        logging.error(msg)
        log_messages.append(msg)
        return None

    # Список уровней (включая расширения)
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
        msg = f"[FIB] Некорректный тренд='{trend}'. Ожидается 'up'/'down'."
        logging.error(msg)
        log_messages.append(msg)
        return None

    # Формируем уровни и диапазоны
    if trend_lower == "up":
        for fib in fib_values:
            lvl_name = f"{fib*100:.1f}%"
            lvl_value = local_high_price - fib * diff
            fib_levels[lvl_name] = round(lvl_value, 5)
            fib_ranges[lvl_name] = round(lvl_value - local_low_price, 5)
    else:  # 'down'
        for fib in fib_values:
            lvl_name = f"{fib*100:.1f}%"
            lvl_value = local_low_price + fib * diff
            fib_levels[lvl_name] = round(lvl_value, 5)
            fib_ranges[lvl_name] = round(local_high_price - lvl_value, 5)

    msg = (
        f"[FIB] Symbol={symbol}, TF={timeframe}, Trend={trend_lower}, "
        f"LocalBars={local_bars}, High={local_high_price:.5f}, Low={local_low_price:.5f}, "
        f"FibLevels={fib_levels}"
    )
    logging.info(msg)
    log_messages.append(msg)

    # Попробуем взять текущую цену (Bid) — если требуется
    tick_info = get_currency_tick(symbol)
    current_price = tick_info["bid"] if tick_info else None

    result = {
        "fib_levels": fib_levels,
        "fib_ranges": fib_ranges,
        "local_high": round(local_high_price, 5),
        "local_low": round(local_low_price, 5),
        "absolute_high": round(absolute_high_price, 5),
        "absolute_low": round(absolute_low_price, 5),
        "current_price": current_price,
        "start_time": df.index.min(),  # если DataFrame индекс = datetime
        "end_time": df.index.max(),
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

    Args:
        high (float): Максимум за период.
        low (float): Минимум за период.
        close (float): Цена закрытия периода.
        current_price (float): Текущая (актуальная) цена.
        start_time (datetime.datetime): Начало периода.
        end_time (datetime.datetime): Конец периода.

    Returns:
        dict: Результаты анализа, содержащие ключи:
            'fib_pivot_levels': dict (Fibonacci Pivot Levels),
            'nearest_levels': dict (ближайшие S/R),
            'time_zones': dict (Fibonacci Time Zones).
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
    symbol: str, timeframe, trend: str = "up", bars: int = 500, local_bars: int = 128
) -> Optional[Dict[str, Any]]:
    """
    Рассчитывает OTE (Optimal Trade Entry) на основе уровней Фибоначчи (61.8% и 79%).
    Предполагается, что "OTE" — зона между 61.8% и 79%.

    Args:
        symbol (str): Тикер (e.g., 'EURUSD').
        timeframe: Таймфрейм (e.g., 'M5', mt5.TIMEFRAME_M5').
        trend (str): Направление ('up' или 'down').
        bars (int): Сколько баров для загрузки.
        local_bars (int): Сколько баров учитывать при поиске экстремумов.

    Returns:
        dict or None:
            {
                "ote_levels": {"61.8%", "79.0%", "range"},
                "fib_levels": ...,
                "fib_ranges": ...,
                "local_high": ...,
                "local_low": ...,
                "absolute_high": ...,
                "absolute_low": ...,
                "current_price": ...,
                "in_ote": bool,
                ...
            }
            или None, если нельзя вычислить Фибо.
    """
    fib_data = calculate_fibonacci_levels(symbol, timeframe, trend, bars, local_bars)
    if not fib_data:
        return None

    fib_levels = fib_data.get("fib_levels", {})
    # Проверяем ключи "61.8%" и "79.0%", приводим их к тому же формату
    level_61 = fib_levels.get("61.8%")
    level_79 = fib_levels.get("79.0%")
    if level_61 is None or level_79 is None:
        logging.warning(
            f"[OTE] Не найдены уровни 61.8% и/или 79.0% для {symbol} {timeframe}."
        )
        return fib_data  # Возвращаем то, что есть

    price_61 = min(level_61, level_79)  # Чтобы в 'up' / 'down' не путаться
    price_79 = max(level_61, level_79)
    ote_range = abs(price_79 - price_61)

    # Текущая цена (если уже есть в fib_data)
    current_price = fib_data.get("current_price")
    if current_price is None:
        # Пытаемся получить
        tick_info = get_currency_tick(symbol)
        if tick_info:
            current_price = tick_info["bid"]
        else:
            current_price = 0

    in_ote = price_61 <= current_price <= price_79

    # Формируем возвращаемый словарь
    fib_data["ote_levels"] = {
        "61.8%": level_61,
        "79.0%": level_79,
        "range": round(ote_range, 5),
    }
    fib_data["in_ote"] = in_ote
    fib_data["current_price"] = current_price  # Обновляем/заполняем, если не было

    return fib_data


def is_price_in_ote(price: float, ote_levels: Dict[str, float]) -> bool:
    """
    Проверяет, находится ли 'price' в зоне OTE (между 61.8% и 79.0%).

    Args:
        price (float): Текущая цена.
        ote_levels (dict): Словарь с ключами "61.8%" и "79.0%".

    Returns:
        bool: True, если в OTE, False — если нет.
    """
    lvl61 = ote_levels.get("61.8%")
    lvl79 = ote_levels.get("79.0%")
    if lvl61 is None or lvl79 is None:
        return False
    low_level = min(lvl61, lvl79)
    high_level = max(lvl61, lvl79)
    return low_level <= price <= high_level


# Рассчёт индикаторов (все функции аналогичны, возвращают списки значений или None)
def calculate_cci(symbol, timeframe, period=20, num_values=3):
    df = get_rates_dataframe(symbol, timeframe, period + num_values - 1)
    if df is None:
        log_data_error(symbol)
        return [None] * num_values
    cci = talib.CCI(df["high"], df["low"], df["close"], timeperiod=period)
    return (
        [round(value, 5) for value in cci.iloc[-num_values:].tolist()]
        if not cci.empty
        else [None] * num_values
    )


def calculate_atr(symbol, timeframe, period=14, num_values=3):
    """
    Расчёт ATR (Average True Range) для указанного символа и таймфрейма.

    :param symbol: Символ финансового инструмента (например, EURUSD).
    :param timeframe: Таймфрейм (например, mt5.TIMEFRAME_H1).
    :param period: Период для расчёта ATR (по умолчанию 14).
    :param num_values: Количество последних значений ATR для возврата.
    :return: Список из num_values значений ATR или список [None] при ошибке.
    """
    try:
        # Получаем данные с запасом
        df = get_rates_dataframe(symbol, timeframe, period + num_values - 1)
        if df is None or df.empty:
            logging.warning(f"Данные отсутствуют для {symbol} на {timeframe}.")
            return [None] * num_values

        # Вычисляем True Range
        df["high_low"] = df["high"] - df["low"]
        df["high_close"] = abs(df["high"] - df["close"].shift(1))
        df["low_close"] = abs(df["low"] - df["close"].shift(1))
        df["true_range"] = df[["high_low", "high_close", "low_close"]].max(axis=1)

        # Вычисляем ATR как скользящее среднее True Range
        df["atr"] = df["true_range"].rolling(window=period).mean()

        # Возвращаем последние num_values значений ATR
        atr_values = df["atr"].iloc[-num_values:]
        return (
            [round(value, 5) for value in atr_values.tolist()]
            if not atr_values.isnull().all()
            else [None] * num_values
        )
    except Exception as e:
        logging.error(f"Ошибка расчёта ATR для {symbol} на {timeframe}: {e}")
        return [None] * num_values


def calculate_macd(
    symbol,
    timeframe,
    short_period=12,
    long_period=26,
    signal_period=9,
    data_period=100,
    num_values=3,
):
    df = get_rates_dataframe(
        symbol, timeframe, data_period + long_period + num_values - 1
    )
    if df is None:
        return [None] * num_values, [None] * num_values

    ema_short = df["close"].ewm(span=short_period, adjust=False).mean()
    ema_long = df["close"].ewm(span=long_period, adjust=False).mean()
    macd = ema_short - ema_long
    signal = macd.ewm(span=signal_period, adjust=False).mean()

    return [round(value, 6) for value in macd.iloc[-num_values:].tolist()], [
        round(value, 6) for value in signal.iloc[-num_values:].tolist()
    ]


def calculate_rsi(symbol, timeframe, period=14, num_values=3):
    df = get_rates_dataframe(symbol, timeframe, period + num_values - 1)
    if df is None:
        return [None] * num_values

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return (
        [round(value, 5) for value in rsi.iloc[-num_values:].tolist()]
        if not rsi.empty
        else [None] * num_values
    )


def calculate_bollinger_bands(
    symbol, timeframe, period=20, num_std_dev=2, data_period=100, num_values=3
):
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


def check_vwap(symbol, timeframe, period=21, num_values=3):
    df = get_rates_dataframe(symbol, timeframe, period + num_values - 1)
    if df is None:
        return [None] * num_values

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_vwap = (typical_price * df["tick_volume"]).cumsum() / df[
        "tick_volume"
    ].cumsum()

    return (
        [round(value, 5) for value in cumulative_vwap.iloc[-num_values:].tolist()]
        if not cumulative_vwap.empty
        else [None] * num_values
    )


def calculate_mfi(symbol, timeframe, period=14, num_values=3):
    df = get_rates_dataframe(symbol, timeframe, period + num_values)
    if df is None or df["tick_volume"].isnull().all():
        return [None] * num_values

    mfi_series = talib.MFI(
        df["high"], df["low"], df["close"], df["tick_volume"], timeperiod=period
    )
    return (
        [round(value, 5) for value in mfi_series.iloc[-num_values:].tolist()]
        if not mfi_series.empty
        else [None] * num_values
    )


def calculate_stochastic(symbol, timeframe, num_values=3):
    # Пример адаптации Stochastic, чтобы вернуть num_values значений
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100 + num_values)
    if rates is None or len(rates) == 0:
        log_data_error(symbol)
        return [None] * num_values, [None] * num_values

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
        return [None] * num_values, [None] * num_values

    return (
        [round(value, 5) for value in slowk[-num_values:].tolist()],
        [round(value, 5) for value in slowd[-num_values:].tolist()],
    )


def calculate_stochastic_with_divergence(symbol, timeframe, num_values=3, period=100):
    """
    Расчёт Стохастика с определением дивергенции/конвергенции.
    """
    # Получаем данные с запасом для анализа
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period + num_values)
    if rates is None or len(rates) == 0:
        log_data_error(symbol)
        return [None] * num_values, [None] * num_values, [None] * num_values

    high_prices = [r["high"] for r in rates]
    low_prices = [r["low"] for r in rates]
    close_prices = [r["close"] for r in rates]

    # Расчёт Стохастика
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

    # Проверка корректности данных
    if (
        slowk is None
        or slowd is None
        or len(slowk) < num_values
        or len(slowd) < num_values
    ):
        return [None] * num_values, [None] * num_values, [None] * num_values

    # Определяем дивергенцию/конвергенцию
    divergences = []
    for i in range(-num_values, 0):  # Анализ последних num_values значений
        if i < -1:  # Проверяем только если есть предыдущие значения
            # Дивергенция бычья: Цена падает, slowk растёт
            if close_prices[i] < close_prices[i - 1] and slowk[i] > slowk[i - 1]:
                divergences.append("bullish_divergence")
            # Дивергенция медвежья: Цена растёт, slowk падает
            elif close_prices[i] > close_prices[i - 1] and slowk[i] < slowk[i - 1]:
                divergences.append("bearish_divergence")
            else:
                divergences.append(None)
        else:
            divergences.append(None)  # Недостаточно данных для анализа

    # Возвращаем значения
    return (
        [round(value, 5) for value in slowk[-num_values:].tolist()],
        [round(value, 5) for value in slowd[-num_values:].tolist()],
        divergences,
    )


from src.utils.mt5_utils import get_ohlc


def get_indicators_data(
    symbol, timeframe, trend="up", num_values=128, use_extended=True
):
    indicators = {}
    logging.info(
        f"Получение данных индикаторов для {symbol} на таймфрейме {timeframe}. Количество значений: {num_values}"
    )

    # Получение OHLC данных
    try:
        ohlc_data = get_ohlc(symbol, timeframe, num_values)
        indicators["ohlc"] = ohlc_data.to_dict(
            orient="records"
        )  # Добавляем OHLC данные
    except Exception as e:
        logging.exception(f"Ошибка OHLC: {e}")
        indicators["ohlc"] = []

    # Получение OHLC get_ohlc_extended данных
    try:
        if use_extended:
            ohlc_data = get_ohlc_extended(symbol, timeframe, num_values)
        else:
            ohlc_data = get_ohlc(symbol, timeframe, num_values)

        indicators["ohlc"] = ohlc_data.to_dict(
            orient="records"
        )  # Добавляем OHLC данные
    except Exception as e:

        logging.exception(f"Ошибка OHLC: {e}")
        indicators["ohlc"] = []

    # MACD
    try:
        macd_values, signal_values = calculate_macd(
            symbol, timeframe, num_values=num_values
        )
        indicators["macd"] = macd_values
        indicators["signal"] = signal_values
    except Exception as e:
        logging.exception(f"Ошибка MACD: {e}")
        indicators["macd"] = [None] * num_values
        indicators["signal"] = [None] * num_values

    # Bollinger Bands
    try:
        sma_values, upper_band_values, lower_band_values = calculate_bollinger_bands(
            symbol, timeframe, num_values=num_values
        )
        indicators["sma"] = sma_values
        indicators["upper_band"] = upper_band_values
        indicators["lower_band"] = lower_band_values
    except Exception as e:
        logging.exception(f"Ошибка Bollinger: {e}")
        indicators["sma"] = [None] * num_values
        indicators["upper_band"] = [None] * num_values
        indicators["lower_band"] = [None] * num_values

    # RSI
    try:
        rsi_values = calculate_rsi(symbol, timeframe, num_values=num_values)
        indicators["rsi"] = rsi_values
    except Exception as e:
        logging.exception(f"Ошибка RSI: {e}")
        indicators["rsi"] = [None] * num_values

    # ATR
    try:
        atr_values = calculate_atr(symbol, timeframe, num_values=num_values)
        if all(value is None for value in atr_values):
            logging.warning(
                f"ATR для {symbol} на {timeframe} вернул только None значения."
            )
        else:
            logging.info(f"ATR для {symbol} на {timeframe}: {atr_values}")
        indicators["atr"] = atr_values
    except Exception as e:
        logging.exception(f"Ошибка ATR для {symbol} на {timeframe}: {e}")
        indicators["atr"] = [None] * num_values

    # VWAP
    try:
        vwap_values = check_vwap(symbol, timeframe, num_values=num_values)
        indicators["vwap"] = vwap_values
    except Exception as e:
        logging.exception(f"Ошибка VWAP: {e}")
        indicators["vwap"] = [None] * num_values

    # CCI
    try:
        cci_values = calculate_cci(symbol, timeframe, num_values=num_values)
        indicators["cci"] = cci_values
    except Exception as e:
        logging.exception(f"Ошибка CCI: {e}")
        indicators["cci"] = [None] * num_values

    # MFI
    try:
        mfi_values = calculate_mfi(symbol, timeframe, num_values=num_values)
        indicators["mfi"] = mfi_values
    except Exception as e:
        logging.exception(f"Ошибка MFI: {e}")
        indicators["mfi"] = [None] * num_values

    # Получение данных Стохастика и дивергенции
    try:
        stochastic_k, stochastic_d, divergences = calculate_stochastic_with_divergence(
            symbol, timeframe, num_values
        )
        indicators["stochastic_k"] = stochastic_k
        indicators["stochastic_d"] = stochastic_d
        indicators["stochastic_divergence"] = divergences
    except Exception as e:
        logging.exception(f"Ошибка расчёта Стохастика: {e}")
        indicators["stochastic_k"] = []
        indicators["stochastic_d"] = []
        indicators["stochastic_divergence"] = []

    # Pivot Points
    try:
        pivot_points = calculate_pivot_points(symbol, timeframe, num_values=num_values)
        indicators["pivot"] = [item["pivot"] for item in pivot_points]
        indicators["pp_resistance"] = [
            item["pp_resistance"] for item in pivot_points
        ]  # Список уровней сопротивления
        indicators["pp_support"] = [
            item["pp_support"] for item in pivot_points
        ]  # Список уровней поддержки
    except Exception as e:
        logging.exception(f"Ошибка Pivot Points: {e}")
        indicators["pivot"] = [None] * num_values
        indicators["pp_resistance"] = [[None] * 3 for _ in range(num_values)]
        indicators["pp_support"] = [[None] * 3 for _ in range(num_values)]
    logging.info(f"Итоговые данные индикаторов: {indicators}")
    logging.info(f"OHLC данные для {timeframe}: {indicators['ohlc']}")

    return indicators


def log_data_error(symbol):
    logging.error(f"Ошибка получения данных для {symbol}.")


import logging


def test_indicators(symbol, timeframe, num_values=100):
    from src.utils.mt5_utils import initialize_mt5, shutdown_mt5, get_rates_dataframe
    from src.indicators.technical_indicators import (
        calculate_macd,
        calculate_bollinger_bands,
        calculate_rsi,
        calculate_atr,
        calculate_stochastic_with_divergence,
        calculate_pivot_points,
    )

    initialize_mt5()

    try:
        # Проверяем получение данных OHLC
        ohlc_data = get_rates_dataframe(symbol, timeframe, num_values)
        if not ohlc_data or ohlc_data.empty:
            logging.error(f"OHLC data is empty for {symbol} on {timeframe}.")
            return

        print("OHLC data:", ohlc_data.tail())

        # Тестируем каждый индикатор
        try:
            macd, signal = calculate_macd(symbol, timeframe, num_values)
            print("MACD:", macd[-5:], "Signal:", signal[-5:])
        except Exception as e:
            logging.error(f"Error calculating MACD: {e}")

        try:
            sma, upper, lower = calculate_bollinger_bands(symbol, timeframe, num_values)
            print(
                "Bollinger Bands - SMA:",
                sma[-5:],
                "Upper:",
                upper[-5:],
                "Lower:",
                lower[-5:],
            )
        except Exception as e:
            logging.error(f"Error calculating Bollinger Bands: {e}")

        try:
            rsi = calculate_rsi(symbol, timeframe, num_values)
            print("RSI:", rsi[-5:])
        except Exception as e:
            logging.error(f"Error calculating RSI: {e}")

        try:
            atr = calculate_atr(symbol, timeframe, num_values)
            print("ATR:", atr[-5:])
        except Exception as e:
            logging.error(f"Error calculating ATR: {e}")

        try:
            stochastic_k, stochastic_d, divergences = (
                calculate_stochastic_with_divergence(symbol, timeframe, num_values)
            )
            print(
                "Stochastic K:", stochastic_k[-5:], "Stochastic D:", stochastic_d[-5:]
            )
        except Exception as e:
            logging.error(f"Error calculating Stochastic: {e}")

        try:
            pivots = calculate_pivot_points(symbol, timeframe, num_values)
            print("Pivot Points:", pivots[-1])
        except Exception as e:
            logging.error(f"Error calculating Pivot Points: {e}")

    finally:
        shutdown_mt5()


# Запуск теста
test_indicators("EURUSD", "M15", num_values=100)
