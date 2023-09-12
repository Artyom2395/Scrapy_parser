import scrapy
import time
import re
import json
from scrapy.http import HtmlResponse
from scrapy.http import HtmlResponse
from cian_spider.items import CianSpiderItem

from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from undetected_chromedriver import ChromeOptions



def search_pattern(string):
    pattern = r'1-комн\. кв\.,\s*[0-9,.]+\s*м²,\s*[0-9]+/[0-9]+\s*этаж'
    result = re.match(pattern, string)
    if result:
        return True
    else:
        return False
    

class CianSpSpider(scrapy.Spider):
    name = "cian_sp"
    allowed_domains = ["kazan.cian.ru"]
    
    start_urls = ["https://kazan.cian.ru/cat.php?deal_type=sale&engine_version=2&offer_type=flat&p=1&region=4777&room1=1"]
    custom_settings = {
        'DOWNLOAD_DELAY': 2,  # Задержка в секундах между запросами
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,  # Максимальное количество одновременных запросов к одному домену
        'DOWNLOAD_TIMEOUT': 15,  # Максимальное время ожидания ответа на запрос (в секундах)
        'RETRY_TIMES': 3,  # Количество попыток повторных запросов при ошибке
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 522, 524, 408, 429],  # Коды ошибок, при которых делать повторный запрос
        'PROXIES': ['http://Wr8xXa:qwSyKX:91.218.50.132:9707'],  # этот прокси сркоее всего истек, замените на ваш прокси
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',  # Замените на свой User-Agent
    }
    def parse(self, response):
        # Извлечь информацию с текущей страницы через Scrapy
        for item in self.parse_with_scrapy(response):
            yield item
       
    
    def parse_with_scrapy(self, response):
        lst = response.xpath('.//div[@class="_93444fe79c--moreSuggestionsButtonContainer--h0z5t"]/a[contains(text(), "Показать ещё")]')
        
        if lst:
            
            yield self.activate_selenium(response, current_url=response.url)
        
        else:    
            #if response.status == 200:
            #Парсинг данных с текущей страницы
            for advert in response.xpath('.//div/*[@data-name="LinkArea"]'):

                title = advert.xpath('.//div/*[@data-mark="OfferTitle"]/span/text()').get()
                address_elem = advert.xpath('.//div/*[@class="_93444fe79c--labels--L8WyJ"]/a/text()').getall()
                price = advert.xpath('.//div/*[@data-mark="MainPrice"]/span/text()').get()
                link = advert.xpath('.//a[contains(@class, "_93444fe79c--link--eoxce")]/@href').get()
                page_number = response.url.split('&p=')[1].split('&')[0]

                address = [elem for elem in address_elem]
                if title is not None and not search_pattern(title):
                    title_alt = advert.xpath('.//div/*[@data-mark="OfferSubtitle"]/text()').get()
                    if title_alt is not None and search_pattern(title_alt):
                        title = title_alt
                if title is not None and (search_pattern(title) or search_pattern(title.replace('\xa0', ' '))):
                    item = CianSpiderItem()
                    item['title'] = title
                    item['address'] = ','.join(address)
                    item['price'] = price
                    #item['link'] = link
                    #item['page_number'] = page_number
                    yield item

        next_page_number = int(response.url.split('&p=')[1].split('&')[0]) + 1
        if next_page_number == 55:
            yield self.activate_selenium(response, current_url=response.url)
        else:
            next_page_url = response.url.replace(f'&p={next_page_number - 1}', f'&p={next_page_number}')
            yield scrapy.Request(next_page_url, callback=self.parse)
            
    
    def activate_selenium(self, response, current_url):
        
        options = ChromeOptions()
        options.add_argument("--proxy-server=socks5://E50AQV:Nk5pGC@94.131.53.235:9245")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        with webdriver.Chrome(options=options) as browser:
            
            browser.get(current_url)
            browser.implicitly_wait(10)
            el = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.XPATH, './/div/*[@data-name="LinkArea"]')))
            element = browser.find_element(By.XPATH, './/div[@class="_93444fe79c--moreSuggestionsButtonContainer--h0z5t"]/a[contains(text(), "Показать ещё")]')
            # Прокрутить страницу до элемента
            browser.execute_script("arguments[0].scrollIntoView();", element)

            # Нажать на элемент
            element.click()
            print('нашел тег а')
            # Дождаться загрузки новой информации
            # (например, ожидание нового элемента на странице)
            wait = WebDriverWait(browser, 10)
            new_element = wait.until(EC.presence_of_element_located((By.XPATH, './/div/*[@data-name="LinkArea"]')))

            # Получить HTML-код страницы после загрузки новой информации
            updated_html = browser.page_source
            
            updated_response = HtmlResponse(url=current_url, body=updated_html, encoding='utf-8')
            # Возвращаем вызов метода parse_with_scrapy для обработки обновленной страницы
            return scrapy.Request(url=updated_response.url, callback=self.parse_with_scrapy, dont_filter=True)
        
        