# TradeSpace_v3_/src/trading/trading.py
import logging
import os
import datetime
import numpy as np
import pandas as pd
import talib
import MetaTrader5 as mt5

from dotenv import load_dotenv
from src.indicators.technical_indicators import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_cci,
    calculate_fibonacci_levels,
    calculate_macd,
    calculate_mfi,
    calculate_rsi,
    calculate_stochastic,
    check_vwap,
    identify_fvg,
)
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
    get_rates_dataframe,
)
from logs.logi import (
    log_market_structure,
    log_fibonacci_levels,
    log_fvg_zones,
    log_ict_result,
)
from src.utils import investing_calendar, investing_news_selenium


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

from dotenv import load_dotenv
import os
import openai

load_dotenv()

# Проверка
print("🔑 OPENAI_API_KEY =", os.getenv("OPENAI_API_KEY"))

openai.api_key = os.getenv("OPENAI_API_KEY")

# openai.api_key = os.getenv("OPENAI_API_KEY") # Если используется AI, можно раскомментировать


# ==========================
# ЛОГИРОВАНИЕ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================


def log_data_error(symbol):
    logging.error(f"Ошибка при получении данных для {symbol}")


# ==========================
# ФУНКЦИИ ПОЛУЧЕНИЯ ДАННЫХ И ИНДИКАТОРЫ
# ==========================


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

    # Округляем до 5 знаков после запятой
    regression_result = {
        "slope": round(slope, 5),  # Наклон
        "intercept": round(intercept, 5),  # Пересечение
        "upper_channel": round(upper_channel[-1], 5),  # Верхний канал
        "lower_channel": round(lower_channel[-1], 5),  # Нижний канал
    }

    logging.info(
        f"Регрессионный анализ для {symbol} ({timeframe}): наклон={regression_result['slope']}, "
        f"пересечение={regression_result['intercept']}, верхний канал={regression_result['upper_channel']}, "
        f"нижний канал={regression_result['lower_channel']}"
    )

    return regression_result  # Возвращаем результаты регрессионного анализа


def prepare_fibonacci_levels_as_fields(symbol, timeframe, trend="up"):
    fib_levels = calculate_fibonacci_levels(symbol, timeframe, trend)
    if fib_levels is None:
        return {}
    # Убедимся, что ключи правильно формируются
    formatted_levels = {
        f"fib_{key.split('.')[0]}": value for key, value in fib_levels.items()
    }
    logging.info(
        f"Formatted Fibonacci levels for {symbol} {timeframe}: {formatted_levels}"
    )
    return formatted_levels


def prepare_fibonacci_levels(symbol, timeframe, trend="up", as_string=False):
    fib_levels = calculate_fibonacci_levels(symbol, timeframe, trend)
    if fib_levels is None:
        return "Нет данных" if as_string else {}
    if as_string:
        return ", ".join(f"{level}: {price:.5f}" for level, price in fib_levels.items())
    return {f"fib_{key.split('.')[0]}": value for key, value in fib_levels.items()}


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


# ==========================
# ОПРЕДЕЛЕНИЕ РЫНОЧНОЙ СТРУКТУРЫ И СТРАТЕГИЙ
# ==========================

# from src.indicators.market_structure import identify_market_structure


# ==========================
# ТЕСТИРОВАНИЕ СТРАТЕГИЙ
# ==========================

from src.trading.ict_strategy import ict_strategy
from src.trading.smc_strategy import smc_strategy
from src.trading.snr_strategy import snr_strategy


def test_strategies(symbol="EURUSD", timeframe=mt5.TIMEFRAME_H1):
    initialize_mt5()
    try:
        ict_result = ict_strategy(symbol, timeframe)
        logging.info(f"ICT Strategy: {ict_result}")

        smc_result = smc_strategy(symbol, timeframe)
        logging.info(f"SMC Strategy: {smc_result}")

        snr_result = snr_strategy(symbol, timeframe)
        logging.info(f"SNR Strategy: {snr_result}")
    finally:
        shutdown_mt5()


if __name__ == "__main__":
    test_strategies()

