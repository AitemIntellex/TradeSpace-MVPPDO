from datetime import datetime, timedelta
import MetaTrader5 as mt5

mt5.initialize()

today = datetime.now()
start_date = today - timedelta(days=365)

# Получаем историю сделок
rates = mt5.history_deals_get(start_date, today)
if rates is None:
    print(f"Ошибка получения истории сделок: {mt5.last_error()}")
else:
    print(f"Количество сделок: {len(rates)}")
    for deal in rates[:5]:  # Показываем первые 5 сделок
        print(f"Время: {datetime.fromtimestamp(deal.time)}, Прибыль: {deal.profit}")

mt5.shutdown()
