# TradeSpace_v2/src/trading/trading.py
import MetaTrader5 as mt5
import logging
import pandas as pd
import numpy as np
import talib
from src.utils.mt5_utils import (
    initialize_mt5,
    shutdown_mt5,
    get_account_info,
    get_currency_tick,
    close_all_positions,
    close_positions_in_profit,
    close_positions_in_loss,
    close_positions_by_symbol,
    open_position,
)
import datetime
from logs.logi import (
    log_market_structure,
    log_fibonacci_levels,
    log_fvg_zones,
    log_ict_result,
)
from src.utils import investing_calendar, investing_news_selenium
from dotenv import load_dotenv
import os


# 1. Определение структуры рынка (тренды, диапазоны)
# Определение структуры рынка с использованием анализа максимумов/минимумов и более продвинутого метода для тренда
# 1. Определение структуры рынка (тренды, диапазоны, индикаторы)
def identify_market_structure(symbol, timeframe):
    df = get_rates_dataframe(symbol, timeframe, 500)
    if df is None:
        log_data_error(symbol)
        return None

    high = df["high"].max()
    low = df["low"].min()
    current_price = df["close"].iloc[-1]

    # Улучшенное определение тренда: учитываем последние максимумы и минимумы
    recent_highs = df["high"].rolling(window=20).max().iloc[-1]
    recent_lows = df["low"].rolling(window=20).min().iloc[-1]

    if current_price > recent_highs:
        trend = "strong_uptrend"
    elif current_price < recent_lows:
        trend = "strong_downtrend"
    else:
        trend = (
            "range"
            if recent_highs - recent_lows < (high - low) * 0.2
            else "uptrend" if current_price > df["close"].mean() else "downtrend"
        )

    # Использование скользящих средних для подтверждения тренда
    sma_50 = df["close"].rolling(window=50).mean().iloc[-1]
    sma_200 = df["close"].rolling(window=200).mean().iloc[-1]
    if sma_50 > sma_200:
        trend_confirmation = "uptrend_confirmation"
    elif sma_50 < sma_200:
        trend_confirmation = "downtrend_confirmation"
    else:
        trend_confirmation = "no_confirmation"

    # Использование ATR для анализа волатильности
    atr = talib.ATR(df["high"], df["low"], df["close"], timeperiod=14).iloc[-1]

    # Использование канала регрессии
    x = np.arange(len(df))
    y = df["close"]
    slope, intercept = np.polyfit(x, y, 1)
    upper_channel = intercept + slope * x + np.std(y)
    lower_channel = intercept + slope * x - np.std(y)
    regression_info = {
        "slope": slope,
        "intercept": intercept,
        "upper_channel": upper_channel[-1],
        "lower_channel": lower_channel[-1],
    }

    # Улучшенные уровни поддержки и сопротивления
    market_structure = {
        "current_price": current_price,
        "trend": trend,
        "trend_confirmation": trend_confirmation,
        "support": low,
        "resistance": high,
        "atr": atr,
        "regression": regression_info,
    }

    logging.info(
        f"MS-Структура рынка для {symbol}: Текущая цена={current_price}, Тренд={trend}, Подтверждение тренда={trend_confirmation}, Поддержка={low}, Сопротивление={high}, ATR={atr}, Канал регрессии={regression_info}"
    )
    return market_structure


# 2. Определение зон ликвидности с учетом FVG
def identify_liquidity_zones(symbol, timeframe):
    df = get_rates_dataframe(symbol, timeframe, 500)
    if df is None:
        log_data_error(symbol)
        return None, None

    # Рассчитываем основные и дополнительные уровни поддержки и сопротивления
    support_level = df["low"].min()
    resistance_level = df["high"].max()

    # Фильтрация экстремальных значений, чтобы избежать рыночных выбросов
    # Например, исключаем последние экстремальные точки, если они выбиваются из общего диапазона
    filtered_df = df[
        (df["high"] < df["high"].quantile(0.95))
        & (df["low"] > df["low"].quantile(0.05))
    ]
    secondary_support = filtered_df["low"].min()
    secondary_resistance = filtered_df["high"].max()

    # Дополнение анализа уровнями регрессионного канала
    regression_result = calculate_regression_channel(symbol, timeframe)
    if regression_result:
        secondary_support = min(secondary_support, regression_result["lower_channel"])
        secondary_resistance = max(
            secondary_resistance, regression_result["upper_channel"]
        )

    logging.info(
        f"LZ-Зоны ликвидности для {symbol}: Поддержка={support_level}, Сопротивление={resistance_level}, "
        f"Вторичная поддержка={secondary_support}, Вторичное сопротивление={secondary_resistance}"
    )
    return support_level, resistance_level, secondary_support, secondary_resistance


