# TradeSpace_v2/src/utils/mt5_utils.py
import MetaTrader5 as mt5
import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Получение данных OHLC для символа
def get_rates_dataframe(symbol, timeframe, period=500):
    try:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period)
        if rates is None or len(rates) == 0:
            return None
        return pd.DataFrame(rates)
    except Exception as e:
        logging.error(f"Ошибка при получении данных для {symbol}: {e}")
        return None


# Инициализация MetaTrader 5
def initialize_mt5():
    if not mt5.initialize():
        raise Exception("Ошибка при инициализации MetaTrader 5")
    else:
        print("MetaTrader 5 успешно инициализирован")


def shutdown_mt5():
    mt5.shutdown()
    print("MetaTrader 5 отключен")


def get_account_info():
    initialize_mt5()
    # Получение информации об аккаунте из MT5
    account_info = mt5.account_info()
    if account_info is None:
        raise Exception("Не удалось получить информацию о счете")

    # Получение списка всех открытых позиций для вычисления объема и количества
    open_positions = mt5.positions_get()
    total_volume = (
        sum([position.volume for position in open_positions]) if open_positions else 0
    )
    open_positions_count = len(open_positions) if open_positions else 0

    # Логирование данных для отладки
    logging.info(f"Баланс: {account_info.balance}, Капитал: {account_info.equity}")

    # Формирование полного словаря с данными аккаунта
    return {
        "balance": account_info.balance,
        "equity": account_info.equity,
        "margin": account_info.margin,
        "free_margin": account_info.margin_free,
        "margin_level": account_info.margin_level,
        "credit": account_info.credit,
        "profit": account_info.profit,
        "loss": -account_info.profit if account_info.profit < 0 else 0,
        "currency": account_info.currency,
        "open_positions_count": open_positions_count,
        "total_volume": total_volume,
    }


import MetaTrader5 as mt5
from datetime import datetime, timedelta


def get_trade_history(start_date=None, end_date=None):
    initialize_mt5()
    if not start_date:
        start_date = datetime(2000, 1, 1)  # Начало истории
    if not end_date:
        end_date = datetime.now()  # Текущая дата

    deals = mt5.history_deals_get(start_date, end_date)
    if deals is None:
        raise RuntimeError(f"Failed to get deals: {mt5.last_error()}")

    result = []
    for deal in deals:
        result.append(
            {
                "time": deal.time,
                "symbol": deal.symbol,
                "profit": deal.profit,
                "volume": deal.volume,
                "price": deal.price,
            }
        )
    return result


def shutdown_mt5():
    mt5.shutdown()


