# src/utils/forex_factory.py

import requests
from bs4 import BeautifulSoup


def get_forex_factory_news():
    """Парсинг новостей с сайта Forex Factory."""
    url = "https://www.forexfactory.com/news"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"Ошибка получения данных с Forex Factory: {response.status_code}"
        )

    soup = BeautifulSoup(response.content, "html.parser")

    news_items = []

    # Пробуем найти блоки новостей, используя универсальный селектор
    articles = soup.select("div.news-article")  # Основной блок с новостями
    print(f"Найдено новостных блоков: {len(articles)}")

    for article in articles:
        title = article.select_one(".title").get_text(strip=True)
        link = article.select_one("a")["href"]
        summary = (
            article.select_one(".teaser").get_text(strip=True)
            if article.select_one(".teaser")
            else "Нет описания"
        )

        # Выводим отладочную информацию
        print(f"Новость: {title}, ссылка: {link}, описание: {summary}")

        news_items.append(
            {
                "title": title,
                "summary": summary,
                "link": f"https://www.forexfactory.com{link}",
            }
        )

    return news_items