# 3. Оптимальные точки входа (OTE)
def calculate_fibonacci_levels(symbol, timeframe, trend="up"):
    df = get_rates_dataframe(symbol, timeframe, 100)
    if df is None or df.empty:
        log_data_error(symbol)
        return None

    high_price = df["high"].max()
    low_price = df["low"].min()
    diff = high_price - low_price

    # Проверяем на случай, если high и low равны (неизменный рынок)
    if diff == 0:
        logging.error(
            f"Ошибка: Недостаточный диапазон цен для расчета уровней Фибоначчи для {symbol}. High и Low равны."
        )
        return None

    fib_levels = {}

    if trend.lower() == "up":
        # Расчет уровней Фибоначчи для восходящего тренда (коррекция вниз)
        fib_levels = {
            "0.0%": high_price,
            "23.6%": high_price - 0.236 * diff,
            "38.2%": high_price - 0.382 * diff,
            "50.0%": high_price - 0.500 * diff,
            "61.8%": high_price - 0.618 * diff,
            "70.5%": high_price - 0.705 * diff,  # Сладкая точка для восходящего тренда
            "79.0%": high_price - 0.790 * diff,
            "100.0%": low_price,
        }
    elif trend.lower() == "down":
        # Расчет уровней Фибоначчи для нисходящего тренда (коррекция вверх)
        fib_levels = {
            "0.0%": low_price,
            "23.6%": low_price + 0.236 * diff,
            "38.2%": low_price + 0.382 * diff,
            "50.0%": low_price + 0.500 * diff,
            "61.8%": low_price + 0.618 * diff,
            "70.5%": low_price + 0.705 * diff,  # Сладкая точка для нисходящего тренда
            "79.0%": low_price + 0.790 * diff,
            "100.0%": high_price,
        }
    else:
        logging.error(
            f"Некорректное значение параметра trend: {trend}. Используйте 'up' или 'down'."
        )
        return None

    # Выводим уровни Фибоначчи в лог
    logging.info(f"Уровни Фибоначчи для {symbol} ({trend} trend):")
    for level, price in fib_levels.items():
        logging.info(f"{level}: {price}")

    return fib_levels


def determine_market_timing():
    current_time = datetime.datetime.utcnow()
    current_weekday = current_time.weekday()
    current_hour = current_time.hour

    if current_weekday >= 5:
        return "Рынок закрыт (выходные дни)"

    if 22 <= current_hour or current_hour < 7:
        return "Азиатская сессия"
    elif 7 <= current_hour < 15:
        return "Европейская сессия"
    elif 12 <= current_hour < 21:
        return "Американская сессия"
    else:
        return "Перекрытие сессий"


# Calculate CCI
def calculate_cci(symbol, timeframe, period=20):
    df = get_rates_dataframe(symbol, timeframe, period)
    if df is None:
        log_data_error(symbol)
        return None
    cci = talib.CCI(df["high"], df["low"], df["close"], timeperiod=period)
    return cci.iloc[-1] if not cci.empty else None


# Calculate ATR
def calculate_atr(symbol, timeframe, period=14):
    df = get_rates_dataframe(symbol, timeframe, period + 1)
    if df is None:
        return None
    tr = df["high"] - df["low"]
    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1]


