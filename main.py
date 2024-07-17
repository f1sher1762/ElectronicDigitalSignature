from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time

def logout_from_google():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--incognito")  # Открывает браузер в режиме инкогнито

    # Запуск Chrome
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://myaccount.google.com/")

    # Ожидание загрузки страницы
    time.sleep(5)

    # Настройка нахождения кнопки выхода
    logout_button = driver.find_element_by_xpath("//a[contains(@href, 'Logout')]")

    # Нажатие кнопки
    logout_button.click()

    # Закрыть браузер
    driver.quit()

# Запуск функции выхода из гугл
logout_from_google()
