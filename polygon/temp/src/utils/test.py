def test_symbol_info(symbol):
    import MetaTrader5 as mt5

    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"Не удалось получить информацию для {symbol}")
    else:
        print(f"Информация о символе {symbol}: {info}")