# MACD Calculation
def calculate_macd(
    symbol, timeframe, short_period=12, long_period=26, signal_period=9, period=100
):
    df = get_rates_dataframe(symbol, timeframe, period + long_period)
    if df is None:
        return None, None

    ema_short = df["close"].ewm(span=short_period, adjust=False).mean()
    ema_long = df["close"].ewm(span=long_period, adjust=False).mean()
    macd = ema_short - ema_long
    signal = macd.ewm(span=signal_period, adjust=False).mean()

    logging.info(f"MACD для {symbol}: MACD={macd.iloc[-1]}, Signal={signal.iloc[-1]}")
    return macd.iloc[-1], signal.iloc[-1]


# RSI Calculation
def calculate_rsi(symbol, timeframe, period=14):
    df = get_rates_dataframe(symbol, timeframe, period + 1)
    if df is None:
        return None

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    logging.info(f"RSI для {symbol}: {rsi.iloc[-1]}")
    return rsi.iloc[-1]


# Bollinger Bands Calculation
def calculate_bollinger_bands(
    symbol, timeframe, period=20, num_std_dev=2, data_period=100
):
    df = get_rates_dataframe(symbol, timeframe, data_period + period)
    if df is None:
        return None, None, None

    sma = df["close"].rolling(window=period).mean()
    std_dev = df["close"].rolling(window=period).std()
    upper_band = sma + (num_std_dev * std_dev)
    lower_band = sma - (num_std_dev * std_dev)

    logging.info(
        f"Bollinger Bands для {symbol}: SMA={sma.iloc[-1]}, Upper={upper_band.iloc[-1]}, Lower={lower_band.iloc[-1]}"
    )
    return sma.iloc[-1], upper_band.iloc[-1], lower_band.iloc[-1]


# VWAP Calculation
def check_vwap(symbol, timeframe, period=100):
    df = get_rates_dataframe(symbol, timeframe, period)
    if df is None:
        log_data_error(symbol)
        return None

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_vwap = (typical_price * df["tick_volume"]).cumsum() / df[
        "tick_volume"
    ].cumsum()
    return cumulative_vwap.iloc[-1]


# Identify FVG with lookback set to 34
import logging
import pandas as pd


def identify_fvg(df, lookback=500, tolerance=0.01, min_gap_candles=2):
    """
    Идентификация зон FVG (Fair Value Gaps).

    df - DataFrame с рыночными данными
    lookback - количество последних свечей для проверки (например, 200 свечей)
    tolerance - допуск для сравнения цен high и low (для учета рыночных колебаний)
    min_gap_candles - минимальное количество свечей между зонами FVG, чтобы зона считалась значимой
    """

    # Проверяем, что данных достаточно для анализа
    if len(df) < lookback:
        logging.warning(
            f"Недостаточно данных для анализа FVG. Доступно только {len(df)} свечей. Будет использовано lookback={len(df) - 1}"
        )
        lookback = len(df) - 1

    fvg_zones = []
    logging.info(f"Проверка FVG на последних {lookback} свечах для символа")

    # Проходим по свечам с конца в начало, чтобы проверить на наличие FVG-зон
    for i in range(len(df) - lookback, len(df) - min_gap_candles):
        # Проверка на наличие FVG между несколькими свечами
        # Проверяем gap между двумя свечами с учетом `tolerance`
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
                f"Найдена FVG-зона с началом {df.index[i]} и концом {df.index[i + min_gap_candles]}: high={high_prev}, low={low_next}"
            )

    if not fvg_zones:
        logging.info("FVG-Зоны: Нет данных. Проверьте диапазон данных или рынок.")
    else:
        logging.info(f"Найдено FVG-зон: {len(fvg_zones)}")

    return fvg_zones if fvg_zones else "Нет данных"


# Пример использования функции для проверки FVG
if __name__ == "__main__":
    # Загрузите свои данные DataFrame (df) через get_rates_dataframe и вызовите функцию identify_fvg
    df = pd.DataFrame()  # Пример использования, подставьте свои данные OHLC
    fvg_zones = identify_fvg(df, lookback=300, tolerance=0.015)
    if fvg_zones != "Нет данных":
        for zone in fvg_zones:
            print(
                f"FVG Зона: Начало - {zone['start']}, Конец - {zone['end']}, High - {zone['high']}, Low - {zone['low']}"
            )


