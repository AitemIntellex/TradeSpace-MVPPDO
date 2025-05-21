from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time


def get_investing_news_selenium():
    """Получение новостей с ru.investing.com через Selenium."""
    chrome_options = webdriver.ChromeOptions()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Открытие страницы новостей Investing.com
        driver.get("https://ru.investing.com/news/latest-news")
        time.sleep(3)  # Даем странице время на загрузку

        news_items = []

        # Поиск блоков новостей
        articles = driver.find_elements(
            By.CSS_SELECTOR, "div.textDiv"
        )  # Это основной блок с новостями

        print(f"Найдено новостных блоков: {len(articles)}")

        for article in articles:
            # Получаем заголовок и ссылку на новость
            title_element = article.find_element(By.CSS_SELECTOR, "a.title")
            title = title_element.text
            link = title_element.get_attribute("href")
            summary = article.find_element(By.CSS_SELECTOR, "p").text

            news_items.append(
                {
                    "title": title,
                    "summary": summary,
                    "link": f"https://ru.investing.com{link}",
                }
            )

        return news_items

    finally:
        # Закрываем браузер после завершения
        driver.quit()
