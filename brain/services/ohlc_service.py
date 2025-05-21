# brain/services/ohlc_service.py


def fetch_ohlc(symbol: str, timeframe: str, candles: int):
    """
    Пример получения OHLC-данных.
    Возвращает список словарей:
    [
      {"time": "2023-02-07 10:00", "open": 1.2000, "high": 1.2050, "low": 1.1990, "close": 1.2030},
      ...
    ]
    """
    # Заглушка, для примера
    import datetime

    base_time = datetime.datetime.now()
    data = []
    for i in range(candles):
        t = base_time.replace(minute=base_time.minute - i)
        price = 1.2000 + i * 0.0001
        data.append(
            {
                "time": t.strftime("%Y-%m-%d %H:%M"),
                "open": price,
                "high": price + 0.0005,
                "low": price - 0.0005,
                "close": price + 0.0001,
            }
        )
    # Разворот, чтобы [0] был самый старый
    data.reverse()
    return data
