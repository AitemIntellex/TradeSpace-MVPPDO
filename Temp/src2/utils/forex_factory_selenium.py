from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time


def get_forex_factory_news_selenium():
    """Получение новостей с Forex Factory через Selenium."""
    chrome_options = webdriver.ChromeOptions()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Открытие страницы новостей Forex Factory
        driver.get("https://www.forexfactory.com/news")
        time.sleep(3)  # Даем странице время на загрузку

        news_items = []

        # Ищем блоки новостей. Попробуем другой селектор для ссылок на новости.
        articles = driver.find_elements(
            By.CSS_SELECTOR, "div.news-article"
        )  # Примерный селектор

        # Если блоки новостей найдены, извлекаем информацию
        print(f"Найдено новостных блоков: {len(articles)}")
        for article in articles:
            # Захватываем заголовок и ссылку на новость
            title_element = article.find_element(By.CSS_SELECTOR, "a.flex")
            title = title_element.text
            link = title_element.get_attribute("href")

            news_items.append({"title": title, "link": link})

        return news_items

    finally:
        # Закрываем браузер после завершения
        driver.quit()
