import MetaTrader5 as mt5
import pandas as pd
import logging

import logging

# Настраиваем логирование в файл
logging.basicConfig(
    filename="trading_logs.log",  # Укажите путь к файлу, если хотите сохранить логи в определенной папке
    level=logging.DEBUG,  # Уровень логов (DEBUG для всех сообщений, INFO для обычных, ERROR для ошибок)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Формат вывода сообщений
)

logging.info("Логирование настроено и работает")


def initialize_mt5():
    if not mt5.initialize():
        raise Exception("Ошибка при инициализации MetaTrader 5")
    return True


def shutdown_mt5():
    mt5.shutdown()
    logging.info("MetaTrader 5 отключен")


def get_account_info():
    account_info = mt5.account_info()
    if account_info is None:
        raise Exception("Не удалось получить информацию о счете")
    return {
        "balance": account_info.balance,
        "equity": account_info.equity,
        "margin": account_info.margin,
        "profit": account_info.profit,
    }


def get_open_positions():
    positions = mt5.positions_get()
    if positions is None:
        return []
    return positions


def get_ohlc(symbol, timeframe, number_of_candles):
    """
    Получение данных OHLC напрямую из MetaTrader 5.

    :param symbol: Символ инструмента, например, "EURUSD".
    :param timeframe: Таймфрейм (например, mt5.TIMEFRAME_M1 для 1-минутного графика).
    :param number_of_candles: Количество свечей для получения данных.
    :return: DataFrame с данными OHLC.
    """
    # Инициализация MetaTrader 5
    if not mt5.initialize():
        raise Exception("Ошибка при инициализации MetaTrader 5")

    # Установка символа для получения данных
    if not mt5.symbol_select(symbol, True):
        mt5.shutdown()
        raise Exception(f"Не удалось выбрать символ {symbol}")

    # Получение данных по свечам
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, number_of_candles)

    # Завершение работы с MetaTrader 5
    mt5.shutdown()

    if rates is None:
        raise Exception(f"Не удалось получить данные для символа {symbol}")

    # Преобразование данных в DataFrame для удобства работы
    rates_frame = pd.DataFrame(rates)
    rates_frame["time"] = pd.to_datetime(rates_frame["time"], unit="s")

    return rates_frame[["time", "open", "high", "low", "close"]]


def get_currency_tick(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise Exception(f"Не удалось получить тик для символа {symbol}")
    return {"bid": tick.bid, "ask": tick.ask}


def open_position_with_indicators(symbol, volume, direction):
    initialize_mt5()  # Убедимся, что MT5 инициализирован

    try:
        price = (
            mt5.symbol_info_tick(symbol).ask
            if direction == "buy"
            else mt5.symbol_info_tick(symbol).bid
        )
        if price is None:
            raise Exception(f"Не удалось получить цену для символа {symbol}")

        # Логика открытия позиции
        order = mt5.order_send(
            action=mt5.TRADE_ACTION_DEAL,
            symbol=symbol,
            volume=volume,
            type=mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL,
            price=price,
            deviation=100,
            magic=123456,
            comment="Открытие позиции",
        )

        if order.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"Ошибка при открытии позиции {symbol}: {order.retcode}")
            return False

        logging.info(f"Позиция {direction} для {symbol} успешно открыта.")
        return True

    finally:
        shutdown_mt5()  # Корректно завершаем работу MT5


def close_position(ticket):
    """
    Закрытие позиции по тикету с улучшенным логированием.
    """
    initialize_mt5()

    try:
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

        # Получаем текущую цену для закрытия позиции
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            raise Exception(f"Не удалось получить тик для символа {symbol}")

        price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
        if price is None:
            raise Exception(f"Не удалось получить цену для символа {symbol}")

        # Логируем перед отправкой запроса
        logging.info(f"Закрытие позиции: символ={symbol}, объем={volume}, цена={price}")

        close_order = mt5.order_send(
            action=mt5.TRADE_ACTION_DEAL,
            symbol=symbol,
            volume=volume,
            type=order_type,
            price=price,
            deviation=100,  # Увеличиваем допустимое отклонение
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


logging.basicConfig(level=logging.DEBUG)


def close_selected_position(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        logging.error(f"Нет открытых позиций для символа {symbol}.")
        return False

    for position in positions:
        result = mt5.order_send(
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
            comment=f"Закрытие позиции для символа {symbol}",
        )
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"Ошибка закрытия позиции для {symbol}: {result.retcode}")
            return False
    logging.info(f"Позиции для {symbol} успешно закрыты.")
    return True


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
            comment="Закрытие позиции",
        )

        if close_order.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(
                f"Ошибка при закрытии позиции: тикет {position.ticket}, код ошибки: {close_order.retcode}"
            )
            success = False
        else:
            logging.info(f"Позиция тикет {position.ticket} успешно закрыта")

    return success


# Закрытие всех позиций
def close_all_positions():
    """
    Закрытие всех открытых позиций.
    """
    initialize_mt5()

    try:
        positions = mt5.positions_get()
        if not positions:
            logging.info("Нет открытых позиций для закрытия.")
            return False

        for position in positions:
            close_position(position.ticket)

        logging.info("Все позиции успешно закрыты.")
        return True

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
            if position.profit > 0:  # Закрываем только прибыльные позиции
                close_position(position.ticket)

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
