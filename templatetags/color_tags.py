from django import template

register = template.Library()


@register.filter
def color_signal(value, indicator_type="rsi"):
    """
    Возвращает название CSS-класса (например 'signal-long' или 'signal-short')
    в зависимости от логики.
    indicator_type может использоваться, чтобы различать MACD, RSI, ATR и т.д.
    """
    try:
        val = float(value)
    except (TypeError, ValueError):
        # Если значение не число, считаем, что оно не подлежит окраске
        return ""

    # Пример: если это RSI, выше 50 — лонг, ниже 50 — шорт
    if indicator_type.lower() == "rsi":
        return "signal-long" if val >= 50 else "signal-short"

    # Логика для MACD
    if indicator_type.lower() == "macd":
        # Допустим, если значение MACD > 0, сигнал лонг, иначе шорт
        return "signal-long" if val > 0 else "signal-short"

    # Если не указали тип индикатора, по умолчанию считаем >0 лонг
    return "signal-long" if val > 0 else "signal-short"