import matplotlib.pyplot as plt


def visualize_fvg(df, fvg_zones):
    plt.figure(figsize=(14, 7))
    plt.plot(df.index, df["close"], label="Close Price")
    for zone in fvg_zones:
        plt.axvspan(zone["start"], zone["end"], color="red", alpha=0.3)
    plt.title("Fair Value Gaps")
    plt.legend()
    plt.show()


import numpy as np
import pandas as pd
import logging


# Анализ канала регрессии
def calculate_regression_channel(symbol, timeframe):
    df = get_rates_dataframe(symbol, timeframe, period=500)
    if df is None or df.empty:
        logging.error(
            f"Ошибка: Недостаточно данных для регрессионного анализа по символу {symbol} и таймфрейму {timeframe}"
        )
        return None

    x = np.arange(len(df))
    y = df["close"]

    try:
        slope, intercept = np.polyfit(x, y, 1)
    except Exception as e:
        logging.error(f"Ошибка при расчете линейной регрессии для {symbol}: {e}")
        return None

    std_dev = np.std(y)
    upper_channel = intercept + slope * x + std_dev
    lower_channel = intercept + slope * x - std_dev

    regression_result = {
        "slope": slope,
        "intercept": intercept,
        "upper_channel": upper_channel[-1],
        "lower_channel": lower_channel[-1],
    }

    logging.info(
        f"Регрессионный анализ для {symbol} ({timeframe}): наклон={slope:.5f}, пересечение={intercept:.5f}, "
        f"верхний канал={upper_channel[-1]:.5f}, нижний канал={lower_channel[-1]:.5f}"
    )

    return regression_result


# Stochastic Calculation
def calculate_stochastic(symbol, timeframe):
    try:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
        if rates is None or len(rates) == 0:
            log_data_error(symbol)
            return None, None

        high_prices = [rate["high"] for rate in rates]
        low_prices = [rate["low"] for rate in rates]
        close_prices = [rate["close"] for rate in rates]

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

        return slowk[-1], slowd[-1]
    except Exception as e:
        logging.error(f"Ошибка при расчете Stochastic для {symbol}: {e}")
        return None, None


# MFI Calculation
def calculate_mfi(symbol, timeframe, period=14):
    df = get_rates_dataframe(symbol, timeframe, period + 1)
    if df is None or df["tick_volume"].isnull().all():
        log_data_error(symbol)
        return None

    mfi = talib.MFI(
        df["high"], df["low"], df["close"], df["tick_volume"], timeperiod=period
    )
    return mfi.iloc[-1] if not mfi.empty else None


# Close Position by Ticket
def close_position_by_ticket(ticket):
    position = mt5.positions_get(ticket=ticket)
    if not position:
        logging.error(f"Ошибка: Позиция с тикетом {ticket} не найдена.")
        return False

    symbol, volume, order_type = (
        position[0].symbol,
        position[0].volume,
        (
            mt5.ORDER_TYPE_SELL
            if position[0].type == mt5.ORDER_TYPE_BUY
            else mt5.ORDER_TYPE_BUY
        ),
    )
    price = (
        mt5.symbol_info_tick(symbol).bid
        if order_type == mt5.ORDER_TYPE_SELL
        else mt5.symbol_info_tick(symbol).ask
    )

    close_order = mt5.order_send(
        action=mt5.TRADE_ACTION_DEAL,
        symbol=symbol,
        volume=volume,
        type=order_type,
        price=price,
        deviation=20,
        magic=123456,
        comment="Automated Close",
    )
    if close_order.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Ошибка при закрытии позиции {ticket}: {close_order.retcode}")
        return False

    send_trade_report(symbol, volume, "закрытие", price, profit=position[0].profit)
    return True


