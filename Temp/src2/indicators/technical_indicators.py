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


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


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


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Новая функция для расчета Pivot Points через pandas
def calculate_pivot_points(symbol, timeframe, num_values=128):
    """
    Рассчитывает Pivot Point и уровни S1, S2, S3, R1, R2, R3 для отображения в веб-интерфейсе.
    """
    df = get_rates_dataframe(symbol, timeframe, num_values + 1)
    if df is None or df.empty:
        return []

    results = []

    for i in range(num_values):
        high = df["high"].iloc[-(i + 2)]
        low = df["low"].iloc[-(i + 2)]
        close = df["close"].iloc[-(i + 2)]

        pivot = (high + low + close) / 3
        r1, r2, r3 = (2 * pivot) - low, pivot + (high - low), high + 2 * (pivot - low)
        s1, s2, s3 = (2 * pivot) - high, pivot - (high - low), low - 2 * (high - pivot)

        results.append(
            {
                "period": i + 1,
                "pivot": round(pivot, 5),
                "pp_resistance": [round(r1, 5), round(r2, 5), round(r3, 5)],
                "pp_support": [round(s1, 5), round(s2, 5), round(s3, 5)],
            }
        )

    return results


# def calculate_fibonacci_levels(symbol, timeframe, trend="up", bars=500):
#     df = get_rates_dataframe(symbol, timeframe, bars)
#     if df is None or df.empty:
#         log_data_error(symbol)
#         return None

#     high_price = df["high"].max()
#     low_price = df["low"].min()
#     diff = high_price - low_price

#     if diff == 0:
#         logging.error(f"Недостаточный диапазон для Фибоначчи {symbol}")
#         return None

#     fib_levels = {}
#     if trend.lower() == "up":
#         fib_levels = {
#             "0.0%": round(high_price, 5),
#             "23.6%": round(high_price - 0.236 * diff, 5),
#             "38.2%": round(high_price - 0.382 * diff, 5),
#             "50.0%": round(high_price - 0.500 * diff, 5),
#             "61.8%": round(high_price - 0.618 * diff, 5),
#             "70.5%": round(high_price - 0.705 * diff, 5),
#             "79.0%": round(high_price - 0.790 * diff, 5),
#             "100.0%": round(low_price, 5),
#         }
#     elif trend.lower() == "down":
#         fib_levels = {
#             "0.0%": round(low_price, 5),
#             "23.6%": round(low_price + 0.236 * diff, 5),
#             "38.2%": round(low_price + 0.382 * diff, 5),
#             "50.0%": round(low_price + 0.500 * diff, 5),
#             "61.8%": round(low_price + 0.618 * diff, 5),
#             "70.5%": round(low_price + 0.705 * diff, 5),
#             "79.0%": round(low_price + 0.790 * diff, 5),
#             "100.0%": round(high_price, 5),
#         }
#     else:
#         logging.error(f"Некорректный тренд: {trend}")
#         return None

#     logging.info(f"Fibonacci levels for {symbol} {timeframe}: {fib_levels}")

#     return fib_levels

import logging


def calculate_ote(symbol, timeframe, trend="up", bars=500, local_bars=128):
    """
    Вычисление оптимальных точек входа (OTE) на основе уровней Фибоначчи.
    """
    fib_data = calculate_fibonacci_levels(symbol, timeframe, trend, bars, local_bars)
    if fib_data is None:
        logging.error(
            f"[OTE] Ошибка расчёта уровней Фибоначчи для {symbol}, {timeframe}"
        )
        return None

    # Найти уровень OTE (например, между 61.8% и 79%)
    ote_levels = {
        "61.8%": fib_data["fib_levels"].get("61.8%"),
        "79.0%": fib_data["fib_levels"].get("79.0%"),
    }

    return {
        "ote_levels": ote_levels,
        "local_high": fib_data["local_high"],
        "local_low": fib_data["local_low"],
        "absolute_high": fib_data["absolute_high"],
        "absolute_low": fib_data["absolute_low"],
    }


def is_price_in_ote(price, ote_levels):
    """
    Проверяет, находится ли цена в зоне OTE.
    """
    if ote_levels["61.8%"] <= price <= ote_levels["79.0%"]:
        return True
    return False


