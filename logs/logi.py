import logging


def log_market_structure(market_structure, symbol):
    current_price = market_structure["current_price"]
    trend = market_structure["trend"]
    support = market_structure["support"]
    resistance = market_structure["resistance"]

    log_message = (
        f"LOGi: Структура рынка для {symbol}: Текущая цена={current_price}, "
        f"Тренд={trend}, Поддержка={support}, Сопротивление={resistance}"
    )
    logging.info(log_message)


def log_fibonacci_levels(fibonacci_levels, symbol):
    fib_levels_str = ", ".join(
        [f"{key}={value}" for key, value in fibonacci_levels.items()]
    )
    log_message = f"Уровни Фибоначчи для {symbol}: {fib_levels_str}"
    logging.info(log_message)


def log_fvg_zones(fvg_zones):
    if not fvg_zones:
        logging.info("FVG Зоны: Нет данных. Проверьте диапазон данных или рынок")
    else:
        fvg_str = "; ".join(
            [
                f"Начало={zone['start']}, Конец={zone['end']}, High={zone['high']}, Low={zone['low']}"
                for zone in fvg_zones
            ]
        )
        logging.info(f"FVG Зоны: {fvg_str}")


def log_ict_result(analysis_info, symbol):
    market_structure = analysis_info["market_structure"]
    log_market_structure(market_structure, symbol)

    liquidity = analysis_info["liquidity"]
    logging.info(
        f"Зоны ликвидности для {symbol}: Поддержка={liquidity['support']}, Сопротивление={liquidity['resistance']}"
    )

    fvg_zones = analysis_info["fvg_zones"]
    log_fvg_zones(fvg_zones)

    fibonacci_levels = analysis_info["ote_levels"]
    log_fibonacci_levels(fibonacci_levels, symbol)

    market_timing = analysis_info["market_timing"]
    logging.info(f"Тайминг рынка: {market_timing['current_session']}")

    signal = analysis_info["signal"]
    decision = analysis_info["decision"]
    logging.info(f"Результат стратегии: Сигнал={signal}, Решение={decision}")