# Get Open Positions
def get_open_positions():
    positions = mt5.positions_get()
    if positions is None:
        logging.error("Ошибка при получении открытых позиций")
        return []

    return [
        {
            "ticket": position.ticket,
            "symbol": position.symbol,
            "volume": position.volume,
            "price": position.price_open,
            "profit": position.profit,
        }
        for position in positions
    ]


# Get Account Balance
def get_balance():
    account_info = mt5.account_info()
    if account_info is None:
        logging.error("Ошибка при получении информации о счете")
        return None
    return account_info.balance


# Automated Trading
def automated_trading(symbol):
    direction = check_indicators_for_entry(symbol)
    if direction:
        open_position_with_indicators(symbol, volume=0.02, direction=direction)
        logging.info(f"Открыта позиция {direction} для {symbol}")
    else:
        logging.info(f"Нет подходящих сигналов для {symbol}")


# Calculate Stop Loss and Take Profit
def calculate_stop_loss_take_profit(symbol, atr_value, entry_price, direction):
    multiplier = 1.5 if direction == "buy" else -1.5
    stop_loss = entry_price - multiplier * atr_value
    take_profit = (
        entry_price + 2 * atr_value
        if direction == "buy"
        else entry_price - 2 * atr_value
    )
    return stop_loss, take_profit


# Итоговая стратегия ICT
def ict_strategy(symbol, timeframe):
    analysis_info = {}

    # Структура рынка
    market_structure = identify_market_structure(symbol, timeframe)
    if market_structure:
        analysis_info["market_structure"] = market_structure

    # Ликвидность
    support, resistance, secondary_support, secondary_resistance = (
        identify_liquidity_zones(symbol, timeframe)
    )

    # Обновляем информацию для анализа
    analysis_info["liquidity"] = {
        "support": support,
        "resistance": resistance,
        "secondary_support": secondary_support,
        "secondary_resistance": secondary_resistance,
    }

    # FVG Зоны
    df = get_rates_dataframe(symbol, timeframe, 500)
    fvg_zones = identify_fvg(df)
    analysis_info["fvg_zones"] = fvg_zones

    # Уровни Фибоначчи
    fib_levels = calculate_fibonacci_levels(symbol, timeframe)
    analysis_info["ote_levels"] = fib_levels

    # Тайминги рынка
    current_session = determine_market_timing()
    analysis_info["market_timing"] = {"current_session": current_session}

    # Решение стратегии
    current_price = market_structure["current_price"]
    if current_price > resistance:
        analysis_info["signal"] = "buy"
        analysis_info["decision"] = "Покупка: цена выше уровня сопротивления."
    elif current_price < support:
        analysis_info["signal"] = "sell"
        analysis_info["decision"] = "Продажа: цена ниже уровня поддержки."
    else:
        analysis_info["signal"] = "no_signal"
        analysis_info["decision"] = "Нет сигнала для открытия позиции."

    logging.info(f"ICT Результат стратегии для {symbol}: {analysis_info}")
    return analysis_info


