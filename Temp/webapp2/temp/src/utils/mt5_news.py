# src/utils/mt5_news.py

import MetaTrader5 as mt5
from datetime import datetime


def get_mt5_news():
    """Получить новости из MetaTrader 5."""
    news_items = mt5.news_get()

    if news_items is None or len(news_items) == 0:
        return []

    formatted_news = []
    for news in news_items:
        # Форматируем дату и время
        news_time = datetime.fromtimestamp(news.datetime)
        formatted_news.append(
            {
                "time": news_time.strftime("%Y-%m-%d %H:%M:%S"),
                "headline": news.headline,
                "body": news.body,
            }
        )

    return formatted_news