def get_trading_profit_history(days=70):
    """
    Получает историю профита по торговым операциям за последние `days` дней.
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    # Получаем историю сделок с MetaTrader 5
    trades = mt5.history_deals_get(start_time, end_time)

    if trades is None:
        print(f"Ошибка получения истории сделок: {mt5.last_error()}")
        return []

    profit_history = []
    for trade in trades:
        profit_history.append(trade.profit)

    return profit_history


def get_historical_account_data():
    """Получает историю баланса и капитала для отображения на графике."""
    today = datetime.now()
    start_date = today - timedelta(days=365)

    # Получаем историю сделок
    rates = mt5.history_deals_get(start_date, today)
    if rates is None:
        print(f"Ошибка получения истории сделок: {mt5.last_error()}")
        return []

    # Формируем список данных
    historical_data = []
    balance = 0

    for deal in rates:
        if deal.type == mt5.DEAL_TYPE_BALANCE:
            balance += deal.profit
        historical_data.append(
            {
                "date": datetime.fromtimestamp(deal.time).strftime("%Y-%m-%d"),
                "balance": balance,
            }
        )

    return historical_data


def get_account_and_positions():
    """Получение информации о счете и открытых позициях"""
    account_info = get_account_info()
    open_positions = get_open_positions()
    return account_info, open_positions


def get_currency_tick(symbol):
    try:
        logging.info(f"Попытка активировать символ: {symbol}")
        if not mt5.symbol_select(symbol, True):  # Попытка активировать символ
            raise Exception(f"Символ {symbol} не удалось выбрать или активировать")

        logging.info(f"Символ {symbol} активирован, пытаемся получить тик")
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise Exception(f"Не удалось получить тик для символа {symbol}")

        logging.info(f"Тик для {symbol} получен: Bid={tick.bid}, Ask={tick.ask}")
        return {"bid": tick.bid, "ask": tick.ask}
    except Exception as e:
        logging.error(f"Ошибка в get_currency_tick для {symbol}: {e}")
        raise e


def log_available_symbols():
    symbols = mt5.symbols_get()
    logging.info(f"Доступные символы: {[symbol.name for symbol in symbols]}")


def get_ohlc(symbol, timeframe, number_of_candles):
    if not mt5.symbol_select(symbol, True):
        raise Exception(f"Не удалось выбрать символ {symbol}")
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, number_of_candles)
    if rates is None:
        raise Exception(f"Не удалось получить данные для символа {symbol}")
    rates_frame = pd.DataFrame(rates)
    rates_frame["time"] = pd.to_datetime(rates_frame["time"], unit="s")
    return rates_frame[["time", "open", "high", "low", "close"]]


# Открытие позиции с комментарием
def open_position(symbol, volume, order_type, reason):
    price = (
        mt5.symbol_info_tick(symbol).ask
        if order_type == mt5.ORDER_TYPE_BUY
        else mt5.symbol_info_tick(symbol).bid
    )
    comment = f"OpenOrder: {reason}"

    order = mt5.order_send(
        symbol=symbol,
        action=mt5.TRADE_ACTION_DEAL,
        volume=volume,
        type=order_type,
        price=price,
        deviation=100,  # Допустимое отклонение
        magic=123456,  # Change to appropriate magic number
        comment=comment,  # Комментарий с причиной входа
    )

    if order is None:
        print(f"Ошибка: не удалось отправить ордер на открытие позиции для {symbol}")
        print(f"Последняя ошибка: {mt5.last_error()}")
        return False

    if order.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Ошибка при открытии позиции для {symbol}: {order.retcode}")
        print(f"Последняя ошибка: {mt5.last_error()}")
        return False

    print(
        f"Открыта позиция {order_type} для {symbol}, объем {volume}, причина: {reason}"
    )
    return True


# Открытие позиции с комментарием
def open_market_position(symbol, volume, direction, take_profit=None, stop_loss=None):
    try:
        initialize_mt5()

        # Получаем текущую цену для открытия позиции
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            raise Exception(f"Не удалось получить тик для символа {symbol}")

        price = tick.ask if direction == "buy" else tick.bid
        if price is None:
            raise Exception(f"Не удалось получить цену для символа {symbol}")

        # Определяем тип ордера: покупка или продажа
        order_type = mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL

        # Формируем запрос на открытие позиции
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "Automated Open",
        }

        # Добавляем take profit и stop loss, если указаны
        if take_profit:
            request["tp"] = take_profit
        if stop_loss:
            request["sl"] = stop_loss

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(
                f"Ошибка при открытии позиции для {symbol}: {result.retcode}"
            )

        logging.info(f"Позиция {direction.upper()} для {symbol} успешно открыта.")
        return True

    except Exception as e:
        logging.error(f"Ошибка при открытии позиции для {symbol}: {e}")
        return False

    finally:
        shutdown_mt5()


# Установка отложенного ордера
def place_pending_order(
    symbol, volume, order_type, price, take_profit=None, stop_loss=None
):
    try:
        initialize_mt5()

        # Определяем тип ордера MetaTrader 5
        if order_type == "buy_limit":
            order_type_mt5 = mt5.ORDER_TYPE_BUY_LIMIT
        elif order_type == "sell_limit":
            order_type_mt5 = mt5.ORDER_TYPE_SELL_LIMIT
        elif order_type == "buy_stop":
            order_type_mt5 = mt5.ORDER_TYPE_BUY_STOP
        elif order_type == "sell_stop":
            order_type_mt5 = mt5.ORDER_TYPE_SELL_STOP
        else:
            raise ValueError(f"Неизвестный тип ордера: {order_type}")

        # Создаем словарь с параметрами ордера
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": order_type_mt5,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Pending order from dashboard",
            "type_time": mt5.ORDER_TIME_GTC,  # "Good till cancelled"
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Добавляем take profit и stop loss, если указаны
        if take_profit:
            request["tp"] = take_profit
        if stop_loss:
            request["sl"] = stop_loss

        # Отправляем запрос на выполнение ордера
        result = mt5.order_send(request)

        # Проверяем результат
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"Ошибка при установке отложенного ордера: {result.comment}")
            return False

        logging.info(f"Отложенный ордер {order_type} для {symbol} успешно установлен.")
        return True

    except Exception as e:
        logging.error(f"Ошибка при установке отложенного ордера для {symbol}: {e}")
        return False

    finally:
        shutdown_mt5()


def close_position_by_ticket(ticket):
    """
    Закрытие позиции по тикету с улучшенным логированием.
    """
    try:
        initialize_mt5()

        position = mt5.positions_get(ticket=ticket)
        if not position:
            raise Exception(f"Позиция с тикетом {ticket} не найдена.")

        symbol = position[0].symbol
        volume = position[0].volume

        # Определяем тип ордера: закрытие buy через sell и наоборот
        order_type = (
            mt5.ORDER_TYPE_SELL
            if position[0].type == mt5.ORDER_TYPE_BUY
            else mt5.ORDER_TYPE_BUY
        )

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise Exception(f"Не удалось получить тик для символа {symbol}")

        price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
        if price is None:
            raise Exception(f"Не удалось получить цену для символа {symbol}")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "Automated Close",
        }

        close_order = mt5.order_send(request)
        if close_order.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(
                f"Ошибка при закрытии позиции {ticket}: {close_order.retcode}"
            )

        logging.info(f"Позиция {ticket} успешно закрыта.")
        return close_order

    except Exception as e:
        logging.error(f"Ошибка при закрытии позиции {ticket}: {e}")
        return None

    finally:
        shutdown_mt5()


def close_all_positions():
    """
    Закрытие всех позиций.
    """
    try:
        initialize_mt5()

        positions = mt5.positions_get()
        if not positions:
            logging.info("Нет позиций для закрытия.")
            return False

        for position in positions:
            close_position(position.ticket)

        logging.info("Все позиции успешно закрыты.")
        return True

    except Exception as e:
        logging.error(f"Ошибка при закрытии всех позиций: {e}")
        return False

    finally:
        shutdown_mt5()


def open_position(symbol, volume, direction, count=1):
    """
    Открытие новой позиции с заданным объемом и направлением.

    :param symbol: Финансовый инструмент (например, 'EURUSDm').
    :param volume: Объем позиции (например, 0.01).
    :param direction: Направление ('buy' для покупки или 'sell' для продажи).
    :param count: Количество позиций для открытия.
    """
    try:
        initialize_mt5()

        for i in range(count):
            # Получаем текущую цену для открытия позиции
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                raise Exception(f"Не удалось получить тик для символа {symbol}")

            price = tick.ask if direction == "buy" else tick.bid
            if price is None:
                raise Exception(f"Не удалось получить цену для символа {symbol}")

            # Определяем тип ордера: покупка или продажа
            order_type = (
                mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL
            )

            # Отправляем запрос на открытие позиции
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": 123456,
                "comment": f"Automated Open: {direction.upper()}",
            }

            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                raise Exception(
                    f"Ошибка при открытии позиции для {symbol}: {result.retcode}"
                )

            logging.info(
                f"Позиция {direction.upper()} для {symbol} успешно открыта (#{i + 1})."
            )

        return True

    except Exception as e:
        logging.error(f"Ошибка при открытии позиции для {symbol}: {e}")
        return False

    finally:
        shutdown_mt5()


def get_open_positions():
    """Получение всех открытых позиций"""
    initialize_mt5()  # Инициализация MT5 перед операцией
    positions = mt5.positions_get()

    if positions is None:
        logging.info("Открытых позиций нет.")
        return []

    return positions


# Функция для закрытия всех позиций по символу
def close_positions_by_symbol(symbol):
    logging.info(f"Попытка закрыть позиции для символа {symbol}")

    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        logging.error(f"Нет открытых позиций для {symbol}")
        return False

    success = True
    for position in positions:
        logging.debug(
            f"Попытка закрыть позицию: тикет {position.ticket}, символ {position.symbol}, объем {position.volume}"
        )
        close_order = mt5.order_send(
            action=mt5.TRADE_ACTION_DEAL,
            symbol=position.symbol,
            volume=position.volume,
            type=(
                mt5.ORDER_TYPE_SELL
                if position.type == mt5.ORDER_TYPE_BUY
                else mt5.ORDER_TYPE_BUY
            ),
            price=(
                mt5.symbol_info_tick(position.symbol).bid
                if position.type == mt5.ORDER_TYPE_BUY
                else mt5.symbol_info_tick(position.symbol).ask
            ),
            deviation=100,
            magic=123456,
            comment="Закрытие по символу",
        )

        if close_order.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(
                f"Ошибка при закрытии позиции: тикет {position.ticket}, код ошибки: {close_order.retcode}"
            )
            success = False
        else:
            logging.info(f"Позиция тикет {position.ticket} успешно закрыта")

    return success


def open_position_with_indicators(symbol, volume, direction):
    """
    Открытие позиции по символу, объему и направлению.
    """
    try:
        initialize_mt5()

        # Получаем текущую цену для открытия позиции
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            raise Exception(f"Не удалось получить тик для символа {symbol}")

        price = tick.ask if direction == "buy" else tick.bid
        if price is None:
            raise Exception(f"Не удалось получить цену для символа {symbol}")

        # Определяем тип ордера: покупка или продажа
        order_type = mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL

        # Отправляем запрос на открытие позиции
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "Automated Open",
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(
                f"Ошибка при открытии позиции для {symbol}: {result.retcode}"
            )

        logging.info(f"Позиция {direction.upper()} для {symbol} успешно открыта.")
        return result

    except Exception as e:
        logging.error(f"Ошибка при открытии позиции для {symbol}: {e}")
        return None

    finally:
        shutdown_mt5()


def close_position(ticket):
    """
    Закрытие позиции по тикету с использованием тикета для правильного закрытия и предотвращения хеджирования.
    """
    initialize_mt5()

    try:
        # Получаем информацию о позиции
        position = mt5.positions_get(ticket=ticket)
        if not position:
            raise Exception(f"Позиция с тикетом {ticket} не найдена.")

        position = position[0]
        symbol = position.symbol
        volume = position.volume

        # Получаем текущую цену для закрытия позиции
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            raise Exception(f"Не удалось получить тик для символа {symbol}")

        # Определяем цену для закрытия
        price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask
        if price is None:
            raise Exception(f"Не удалось получить цену для символа {symbol}")

        # Логируем перед отправкой запроса на закрытие
        logging.info(f"Закрытие позиции: символ={symbol}, объем={volume}, цена={price}")

        # Отправляем запрос на закрытие позиции
        close_order = mt5.order_send(
            action=mt5.TRADE_ACTION_DEAL,  # Действие сделки
            symbol=symbol,
            volume=volume,
            type=(
                mt5.ORDER_TYPE_SELL
                if position.type == mt5.ORDER_TYPE_BUY
                else mt5.ORDER_TYPE_BUY
            ),  # Закрываем противоположной сделкой
            position=ticket,  # Указываем тикет позиции для закрытия
            price=price,
            deviation=100,  # Допустимое отклонение
            magic=123456,
            comment="Automated Close",
        )

        # Проверяем статус выполнения ордера
        if close_order.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(
                f"Ошибка при закрытии позиции {ticket}: код {close_order.retcode}"
            )
            return False

        logging.info(f"Позиция {ticket} успешно закрыта.")
        return True

    except Exception as e:
        logging.error(f"Ошибка при закрытии позиции {ticket}: {e}")
        return False

    finally:
        shutdown_mt5()


# Закрытие позиций в плюсе
def close_positions_in_profit():
    """
    Закрытие всех позиций, которые находятся в плюсе.
    """
    initialize_mt5()

    try:
        positions = mt5.positions_get()
        if not positions:
            logging.info("Нет позиций для закрытия.")
            return False

        for position in positions:
            logging.info(f"Позиция {position.ticket}: прибыль {position.profit}")
            if position.profit > 0:  # Закрываем только прибыльные позиции
                success = close_position(position.ticket)
                if not success:
                    logging.error(f"Ошибка при закрытии позиции {position.ticket}")
                else:
                    logging.info(f"Позиция {position.ticket} успешно закрыта.")

        logging.info("Прибыльные позиции закрыты.")
        return True

    finally:
        shutdown_mt5()


# Закрытие позиций в минусе
def close_positions_in_loss():
    """
    Закрытие всех позиций, которые находятся в минусе.
    """
    initialize_mt5()

    try:
        positions = mt5.positions_get()
        if not positions:
            logging.info("Нет позиций для закрытия.")
            return False

        for position in positions:
            if position.profit < 0:  # Закрываем только убыточные позиции
                close_position(position.ticket)

        logging.info("Убыточные позиции закрыты.")
        return True

    finally:
        shutdown_mt5()


# Initialize MT5 at the start of your script
initialize_mt5()

# Example usage, wrapped in try-finally to ensure proper shutdown
try:
    # Place your code here
    pass
finally:
    # Shut down MT5 at the end
    shutdown_mt5()