# Get Indicators Data
def get_indicators_data(symbol, timeframe, trend="up"):
    indicators = {}

    # MACD
    try:
        macd_value, signal_value = calculate_macd(symbol, timeframe)
        indicators["macd"] = macd_value
        indicators["signal"] = signal_value
    except Exception as e:
        logging.exception(f"Ошибка при расчете MACD для {symbol}: {e}")

    # Bollinger Bands
    try:
        sma, upper_band, lower_band = calculate_bollinger_bands(symbol, timeframe)
        indicators["sma"] = sma
        indicators["upper_band"] = upper_band
        indicators["lower_band"] = lower_band
    except Exception as e:
        logging.exception(f"Ошибка при расчете Bollinger Bands для {symbol}: {e}")

    # RSI
    try:
        rsi = calculate_rsi(symbol, timeframe)
        indicators["rsi"] = rsi
    except Exception as e:
        logging.exception(f"Ошибка при расчете RSI для {symbol}: {e}")

    # ATR
    try:
        atr = calculate_atr(symbol, timeframe)
        indicators["atr"] = atr
    except Exception as e:
        logging.exception(f"Ошибка при расчете ATR для {symbol}: {e}")

    # Stochastic Oscillator
    try:
        stochastic_k, stochastic_d = calculate_stochastic(symbol, timeframe)
        indicators["stochastic_k"] = stochastic_k
        indicators["stochastic_d"] = stochastic_d
    except Exception as e:
        logging.exception(f"Ошибка при расчете Stochastic для {symbol}: {e}")

    # VWAP
    try:
        vwap = check_vwap(symbol, timeframe)
        indicators["vwap"] = vwap
    except Exception as e:
        logging.exception(f"Ошибка при расчете VWAP для {symbol}: {e}")

    # CCI
    try:
        cci = calculate_cci(symbol, timeframe)
        indicators["cci"] = cci
    except Exception as e:
        logging.exception(f"Ошибка при расчете CCI для {symbol}: {e}")

    # MFI
    try:
        mfi = calculate_mfi(symbol, timeframe)
        indicators["mfi"] = mfi
    except Exception as e:
        logging.exception(f"Ошибка при расчете MFI для {symbol}: {e}")

    # Fibonacci Levels
    try:
        fibonacci_levels = calculate_fibonacci_levels(symbol, timeframe, trend)
        indicators["fibonacci_levels"] = fibonacci_levels
    except Exception as e:
        logging.exception(f"Ошибка при расчете уровней Фибоначчи для {symbol}: {e}")

    # Regression Channel
    try:
        regression_channel = calculate_regression_channel(symbol, timeframe)
        indicators["regression_channel"] = regression_channel
    except Exception as e:
        logging.exception(f"Ошибка при расчете канала регрессии для {symbol}: {e}")

    return indicators if indicators else None


# Send Trade Report
def send_trade_report(symbol, volume, action, price, profit):
    report_message = (
        f"Торговый отчет\n"
        f"Символ: {symbol}\n"
        f"Объём: {volume}\n"
        f"Действие: {action}\n"
        f"Цена: {price}\n"
        f"Прибыль: {profit}\n"
    )
    logging.info(report_message)
    print(report_message)


# Open Position with Indicators
def open_position_with_indicators(symbol, volume, direction):
    order_type = mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL
    price = (
        mt5.symbol_info_tick(symbol).ask
        if order_type == mt5.ORDER_TYPE_BUY
        else mt5.symbol_info_tick(symbol).bid
    )

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 123456,
        "comment": "Automated Trade",
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Ошибка при открытии позиции для {symbol}: {result.retcode}")
        return False

    send_trade_report(symbol, volume, direction, price, profit=None)
    return True


# СТРАТЕГИЯ SNR
def snr_strategy(symbol, timeframe):
    """
    Стратегия SNR (Support and Resistance) для анализа рыночной структуры и генерации торговых сигналов.
    """
    # Получаем данные о свечах (OHLC) для символа и таймфрейма
    df = get_rates_dataframe(symbol, timeframe, period=500)
    if df is None or df.empty:
        logging.error(
            f"Ошибка: Недостаточно данных для стратегии SNR по символу {symbol} и таймфрейму {timeframe}"
        )
        return None

    # Определение уровней поддержки и сопротивления на основе экстремумов
    high_level = df["high"].rolling(window=20).max()  # Сопротивление
    low_level = df["low"].rolling(window=20).min()  # Поддержка

    # Получаем текущую цену
    current_price = df["close"].iloc[-1]

    # Логика для определения сигналов на покупку или продажу
    signal = None
    if current_price >= high_level.iloc[-1]:
        signal = "sell"
        logging.info(
            f"SNR: Сигнал на продажу по {symbol}. Текущая цена: {current_price}, Уровень сопротивления: {high_level.iloc[-1]}"
        )
    elif current_price <= low_level.iloc[-1]:
        signal = "buy"
        logging.info(
            f"SNR: Сигнал на покупку по {symbol}. Текущая цена: {current_price}, Уровень поддержки: {low_level.iloc[-1]}"
        )
    else:
        logging.info(
            f"SNR: Нет сигнала для {symbol}. Текущая цена находится между уровнями поддержки и сопротивления."
        )

    # Возвращаем результат анализа
    return {
        "current_price": current_price,
        "support_level": low_level.iloc[-1],
        "resistance_level": high_level.iloc[-1],
        "signal": signal,
    }


