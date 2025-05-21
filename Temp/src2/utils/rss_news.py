# src/utils/rss_news.py

import feedparser


def get_fxstreet_news():
    """Получение новостей из RSS-ленты FXStreet."""
    rss_url = "https://www.fxstreet.com/rss"
    feed = feedparser.parse(rss_url)

    news_items = []
    for entry in feed.entries[:15]:  # Берём первые 10 новостей
        news_items.append(
            {"title": entry.title, "summary": entry.summary, "link": entry.link}
        )

    return news_items
