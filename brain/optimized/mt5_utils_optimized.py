import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Generator

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# ------------------------------ Контекстный менеджер для MT5 ------------------------------


def initialize_mt5():
    """
    Инициализирует MetaTrader 5, проверяет соединение и активирует символы.
    """
    if not mt5.initialize():
        raise Exception("Не удалось инициализировать MetaTrader 5")

    account_info = mt5.account_info()
    if account_info is None:
        raise Exception(
            "Не удалось получить информацию об аккаунте. Возможно, терминал не подключён."
        )

    print(
        f"✅ MT5 подключён. Аккаунт: {account_info.login}, Баланс: {account_info.balance}"
    )
    print(mt5.terminal_info())  # Посмотреть, где лежит exe и т.д.
    print(mt5.account_info())


def ensure_symbol_is_selected(symbol: str):
    """
    Проверяет, добавлен ли символ в Market Watch, и если нет — активирует его.
    """
    if not mt5.symbol_select(symbol, True):
        raise Exception(
            f"Не удалось выбрать символ {symbol}. Добавьте его в Market Watch."
        )


class MT5Connector:
    """
    Контекстный менеджер для инициализации и завершения работы с MetaTrader 5.
    """

    def __enter__(self) -> "MT5Connector":
        if not mt5.initialize():
            raise Exception("Ошибка при инициализации MetaTrader 5")
        logging.info("MetaTrader 5 успешно инициализирован")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        mt5.shutdown()
        logging.info("MetaTrader 5 отключен")


# ------------------------------ Функции подключения и работы с аккаунтом ------------------------------


def connect_mt5(account: Any) -> bool:
    """
    Подключается к MT5 с использованием данных аккаунта.
    """
    try:
        with MT5Connector():
            if not mt5.login(account.login, account.password, server=account.server):
                raise ConnectionError(
                    f"MetaTrader 5: Ошибка авторизации для {account.name}"
                )
            logging.info(f"Успешная авторизация для {account.name}")
            return True
    except Exception as e:
        logging.error(f"Ошибка подключения: {e}")
        return False


# ------------------------------ Получение данных ------------------------------

import MetaTrader5 as mt5

# 🛠 Маппинг строковых таймфреймов в числа для MT5
TIMEFRAME_MAPPING = {
    "1m": mt5.TIMEFRAME_M1,
    "5m": mt5.TIMEFRAME_M5,
    "15m": mt5.TIMEFRAME_M15,
    "30m": mt5.TIMEFRAME_M30,
    "1h": mt5.TIMEFRAME_H1,
    "4h": mt5.TIMEFRAME_H4,
    "1d": mt5.TIMEFRAME_D1,
    "1w": mt5.TIMEFRAME_W1,
}


def convert_timeframe(timeframe_str):
    """
    Конвертирует строковый таймфрейм (M15, H1 и т. д.) в формат MetaTrader 5.
    """
    return TIMEFRAME_MAPPING.get(timeframe_str, None)


# def get_rates_dataframe(symbol: str, timeframe: str, num_candles: int):
#     """
#     Получает исторические данные из MetaTrader 5.
#     """
#     mt5_timeframe = convert_timeframe(timeframe)

#     if mt5_timeframe is None:
#         raise ValueError(
#             f"Неверный формат таймфрейма: {timeframe}. Используйте M1, M5, M15, H1 и т. д."
#         )

#     # Выбираем символ перед copy_rates_from_pos
#     if not mt5.symbol_select(symbol, True):
#         raise Exception(f"Не удалось активировать символ {symbol} в Market Watch.")

#     rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, num_candles)

#     if rates is None or len(rates) == 0:
#         err_code, err_desc = last_error()
#         logging.error(f"Ошибка {err_code}: {err_desc}")
#         raise Exception(f"Не удалось получить данные для {symbol} {timeframe}")


#     return pd.DataFrame(rates)
def get_rates_dataframe(symbol: str, timeframe: str, num_candles: int):
    print(f"⚡️ Запрашиваем {num_candles} свечей для {symbol} ({timeframe})")

    # 🛠 Конвертируем таймфрейм в int
    mt5_timeframe = TIMEFRAME_MAPPING.get(timeframe)
    if mt5_timeframe is None:
        raise ValueError(f"❌ Неверный формат таймфрейма: {timeframe}")

    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, num_candles)

    if rates is None:
        print(f"❌ Ошибка: Не удалось получить данные для {symbol} ({timeframe})")
        return None

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df


def get_trade_history(
    start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Получает историю сделок за указанный период.
    """
    start_date = start_date or datetime(2000, 1, 1)
    end_date = end_date or datetime.now()
    try:
        with MT5Connector():
            deals = mt5.history_deals_get(start_date, end_date)
            if deals is None:
                raise RuntimeError(f"Не удалось получить сделки: {mt5.last_error()}")
            return [
                {
                    "time": deal.time,
                    "symbol": deal.symbol,
                    "profit": deal.profit,
                    "volume": deal.volume,
                    "price": deal.price,
                }
                for deal in deals
            ]
    except Exception as e:
        logging.error(f"Ошибка получения торговой истории: {e}")
        return []


# ------------------------------ Торговые операции ------------------------------


def open_position(symbol: str, volume: float, direction: str, count: int = 1) -> bool:
    """
    Открывает позицию по заданному символу.
    """
    try:
        with MT5Connector():
            for _ in range(count):
                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    raise Exception(f"Не удалось получить тик для символа {symbol}")
                price = tick.ask if direction == "buy" else tick.bid
                order_type = (
                    mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL
                )
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
                    f"Позиция {direction.upper()} для {symbol} успешно открыта."
                )
            return True
    except Exception as e:
        logging.error(f"Ошибка при открытии позиции для {symbol}: {e}")
        return False


def close_position(ticket: int) -> bool:
    """
    Закрывает позицию по указанному тикету.
    """
    try:
        with MT5Connector():
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                raise Exception(f"Позиция с тикетом {ticket} не найдена.")
            position = positions[0]
            symbol = position.symbol
            volume = position.volume
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                raise Exception(f"Не удалось получить тик для символа {symbol}")
            price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask
            close_order = mt5.order_send(
                action=mt5.TRADE_ACTION_DEAL,
                symbol=symbol,
                volume=volume,
                type=(
                    mt5.ORDER_TYPE_SELL
                    if position.type == mt5.ORDER_TYPE_BUY
                    else mt5.ORDER_TYPE_BUY
                ),
                position=ticket,
                price=price,
                deviation=100,
                magic=123456,
                comment="Automated Close",
            )
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


# ------------------------------ Пример использования ------------------------------

if __name__ == "__main__":
    try:
        with MT5Connector():
            # Пример: можно проверить получение тиков для символа
            symbol = "EURUSD"
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                logging.info(
                    f"Текущий тик для {symbol}: Ask={tick.ask}, Bid={tick.bid}"
                )
            else:
                logging.error(f"Не удалось получить тик для {symbol}")
    except Exception as e:
        logging.error(f"Ошибка в основном блоке: {e}")