# SMC Strategy
def smc_strategy(symbol, timeframe):
    support, resistance = identify_liquidity_zones(symbol, timeframe)
    current_price = mt5.symbol_info_tick(symbol).ask
    macd, signal = calculate_macd(symbol, timeframe)
    atr = calculate_atr(symbol, timeframe)

    logging.info(
        f"Текущая цена для {symbol}: {current_price}, MACD: {macd}, Signal: {signal}, ATR: {atr}"
    )

    if current_price > resistance and macd > signal and atr > 0.5:
        logging.info(f"Условие на открытие BUY выполнено для {symbol}")
        return "buy"
    elif current_price < support and macd < signal and atr > 0.5:
        logging.info(f"Условие на открытие SELL выполнено для {symbol}")
        return "sell"
    else:
        logging.info(f"Условия для открытия позиции на {symbol} не выполнены")
        return None


# Check Indicators for Entry Signal
def check_indicators_for_entry(symbol, timeframe="H1"):
    indicators = get_indicators_data(symbol, timeframe)

    if not indicators:
        logging.error(f"Ошибка при получении данных индикаторов для {symbol}")
        return None

    # Example logic to determine trade direction based on MACD and RSI
    macd = indicators["macd"]
    signal = indicators["signal"]
    rsi = indicators["rsi"]

    if macd > signal and rsi < 30:
        logging.info(f"Сигнал на покупку по {symbol} на основе MACD и RSI")
        return "buy"
    elif macd < signal and rsi > 70:
        logging.info(f"Сигнал на продажу по {symbol} на основе MACD и RSI")
        return "sell"
    else:
        logging.info(f"Нет сигнала по {symbol}")
        return None


# Open Position
def open_position_with_indicators(symbol, volume=0.1, direction="buy"):
    order_type = mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL
    price = (
        mt5.symbol_info_tick(symbol).ask
        if order_type == mt5.ORDER_TYPE_BUY
        else mt5.symbol_info_tick(symbol).bid
    )

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 123456,
        "comment": "Automated Trade",
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"Ошибка при открытии позиции для {symbol}: {result.retcode}")
        return False
    send_trade_report(symbol, volume, direction, price, profit=None)
    return True


# Automated Trading Function
def automated_trading(symbol):
    direction = check_indicators_for_entry(symbol)
    if direction:
        open_position_with_indicators(symbol, volume=0.02, direction=direction)
        logging.info(f"Открыта позиция {direction} для {symbol}")
    else:
        logging.info(f"Нет подходящих сигналов для {symbol}")


# Main function to execute trading strategy
def execute_trading_strategy():
    symbol = "EURUSD"
    timeframe = mt5.TIMEFRAME_H1

    # Connect to MetaTrader 5
    if not mt5.initialize():
        logging.error("MetaTrader 5 initialization failed")
        return

    # Place your automated trading strategy here
    automated_trading(symbol)

    # Shut down connection to MetaTrader 5
    mt5.shutdown()


# Run the trading strategy
if __name__ == "__main__":
    logging.basicConfig(level=logging.info)
    execute_trading_strategy()

from django.shortcuts import redirect, render
from .trading import (
    ict_strategy,
    get_indicators_data,
    get_balance,
    get_open_positions,
    open_position_with_indicators,
    close_position_by_ticket,
)


# View для отображения панели управления
import MetaTrader5 as mt5
import logging
import pandas as pd
import numpy as np
import talib
from src.utils.mt5_utils import get_rates_dataframe
import datetime
from logs.logi import (
    log_market_structure,
    log_fibonacci_levels,
    log_fvg_zones,
    log_ict_result,
)
from django.shortcuts import redirect, render
from .trading import (
    ict_strategy,
    get_indicators_data,
    get_balance,
    get_open_positions,
    open_position_with_indicators,
    close_position_by_ticket,
)


