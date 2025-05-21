# tgdbot.py
import MetaTrader5 as mt5
from telegram import Bot
import asyncio
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
account = int(os.getenv('MT5_ACCOUNT'))
password = os.getenv('MT5_PASSWORD')
server = os.getenv('MT5_SERVER')

# Инициализация Telegram бота
bot = Bot(token=bot_token)

# Асинхронная функция для отправки сообщений
async def send_telegram_message(message):
    try:
        await bot.send_message(chat_id=chat_id, text=message)
        print(f"Сообщение отправлено: {message}")
    except Exception as e:
        print(f"Ошибка при отправке сообщения в Telegram: {e}")

# Инициализация MetaTrader 5
def initialize_mt5():
    if not mt5.initialize():
        print("Не удалось инициализировать MetaTrader 5")
        mt5.shutdown()
        return False

    if not mt5.login(account, password=password, server=server):
        print(f"Не удалось подключиться к счету {account}, ошибка: {mt5.last_error()}")
        mt5.shutdown()
        return False

    print(f"Успешное подключение к счету {account}")
    return True

# Получение информации о счете
def get_account_info():
    account_info = mt5.account_info()
    if account_info is None:
        print("Ошибка при получении информации о счете")
        return None

    message = (f"Exness forex:\n"
               f"Номер счета: {account_info.login}\n"
               f"Баланс: {account_info.balance}\n"
               f"Эквити: {account_info.equity}\n"
               f"Открытые позиции: {mt5.positions_total()}")

    return message

# Функция для расчета скользящей средней
def get_moving_average(symbol, timeframe, period):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period)
    if rates is None or len(rates) == 0:
        print(f"Ошибка при получении данных для {symbol}")
        return None

    prices = [rate['close'] for rate in rates]
    return sum(prices) / period

# Определение зон спроса и предложения (Supply and Demand)
def detect_supply_demand_zone(symbol, timeframe):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
    if rates is None or len(rates) == 0:
        print(f"Ошибка при получении данных для {symbol}")
        return None

    highs = [rate['high'] for rate in rates]
    lows = [rate['low'] for rate in rates]

    demand_zone = min(lows)  # Зона спроса
    supply_zone = max(highs)  # Зона предложения

    return supply_zone, demand_zone

# Открытие позиции с комментарием
def open_position(symbol, volume, order_type, reason):
    price = mt5.symbol_info_tick(symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid
    comment = f"OpenOrder: {reason}"

    order = mt5.order_send(
        symbol=symbol,
        action=mt5.TRADE_ACTION_DEAL,
        volume=volume,
        type=order_type,
        price=price,
        deviation=100,  # Допустимое отклонение
        magic=123456,  # Change to appropriate magic number
        comment=comment  # Комментарий с причиной входа
    )

    if order is None:
        print(f"Ошибка: не удалось отправить ордер на открытие позиции для {symbol}")
        print(f"Последняя ошибка: {mt5.last_error()}")
        return False

    if order.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Ошибка при открытии позиции для {symbol}: {order.retcode}")
        print(f"Последняя ошибка: {mt5.last_error()}")
        return False

    print(f"Открыта позиция {order_type} для {symbol}, объем {volume}, причина: {reason}")
    return True

# Логика стратегии SMC (Smart Money Concepts)
async def smc_trading_strategy(symbol, volume):
    supply_zone, demand_zone = detect_supply_demand_zone(symbol, mt5.TIMEFRAME_M15)
    if supply_zone is None or demand_zone is None:
        return

    current_price = mt5.symbol_info_tick(symbol).bid

    positions = mt5.positions_get(symbol=symbol)

    # Вход в длинную позицию (BUY) с комментарием
    if current_price < demand_zone and len(positions) == 0:
        reason = f"Цена ниже зоны спроса ({demand_zone})"
        open_position(symbol, volume, mt5.ORDER_TYPE_BUY, reason)
        await send_telegram_message(f"Открыта длинная позиция для {symbol}, причина: {reason}")

    # Вход в короткую позицию (SELL) с комментарием
    elif current_price > supply_zone and len(positions) == 0:
        reason = f"Цена выше зоны предложения ({supply_zone})"
        open_position(symbol, volume, mt5.ORDER_TYPE_SELL, reason)
        await send_telegram_message(f"Открыта короткая позиция для {symbol}, причина: {reason}")

# Основная логика
async def main():
    if not initialize_mt5():
        return

    symbols = ["XAUUSDm", "EURUSDm", "GBPJPYm", "USDJPYm", "GBPUSDm"]  # Список торговых пар
    volume = 0.01

    try:
        account_message = get_account_info()
        if account_message:
            await send_telegram_message(account_message)

        while True:
            for symbol in symbols:
                await smc_trading_strategy(symbol, volume)

            # Отправляем сообщения каждые 3 минуты
            await send_telegram_message("Все в порядке. Без изменений.")
            await asyncio.sleep(180)  # 180 секунд = 3 минуты
    except KeyboardInterrupt:
        pass
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
