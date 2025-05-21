# src/utils/investing_news.py

import requests
from bs4 import BeautifulSoup


def get_investing_news():
    """Парсинг последних новостей с сайта Investing.com."""
    url = "https://ru.investing.com/news/latest-news"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Ошибка получения данных с Investing.com: {response.status_code}"
        )

    soup = BeautifulSoup(response.content, "html.parser")
    news_items = []

    # Поиск новостных статей
    articles = soup.select("div.textDiv")  # Основной контейнер с новостями
    for article in articles:
        title = article.select_one("a.title").get_text(strip=True)
        link = article.select_one("a")["href"]
        summary = article.select_one("p").get_text(strip=True)

        news_items.append(
            {
                "title": title,
                "summary": summary,
                "link": f"https://ru.investing.com{link}",
            }
        )

    return news_items