# Helper function to log errors if dataframe is None
def log_data_error(symbol):
    logging.error(f"Ошибка при получении данных для {symbol}")


# View для отображения панели управления

from webapp.templatetags.custom_tags import get_value


import numpy as np
import pandas as pd
import logging


def calculate_regression_channel(symbol, timeframe):
    # Получаем данные о свечах (OHLC) для символа и таймфрейма
    df = get_rates_dataframe(symbol, timeframe, period=500)
    if df is None or df.empty:
        logging.error(
            f"Ошибка: Недостаточно данных для регрессионного анализа по символу {symbol} и таймфрейму {timeframe}"
        )
        return None

    # Рассчитываем параметры линейной регрессии
    x = np.arange(len(df))
    y = df["close"]

    # Применяем линейную регрессию
    slope, intercept = np.polyfit(x, y, 1)

    # Рассчитываем верхний и нижний канал регрессии
    std_dev = np.std(y)
    upper_channel = intercept + slope * x + std_dev
    lower_channel = intercept + slope * x - std_dev

    # Возвращаем результаты последнего значения канала для удобного отображения
    regression_result = {
        "slope": slope,
        "intercept": intercept,
        "upper_channel": upper_channel[-1],
        "lower_channel": lower_channel[-1],
    }

    # Добавляем логирование для отладки
    logging.info(
        f"Регрессионный анализ для {symbol} ({timeframe}): наклон={slope:.5f}, пересечение={intercept:.5f}, "
        f"верхний канал={upper_channel[-1]:.5f}, нижний канал={lower_channel[-1]:.5f}"
    )

    return regression_result


# View для открытия позиции
def open_position_view(request):
    if request.method == "POST":
        symbol = request.POST.get("symbol")
        direction = request.POST.get("direction")
        volume = float(request.POST.get("volume"))

        # Открываем позицию
        open_position_with_indicators(symbol, volume, direction)

    return redirect("dashboard")  # Возвращаемся на дашборд


# View для закрытия позиции по тикету
def close_position_view(request, ticket):
    close_position_by_ticket(ticket)
    return redirect("dashboard")


def run_strategy(currency_pair, timeframe, strategy_function, strategy_name):
    """Запуск стратегии и логирование"""
    try:
        result = strategy_function(currency_pair, timeframe)

        return result
    except Exception as e:
        # logging.error(f"Ошибка в стратегии {strategy_name} для {timeframe}: {e}")
        return {}


def analyze_strategies_for_timeframes(symbol, timeframes):
    indicators_by_timeframe = {}
    ict_strategies_by_timeframe = {}
    smc_strategies_by_timeframe = {}
    snr_strategies_by_timeframe = {}  # Добавляем SNR стратегию

    for label, timeframe in timeframes.items():
        # logging.error(f"Анализ индикаторов для {symbol} на таймфрейме {label}")
        indicators = get_indicators_data(symbol, timeframe)

        if indicators:
            indicators_by_timeframe[label] = indicators
            logging.info(f"Индикаторы для {label}: {indicators}")

        # Запуск ICT стратегии
        ict_strategies_by_timeframe[label] = run_strategy(
            symbol, timeframe, ict_strategy, "ICT"
        )

        # Запуск SMC стратегии
        smc_strategies_by_timeframe[label] = run_strategy(
            symbol, timeframe, smc_strategy, "SMC"
        )

        # Запуск SNR стратегии
        snr_result = snr_strategy(symbol, timeframe)
        if snr_result:
            snr_strategies_by_timeframe[label] = snr_result
            logging.info(
                f"SNR: Результат SNR стратегии для {symbol} ({label}): {snr_result}"
            )
        else:
            logging.warning(
                f"SNR стратегия не дала результат для {symbol} на таймфрейме {label}"
            )

    return (
        indicators_by_timeframe,
        ict_strategies_by_timeframe,
        smc_strategies_by_timeframe,
        snr_strategies_by_timeframe,  # Добавляем SNR результаты в возвращаемое значение
    )