# ==========================
# ОТЧЁТЫ, ОТКРЫТИЕ/ЗАКРЫТИЕ ПОЗИЦИЙ
# ==========================


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


def close_position_by_ticket(ticket):
    position = mt5.positions_get(ticket=ticket)
    if not position:
        logging.error(f"Позиция {ticket} не найдена.")
        return False

    symbol = position[0].symbol
    volume = position[0].volume
    order_type = (
        mt5.ORDER_TYPE_SELL
        if position[0].type == mt5.ORDER_TYPE_BUY
        else mt5.ORDER_TYPE_BUY
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


def get_open_positions():
    positions = mt5.positions_get()
    if positions is None:
        logging.error("Ошибка при получении открытых позиций")
        return []

    return [
        {
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "price": pos.price_open,
            "profit": pos.profit,
        }
        for pos in positions
    ]


def get_balance():
    account_info = mt5.account_info()
    if account_info is None:
        logging.error("Ошибка при получении информации о счете")
        return None
    return account_info.balance


# ==========================
# ИНТЕГРАЦИЯ СТРАТЕГИЙ ПО ТАЙМФРЕЙМАМ
# ==========================


def run_strategy(symbol, timeframe, strategy_function, strategy_name):
    try:
        result = strategy_function(symbol, timeframe)
        return result
    except Exception as e:
        logging.error(f"Ошибка в стратегии {strategy_name} для {timeframe}: {e}")
        return {}


from src.indicators.technical_indicators import get_indicators_data


def analyze_strategies_for_timeframes(symbol, timeframes, num_values=1):
    indicators_by_timeframe = {}
    ict_strategies_by_timeframe = {}
    smc_strategies_by_timeframe = {}
    snr_strategies_by_timeframe = {}

    for label, tf in timeframes.items():
        # Получаем индикаторы с нужным num_values
        indicators = get_indicators_data(symbol, tf, trend="up", num_values=num_values)
        if indicators:
            indicators_by_timeframe[label] = indicators

        ict_data = ict_strategy(symbol, tf, num_values=num_values)
        ict_strategies_by_timeframe[label] = ict_data

        smc_data = smc_strategy(symbol, tf, num_values=num_values)
        smc_strategies_by_timeframe[label] = smc_data

        snr_data = snr_strategy(symbol, tf, num_values=num_values)
        snr_strategies_by_timeframe[label] = (
            snr_data if snr_data else {"signal": "no_signal"}
        )

    return (
        indicators_by_timeframe,
        ict_strategies_by_timeframe,
        smc_strategies_by_timeframe,
        snr_strategies_by_timeframe,
    )


# ==========================
# АВТОМАТИЗАЦИЯ ТОРГОВЛИ
# ==========================


def check_indicators_for_entry(symbol, timeframe="H1"):
    indicators = get_indicators_data(symbol, timeframe)
    if not indicators:
        logging.error(f"Ошибка при получении индикаторов для {symbol}")
        return None

    macd = indicators["macd"]
    signal = indicators["signal"]
    rsi = indicators["rsi"]

    if macd and signal and rsi:
        macd_last = macd[-1]
        signal_last = signal[-1]
        rsi_last = rsi[-1]
    else:
        return None

    if macd_last is not None and signal_last is not None and rsi_last is not None:
        if macd_last > signal_last and rsi_last < 30:
            return "buy"
        elif macd_last < signal_last and rsi_last > 70:
            return "sell"
        else:
            return None
    return None


def automated_trading(symbol):
    direction = check_indicators_for_entry(symbol)
    if direction:
        open_position_with_indicators(symbol, volume=0.02, direction=direction)
        logging.info(f"Открыта позиция {direction} для {symbol}")
    else:
        logging.info(f"Нет подходящих сигналов для {symbol}")


def execute_trading_strategy():
    symbol = "EURUSD"
    timeframe = mt5.TIMEFRAME_H1
    if not mt5.initialize():
        logging.error("MetaTrader 5 initialization failed")
        return
    automated_trading(symbol)
    mt5.shutdown()