def calculate_fibonacci_levels(symbol, timeframe, trend="up", bars=500, local_bars=128):
    """
    Рассчитывает уровни Фибоначчи (0%, 23.6%, 38.2%, 50%, 61.8%, 70.5%, 79%, 100%, 127.2%, 161.8%, 261.8%)
    на основе локальных максимума и минимума за последние `local_bars` свечей.

    :param symbol: Тикер (например, 'EURUSD').
    :param timeframe: Таймфрейм (например, mt5.TIMEFRAME_H1).
    :param trend: 'up' или 'down', определяет направление расчёта уровней.
    :param bars: Общее количество баров для загрузки из get_rates_dataframe (по умолчанию 500).
    :param local_bars: Количество последних баров, среди которых ищется локальный high/low.
    :return: Словарь c ключами:
        {
          "fib_levels": {...},         # Словарь уровней Фибоначчи
          "local_high": float,        # Найденный локальный максимум
          "local_low": float,         # Найденный локальный минимум
          "trend": str,               # 'up' или 'down'
          "bars_used": int,           # Сколько всего баров было загружено
          "local_bars_used": int,     # Сколько баров пошло на поиск экстремумов
          "log": list[str],           # Лог-сообщения для веб-интерфейса
        }
        или None, если произошла ошибка.
    """
    # Шаг 1. Загрузить нужное количество баров
    df = get_rates_dataframe(symbol, timeframe, bars)
    log_messages = []  # Собираем логи здесь (для веб-интерфейса)

    if df is None or df.empty:
        msg = f"[FIB] Данные для {symbol} {timeframe} отсутствуют или пусты."
        logging.error(msg)
        log_messages.append(msg)
        return None

    actual_bars_loaded = len(df)
    if actual_bars_loaded < local_bars:
        local_bars = actual_bars_loaded
        msg = (
            f"[FIB] Предупреждение: в DataFrame всего {actual_bars_loaded} баров, "
            f"уменьшаем local_bars до {local_bars}."
        )
        logging.warning(msg)
        log_messages.append(msg)

    # Шаг 2. Получить "хвост" для поиска локальных экстремумов
    df_local = df.tail(local_bars)  # последние local_bars строк
    local_high_price = df_local["high"].max()
    local_low_price = df_local["low"].min()

    # Абсолютные экстремумы
    absolute_high_price = df["high"].max()
    absolute_low_price = df["low"].min()

    diff = local_high_price - local_low_price
    if diff == 0:
        msg = f"[FIB] Недостаточный диапазон (high == low) для Фибоначчи {symbol} {timeframe}."
        logging.error(msg)
        log_messages.append(msg)
        return None

    # Шаг 3. Формирование набора уровней Фибоначчи (включая расширенные уровни до 261.8%)
    fib_values = [
        -0.618,
        # -0.382,
        # -0.236,
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

    trend_lower = trend.lower()

    if trend_lower not in ("up", "down"):
        msg = f"[FIB] Некорректный тренд: {trend}. Ожидается 'up' или 'down'."
        logging.error(msg)
        log_messages.append(msg)
        return None

    fib_levels = {}
    fib_ranges = {}  # Новый словарь для диапазонов уровней

    # Для наглядности разобьём логику
    if trend_lower == "up":
        # "up" — считаем, что high_price выше low_price
        for fib in fib_values:
            level_name = f"{fib*100:.1f}%"
            # Уровень: high - fib * (high - low)
            fib_level_value = local_high_price - fib * diff
            fib_levels[level_name] = round(fib_level_value, 5)

            # Диапазон: разница между уровнем и low
            fib_range_value = fib_level_value - local_low_price
            fib_ranges[level_name] = round(fib_range_value, 5)

    else:  # trend_lower == "down"
        # "down" — считаем, что low_price < high_price
        for fib in fib_values:
            level_name = f"{fib*100:.1f}%"
            # Уровень: low + fib * (high - low)
            fib_level_value = local_low_price + fib * diff
            fib_levels[level_name] = round(fib_level_value, 5)

            # Диапазон: разница между high и уровнем
            fib_range_value = local_high_price - fib_level_value
            fib_ranges[level_name] = round(fib_range_value, 5)

    # Шаг 4. Логируем результаты
    msg = (
        f"[FIB] Symbol={symbol}, TF={timeframe}, Trend={trend_lower}, "
        f"LocalBars={local_bars}, High={local_high_price:.5f}, "
        f"Low={local_low_price:.5f}, FibLevels={fib_levels}, FibRanges={fib_ranges}"
    )
    logging.info(msg)
    log_messages.append(msg)

    # Шаг 5. Собираем итоговый словарь
    result = {
        "fib_levels": fib_levels,
        "fib_ranges": fib_ranges,  # Добавляем диапазоны
        "local_high": round(local_high_price, 5),
        "local_low": round(local_low_price, 5),
        "absolute_high": round(absolute_high_price, 5),
        "absolute_low": round(absolute_low_price, 5),
        "trend": trend_lower,
        "bars_used": actual_bars_loaded,
        "local_bars_used": local_bars,
        "log": log_messages,
    }

    return result


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
